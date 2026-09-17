from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from database.models import Base, VlessUser
import os

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

app = FastAPI(title="VLESS API")


class CreateUser(BaseModel):
    telegram_id: int
    username: str
    days: int


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/users")
async def create_user(data: CreateUser):
    if data.days < 1 or data.days > 3650:
        raise HTTPException(400, "المدة غير صحيحة")

    user_uuid = str(uuid4())
    expires = datetime.utcnow() + timedelta(days=data.days)

    async with SessionLocal() as db:
        user = VlessUser(
            telegram_id=data.telegram_id,
            username=data.username,
            uuid=user_uuid,
            expires_at=expires,
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        return {
            "id": user.id,
            "username": user.username,
            "uuid": user.uuid,
            "expires_at": user.expires_at,
        }


@app.get("/users")
async def users():
    async with SessionLocal() as db:
        result = await db.execute(
            select(VlessUser).order_by(VlessUser.id.desc())
        )

        rows = result.scalars().all()

        return [
            {
                "id": u.id,
                "telegram_id": u.telegram_id,
                "username": u.username,
                "uuid": u.uuid,
                "expires_at": u.expires_at,
            }
            for u in rows
        ]


@app.delete("/users/{user_id}")
async def delete_user(user_id: int):
    async with SessionLocal() as db:
        user = await db.get(VlessUser, user_id)

        if not user:
            raise HTTPException(404, "الحساب غير موجود")

        await db.delete(user)
        await db.commit()

        return {"status": "deleted"}


@app.post("/users/{user_id}/extend")
async def extend_user(user_id: int, days: int = 30):
    if days < 1 or days > 3650:
        raise HTTPException(400, "المدة غير صحيحة")

    async with SessionLocal() as db:
        user = await db.get(VlessUser, user_id)

        if not user:
            raise HTTPException(404, "الحساب غير موجود")

        now = datetime.utcnow()

        if user.expires_at < now:
            user.expires_at = now + timedelta(days=days)
        else:
            user.expires_at += timedelta(days=days)

        await db.commit()
        await db.refresh(user)

        return {
            "id": user.id,
            "username": user.username,
            "expires_at": user.expires_at,
        }