import math
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_client
from app.core.config import settings
from app.core.database import get_db
from app.models.campaign import Campaign, CampaignStatus
from app.models.task import Task, TaskReport, TaskStatus, Notification
from app.models.user import Client, Executor, User
from app.services.notifier import notify_telegram

router = APIRouter(prefix="/tasks", tags=["tasks"])

TASK_TIME_LIMIT_MINUTES = 30


def haversine_km(lat1, lng1, lat2, lng2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class TaskOut(BaseModel):
    id: int
    campaign_id: int
    address: str
    lat: float | None
    lng: float | None
    status: str
    category: str
    price_per_task: float
    distance_m: float | None = None
    accepted_at: datetime | None
    deadline_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class ReportOut(BaseModel):
    id: int
    task_id: int
    address: str
    status: str
    photo_url: str | None
    photo_taken_at: datetime | None
    check_result: Any
    client_confirmed: bool | None
    rejection_reason: str | None
    executor_phone: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Для исполнителей (без JWT, по telegram_id) ──────────────────────────────

@router.get("/nearby")
async def tasks_nearby(
    lat: float,
    lng: float,
    radius_m: float = 2000,
    telegram_id: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Задания рядом с исполнителем. Вызывается ботом."""
    result = await db.execute(
        select(Task)
        .join(Campaign)
        .where(
            Task.status == TaskStatus.available,
            Campaign.status == CampaignStatus.active,
            Task.lat.isnot(None),
            Task.lng.isnot(None),
        )
        .options(selectinload(Task.campaign))
    )
    tasks = result.scalars().all()

    nearby = []
    for task in tasks:
        dist_km = haversine_km(lat, lng, float(task.lat), float(task.lng))
        dist_m = dist_km * 1000
        if dist_m <= radius_m:
            nearby.append({
                "id": task.id,
                "campaign_id": task.campaign_id,
                "address": task.address,
                "lat": float(task.lat),
                "lng": float(task.lng),
                "category": task.campaign.category,
                "price_per_task": float(task.campaign.price_per_task),
                "distance_m": round(dist_m),
                "status": task.status.value,
            })

    nearby.sort(key=lambda t: t["distance_m"])
    return nearby


@router.post("/{task_id}/accept")
async def accept_task(
    task_id: int,
    telegram_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Исполнитель берёт задание."""
    result = await db.execute(
        select(Executor).join(User).where(User.telegram_id == telegram_id)
    )
    executor = result.scalar_one_or_none()
    if not executor:
        raise HTTPException(status_code=404, detail="Исполнитель не найден")

    task = await db.get(Task, task_id, options=[selectinload(Task.campaign)])
    if not task:
        raise HTTPException(status_code=404, detail="Задание не найдено")
    if task.status != TaskStatus.available:
        raise HTTPException(status_code=400, detail="Задание уже занято или выполнено")

    now = datetime.now(timezone.utc)
    task.status = TaskStatus.in_progress
    task.executor_id = executor.id
    task.accepted_at = now
    task.deadline_at = now + timedelta(minutes=TASK_TIME_LIMIT_MINUTES)
    await db.commit()

    return {
        "ok": True,
        "task_id": task.id,
        "address": task.address,
        "category": task.campaign.category,
        "price": float(task.campaign.price_per_task),
        "deadline_at": task.deadline_at.isoformat(),
    }


@router.post("/{task_id}/submit")
async def submit_photo(
    task_id: int,
    telegram_id: int = Form(...),
    photo_lat: float | None = Form(None),
    photo_lng: float | None = Form(None),
    photo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Исполнитель загружает фото."""
    result = await db.execute(
        select(Executor).join(User).where(User.telegram_id == telegram_id)
    )
    executor = result.scalar_one_or_none()
    if not executor:
        raise HTTPException(status_code=404, detail="Исполнитель не найден")

    task = await db.get(Task, task_id, options=[selectinload(Task.campaign)])
    if not task or task.executor_id != executor.id:
        raise HTTPException(status_code=404, detail="Задание не найдено")
    if task.status != TaskStatus.in_progress:
        raise HTTPException(status_code=400, detail="Задание не в работе")

    # Сохраняем фото
    os.makedirs(settings.MEDIA_DIR, exist_ok=True)
    ext = os.path.splitext(photo.filename or "photo.jpg")[1] or ".jpg"
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(settings.MEDIA_DIR, filename)
    content = await photo.read()
    with open(filepath, "wb") as f:
        f.write(content)

    # Создаём отчёт
    report = TaskReport(
        task_id=task.id,
        executor_id=executor.id,
        photo_path=filename,
        photo_taken_at=datetime.now(timezone.utc),
        photo_lat=photo_lat,
        photo_lng=photo_lng,
    )
    db.add(report)

    # Переводим в pending_review (ждёт ручной модерации)
    task.status = TaskStatus.pending_review
    await db.commit()

    # Уведомляем заказчика
    camp_result = await db.execute(
        select(Campaign).where(Campaign.id == task.campaign_id)
    )
    campaign = camp_result.scalar_one_or_none()
    if campaign:
        from app.models.user import Client as ClientModel
        client_res = await db.execute(select(ClientModel).where(ClientModel.id == campaign.client_id))
        client = client_res.scalar_one_or_none()
        if client:
            notif = Notification(
                user_id=client.user_id,
                title="Новое фото на проверку",
                body=f"Фото по адресу {task.address} ожидает проверки",
                meta={"task_id": task.id, "campaign_id": campaign.id},
            )
            db.add(notif)
            await db.commit()

    return {"ok": True, "status": "pending_review"}


# ── Для заказчиков (с JWT) ─────────────────────────────────────────────────

@router.get("/campaign/{campaign_id}/reports", response_model=list[ReportOut])
async def campaign_reports(
    campaign_id: int,
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """Все задания кампании с отчётами."""
    campaign = await db.get(Campaign, campaign_id)
    if not campaign or campaign.client_id != client.id:
        raise HTTPException(status_code=404, detail="Кампания не найдена")

    result = await db.execute(
        select(Task)
        .where(Task.campaign_id == campaign_id)
        .options(selectinload(Task.report).selectinload(TaskReport.executor).selectinload(Executor.user))
    )
    tasks = result.scalars().all()

    out = []
    for task in tasks:
        report = task.report
        photo_url = None
        if report and report.photo_path:
            photo_url = f"/media/{report.photo_path}"

        executor_phone = None
        if report and report.executor and report.executor.user:
            executor_phone = report.executor.user.phone

        out.append(ReportOut(
            id=task.id,
            task_id=task.id,
            address=task.address,
            status=task.status.value,
            photo_url=photo_url,
            photo_taken_at=report.photo_taken_at if report else None,
            check_result=report.check_result if report else None,
            client_confirmed=report.client_confirmed if report else None,
            rejection_reason=report.rejection_reason if report else None,
            executor_phone=executor_phone,
            created_at=report.created_at if report else task.accepted_at or datetime.now(timezone.utc),
        ))
    return out


@router.post("/{task_id}/moderate")
async def moderate_task(
    task_id: int,
    approved: bool = Form(...),
    rejection_reason: str | None = Form(None),
    client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """Ручная модерация фото заказчиком."""
    task = await db.get(
        Task, task_id,
        options=[
            selectinload(Task.campaign),
            selectinload(Task.report).selectinload(TaskReport.executor).selectinload(Executor.user),
        ]
    )
    if not task:
        raise HTTPException(status_code=404, detail="Задание не найдено")

    campaign = task.campaign
    if campaign.client_id != client.id:
        raise HTTPException(status_code=403, detail="Нет доступа")
    if task.status != TaskStatus.pending_review:
        raise HTTPException(status_code=400, detail="Задание не ожидает проверки")

    report = task.report
    if not report:
        raise HTTPException(status_code=404, detail="Отчёт не найден")

    now = datetime.now(timezone.utc)
    executor = report.executor

    if approved:
        task.status = TaskStatus.completed
        task.completed_at = now
        report.client_confirmed = True

        # Начисляем исполнителю
        executor.balance = float(executor.balance) + float(campaign.price_per_task)
        executor.completed_tasks += 1

        # Уведомление исполнителю
        notif = Notification(
            user_id=executor.user_id,
            title="Фото принято!",
            body=f"Ваше фото по адресу {task.address} принято. Начислено {campaign.price_per_task} ₽",
            meta={"task_id": task.id, "amount": float(campaign.price_per_task)},
        )
    else:
        task.status = TaskStatus.rejected
        report.client_confirmed = False
        report.rejection_reason = rejection_reason

        # Освобождаем задание
        task.executor_id = None
        task.accepted_at = None
        task.deadline_at = None
        # Не удаляем отчёт — оставляем историю

        # Уведомление исполнителю
        notif = Notification(
            user_id=executor.user_id,
            title="Фото отклонено",
            body=f"Ваше фото по адресу {task.address} отклонено. Причина: {rejection_reason or 'не указана'}",
            meta={"task_id": task.id},
        )

    db.add(notif)
    await db.commit()

    # Отправляем Telegram-сообщение исполнителю
    if executor.user.telegram_id:
        await notify_telegram(executor.user.telegram_id, notif.body)

    return {"ok": True}
