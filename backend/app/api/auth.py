from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import Client, User, UserRole

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    name: str
    company_name: str | None = None
    phone: str | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    name: str | None


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterIn, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")

    user = User(
        role=UserRole.client,
        email=data.email,
        password_hash=hash_password(data.password),
        name=data.name,
        phone=data.phone,
    )
    db.add(user)
    await db.flush()

    client = Client(user_id=user.id, company_name=data.company_name)
    db.add(client)
    await db.commit()
    await db.refresh(user)

    return TokenOut(
        access_token=create_access_token(user.id),
        user_id=user.id,
        name=user.name,
    )


@router.post("/login", response_model=TokenOut)
async def login(data: LoginIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")

    return TokenOut(
        access_token=create_access_token(user.id),
        user_id=user.id,
        name=user.name,
    )


@router.get("/me")
async def me(db: AsyncSession = Depends(get_db), token: str = ""):
    # Простая проверка — полная в deps.py
    return {"ok": True}
