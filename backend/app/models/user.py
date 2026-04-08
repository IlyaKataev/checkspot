import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    client = "client"
    executor = "executor"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    agreed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Только для клиентов (dashboard)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Только для исполнителей (Telegram)
    telegram_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    telegram_username: Mapped[str | None] = mapped_column(String(255), nullable=True)

    client: Mapped["Client | None"] = relationship(back_populates="user", uselist=False)
    executor: Mapped["Executor | None"] = relationship(back_populates="user", uselist=False)
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user")
    support_tickets: Mapped[list["SupportTicket"]] = relationship(back_populates="user")


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    balance: Mapped[float] = mapped_column(Numeric(10, 2), default=0)

    user: Mapped["User"] = relationship(back_populates="client")
    campaigns: Mapped[list["Campaign"]] = relationship(back_populates="client")


class Executor(Base):
    __tablename__ = "executors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    balance: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    completed_tasks: Mapped[int] = mapped_column(Integer, default=0)
    # Последняя известная геолокация
    lat: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    lng: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="executor")
    tasks: Mapped[list["Task"]] = relationship(back_populates="executor")
    reports: Mapped[list["TaskReport"]] = relationship(back_populates="executor")
    payouts: Mapped[list["Payout"]] = relationship(back_populates="executor")
