from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.task import Payout, PayoutStatus
from app.models.user import Executor, User
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin", tags=["admin"])


async def require_any_client(user: User = Depends(get_current_user)) -> User:
    """Для MVP — любой залогиненный клиент видит выплаты."""
    if user.role.value != "client":
        raise HTTPException(status_code=403, detail="Только для клиентов")
    return user


@router.get("/payouts")
async def list_payouts(
    status: str = "pending",
    user: User = Depends(require_any_client),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Payout)
        .where(Payout.status == PayoutStatus(status))
        .options(
            selectinload(Payout.executor).selectinload(Executor.user)
        )
        .order_by(Payout.created_at.desc())
    )
    payouts = result.scalars().all()

    return [
        {
            "id": p.id,
            "amount": float(p.amount),
            "phone": p.phone,
            "status": p.status.value,
            "executor_name": p.executor.user.name if p.executor else None,
            "executor_tg": p.executor.user.telegram_username if p.executor else None,
            "completed_tasks": p.executor.completed_tasks if p.executor else 0,
            "created_at": p.created_at,
            "completed_at": p.completed_at,
        }
        for p in payouts
    ]


@router.post("/payouts/{payout_id}/complete")
async def complete_payout(
    payout_id: int,
    user: User = Depends(require_any_client),
    db: AsyncSession = Depends(get_db),
):
    payout = await db.get(
        Payout, payout_id,
        options=[selectinload(Payout.executor).selectinload(Executor.user)]
    )
    if not payout:
        raise HTTPException(status_code=404, detail="Выплата не найдена")
    if payout.status != PayoutStatus.pending:
        raise HTTPException(status_code=400, detail="Выплата уже обработана")

    payout.status = PayoutStatus.completed
    payout.completed_at = datetime.now(timezone.utc)
    await db.commit()

    # Уведомляем исполнителя
    if payout.executor and payout.executor.user.telegram_id:
        from app.services.notifier import notify_telegram
        await notify_telegram(
            payout.executor.user.telegram_id,
            f"💳 Выплата {payout.amount:.0f} ₽ отправлена на номер {payout.phone}",
        )

    return {"ok": True}


@router.post("/payouts/{payout_id}/reject")
async def reject_payout(
    payout_id: int,
    reason: str = Form(default=""),
    user: User = Depends(require_any_client),
    db: AsyncSession = Depends(get_db),
):
    payout = await db.get(
        Payout, payout_id,
        options=[selectinload(Payout.executor).selectinload(Executor.user)]
    )
    if not payout:
        raise HTTPException(status_code=404, detail="Выплата не найдена")
    if payout.status != PayoutStatus.pending:
        raise HTTPException(status_code=400, detail="Выплата уже обработана")

    payout.status = PayoutStatus.failed
    await db.commit()

    # Возвращаем деньги на баланс исполнителя
    executor = payout.executor
    executor.balance = float(executor.balance) + float(payout.amount)
    await db.commit()

    if executor.user.telegram_id:
        from app.services.notifier import notify_telegram
        msg = f"❌ Выплата {payout.amount:.0f} ₽ отклонена"
        if reason:
            msg += f". Причина: {reason}"
        msg += ". Средства возвращены на баланс."
        await notify_telegram(executor.user.telegram_id, msg)

    return {"ok": True}
