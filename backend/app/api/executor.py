from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.task import Payout, PayoutStatus, Notification
from app.models.user import Executor, User

router = APIRouter(prefix="/executor", tags=["executor"])


async def get_executor_by_tg(telegram_id: int, db: AsyncSession) -> Executor:
    result = await db.execute(
        select(Executor).join(User).where(User.telegram_id == telegram_id)
    )
    executor = result.scalar_one_or_none()
    if not executor:
        raise HTTPException(status_code=404, detail="Исполнитель не найден")
    return executor


class BalanceOut(BaseModel):
    balance: float
    completed_tasks: int
    pending_payout: float


@router.get("/balance")
async def get_balance(telegram_id: int, db: AsyncSession = Depends(get_db)):
    executor = await get_executor_by_tg(telegram_id, db)

    # Считаем pending выплат
    result = await db.execute(
        select(Payout)
        .where(Payout.executor_id == executor.id, Payout.status == PayoutStatus.pending)
    )
    pending = result.scalars().all()
    pending_total = sum(float(p.amount) for p in pending)

    return {
        "balance": float(executor.balance),
        "completed_tasks": executor.completed_tasks,
        "pending_payout": pending_total,
    }


@router.post("/payout")
async def request_payout(
    telegram_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
):
    executor = await get_executor_by_tg(telegram_id, db)

    if float(executor.balance) < 100:
        raise HTTPException(status_code=400, detail="Минимальная сумма вывода 100 ₽")

    amount = float(executor.balance)
    payout = Payout(
        executor_id=executor.id,
        amount=amount,
        phone=executor.user.phone,
        status=PayoutStatus.pending,
    )
    db.add(payout)
    executor.balance = 0
    await db.commit()

    return {"ok": True, "amount": amount}


@router.get("/notifications")
async def get_notifications(telegram_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Executor).join(User).where(User.telegram_id == telegram_id)
    )
    executor = result.scalar_one_or_none()
    if not executor:
        return []

    notif_result = await db.execute(
        select(Notification)
        .where(Notification.user_id == executor.user_id, Notification.is_read == False)
        .order_by(Notification.created_at.desc())
    )
    notifications = notif_result.scalars().all()
    for n in notifications:
        n.is_read = True
    await db.commit()

    return [{"id": n.id, "title": n.title, "body": n.body, "meta": n.meta} for n in notifications]
