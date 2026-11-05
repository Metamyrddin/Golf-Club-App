"""Normalised schema. Medical columns are sealed JSON when a Fernet key is set."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    profile: Mapped["Profile"] = relationship(back_populates="user", uselist=False)
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="user")


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    height_cm: Mapped[float | None] = mapped_column(Float)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    age: Mapped[int | None] = mapped_column(Integer)
    gender: Mapped[str | None] = mapped_column(String(32))
    body_type: Mapped[str | None] = mapped_column(String(32))
    wrist_to_floor_cm: Mapped[float | None] = mapped_column(Float)
    hand_size_cm: Mapped[float | None] = mapped_column(Float)
    bench_press_kg: Mapped[float | None] = mapped_column(Float)
    squat_kg: Mapped[float | None] = mapped_column(Float)
    vo2_max: Mapped[float | None] = mapped_column(Float)
    resting_hr: Mapped[float | None] = mapped_column(Float)
    fitness_level: Mapped[int | None] = mapped_column(Integer)
    handicap: Mapped[float | None] = mapped_column(Float)
    swing_speed_mph: Mapped[float | None] = mapped_column(Float)
    current_brand: Mapped[str | None] = mapped_column(String(64))
    preferred_brands: Mapped[list | None] = mapped_column(JSON)
    # Sealed when MEDICAL_FERNET_KEY is set. See app.privacy.
    medical_flags: Mapped[dict | list | None] = mapped_column(JSON)
    medical_notes: Mapped[dict | str | None] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    user: Mapped[User] = relationship(back_populates="profile")


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    country: Mapped[str] = mapped_column(String(64), default="")
    blurb: Mapped[str] = mapped_column(Text, default="")

    heads: Mapped[list["ClubHead"]] = relationship(back_populates="brand")
    shafts: Mapped[list["Shaft"]] = relationship(back_populates="brand")


class ClubHead(Base):
    __tablename__ = "club_heads"
    __table_args__ = (UniqueConstraint("brand_id", "model", name="uq_head_brand_model"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    club_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    launch: Mapped[str] = mapped_column(String(16), default="mid")
    spin: Mapped[str] = mapped_column(String(16), default="mid")
    offset: Mapped[str] = mapped_column(String(16), default="mid")
    lofts: Mapped[list] = mapped_column(JSON)
    standard_loft: Mapped[float | None] = mapped_column(Float)
    pw_loft: Mapped[float | None] = mapped_column(Float)
    set_makeup: Mapped[str | None] = mapped_column(String(16))
    year: Mapped[int | None] = mapped_column(Integer)
    blurb: Mapped[str] = mapped_column(Text, default="")

    brand: Mapped[Brand] = relationship(back_populates="heads")


class Shaft(Base):
    __tablename__ = "shafts"
    __table_args__ = (UniqueConstraint("brand_id", "model", name="uq_shaft_brand_model"),)

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    families: Mapped[list] = mapped_column(JSON)
    profile: Mapped[str] = mapped_column(String(16), nullable=False)
    launch: Mapped[str] = mapped_column(String(16), default="mid")
    spin: Mapped[str] = mapped_column(String(16), default="mid")
    flex_weights: Mapped[dict] = mapped_column(JSON)
    torque: Mapped[float | None] = mapped_column(Float)
    blurb: Mapped[str] = mapped_column(Text, default="")

    brand: Mapped[Brand] = relationship(back_populates="shafts")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    # Both columns may be Fernet-sealed. They contain the medical flags.
    profile_snapshot: Mapped[dict | None] = mapped_column(JSON)
    result: Mapped[dict | None] = mapped_column(JSON)
    taken_to_fitter: Mapped[bool] = mapped_column(Boolean, default=False)
    rating: Mapped[int | None] = mapped_column(Integer)
    fitter_notes: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User | None] = relationship(back_populates="recommendations")
