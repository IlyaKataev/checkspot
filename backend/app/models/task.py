import enum
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TaskStatus(str, enum.Enum):
    available = "available"
    in_progress = "in_progress"
    pending_review = "pending_review"   # фото загружено, ждёт модерации
    completed = "completed"
    rejected = "rejected"


class PayoutStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class TicketType(str, enum.Enum):
    support = "support"
    complaint = "complaint"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    address: Mapped[str] = mapped_column(String(500))
    lat: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    lng: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.available)
    executor_id: Mapped[int | None] = mapped_column(ForeignKey("executors.id"), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    campaign: Mapped["Campaign"] = relationship(back_populates="tasks")
    executor: Mapped["Executor | None"] = relationship(back_populates="tasks")
    report: Mapped["TaskReport | None"] = relationship(back_populates="task", uselist=False)


class TaskReport(Base):
    __tablename__ = "task_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), unique=True)
    executor_id: Mapped[int] = mapped_column(ForeignKey("executors.id"))
    photo_path: Mapped[str] = mapped_column(String(500))
    photo_taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    photo_lat: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    photo_lng: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    # JSON от AI или ручной результат
    check_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    client_confirmed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    task: Mapped["Task"] = relationship(back_populates="report")
    executor: Mapped["Executor"] = relationship(back_populates="reports")


class Payout(Base):
    __tablename__ = "payouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    executor_id: Mapped[int] = mapped_column(ForeignKey("executors.id"))
    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    status: Mapped[PayoutStatus] = mapped_column(Enum(PayoutStatus), default=PayoutStatus.pending)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    executor: Mapped["Executor"] = relationship(back_populates="payouts")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="notifications")


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    type: Mapped[TicketType] = mapped_column(Enum(TicketType), default=TicketType.support)
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="support_tickets")
