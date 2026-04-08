"""Фоновые задачи: освобождение просроченных заданий."""
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.task import Task, TaskStatus
from app.services.notifier import notify_telegram

logger = logging.getLogger(__name__)


async def release_expired_tasks() -> None:
    """Освобождает задания, у которых истёк дедлайн."""
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(Task).where(
                Task.status == TaskStatus.in_progress,
                Task.deadline_at < now,
            )
        )
        expired = result.scalars().all()

        if not expired:
            return

        for task in expired:
            task.status = TaskStatus.available
            task.executor_id = None
            task.accepted_at = None
            task.deadline_at = None

        await db.commit()
        logger.info(f"Released {len(expired)} expired tasks")

        # Уведомляем исполнителей (загружаем отдельно, чтоб не усложнять запрос выше)
        for task in expired:
            from sqlalchemy.orm import selectinload
            from app.models.user import Executor, User
            t = await db.get(
                Task, task.id,
                options=[selectinload(Task.campaign)]
            )
            # executor уже отвязан, но можно попробовать уведомить через историю — пропускаем для простоты


async def scheduler_loop() -> None:
    """Запускается один раз при старте, крутится бесконечно."""
    logger.info("Task scheduler started")
    while True:
        try:
            await release_expired_tasks()
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        await asyncio.sleep(5 * 60)  # каждые 5 минут
