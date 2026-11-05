"""Load the v1 catalog and a small sample of golfers. Safe to run twice.

    python -m app.seed
"""

from __future__ import annotations

import random

from sqlalchemy import select

from app.catalog.data import BRANDS, HEADS, SHAFTS
from app.db import init_db, session_factory
from app.fitting.profile import GolferProfile
from app.models import Brand, ClubHead, Profile, Recommendation, Shaft, User
from app.privacy import seal
from app.security import hash_password
from app.services import build_recommendation
from app.synthetic import sample_profile
from app.schemas import ProfileIn

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "FitSheet-demo-1"
SAMPLE_PASSWORD = "Sample-fit-10"


def _brand_id(name: str) -> str:
    return next(brand["id"] for brand in BRANDS if brand["name"] == name)


def upsert_catalog(session) -> None:
    for brand in BRANDS:
        row = session.get(Brand, brand["id"])
        if row is None:
            row = Brand(id=brand["id"])
            session.add(row)
        row.name = brand["name"]
        row.country = brand["country"]
        row.blurb = brand["blurb"]
    session.flush()

    for head in HEADS:
        row = session.get(ClubHead, head["id"])
        if row is None:
            row = ClubHead(id=head["id"], brand_id=_brand_id(head["brand"]), model=head["model"])
            session.add(row)
        row.brand_id = _brand_id(head["brand"])
        row.model = head["model"]
        row.club_type = head["club_type"]
        row.category = head["category"]
        row.launch = head["launch"]
        row.spin = head["spin"]
        row.offset = head["offset"]
        row.lofts = head["lofts"]
        row.standard_loft = head["standard_loft"]
        row.pw_loft = head["pw_loft"]
        row.set_makeup = head["set_makeup"]
        row.year = head["year"]
        row.blurb = head["blurb"]

    for shaft in SHAFTS:
        row = session.get(Shaft, shaft["id"])
        if row is None:
            row = Shaft(id=shaft["id"], brand_id=_brand_id(shaft["brand"]), model=shaft["model"])
            session.add(row)
        row.brand_id = _brand_id(shaft["brand"])
        row.model = shaft["model"]
        row.families = shaft["families"]
        row.profile = shaft["profile"]
        row.launch = shaft["launch"]
        row.spin = shaft["spin"]
        row.flex_weights = shaft["flex_weights"]
        row.torque = shaft["torque"]
        row.blurb = shaft["blurb"]
    session.commit()


def _ensure_user(session, email: str, password: str, profile: GolferProfile, with_fit: bool) -> None:
    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, password_hash=hash_password(password))
        session.add(user)
        session.flush()
    if user.profile is None:
        data = profile.to_dict()
        flags = data.pop("medical_flags")
        notes = data.pop("medical_notes")
        row = Profile(
            user_id=user.id,
            medical_flags=seal(flags),
            medical_notes=seal(notes) if notes else None,
            **data,
        )
        session.add(row)
        session.commit()
        if with_fit:
            build_recommendation(
                session,
                user,
                ProfileIn(**profile.to_dict()),
                save=True,
            )
    else:
        session.commit()


def seed() -> None:
    init_db()
    session = session_factory()()
    try:
        upsert_catalog(session)
        _ensure_user(
            session,
            DEMO_EMAIL,
            DEMO_PASSWORD,
            GolferProfile(
                age=46,
                height_cm=180,
                weight_kg=86,
                gender="male",
                body_type="average",
                wrist_to_floor_cm=89,
                handicap=14,
                fitness_level=3,
                squat_kg=100,
                preferred_brands=["Titleist"],
                current_brand="Callaway",
            ),
            with_fit=True,
        )
        rng = random.Random(7)
        for index in range(1, 11):
            _ensure_user(
                session,
                f"sample{index:02d}@example.com",
                SAMPLE_PASSWORD,
                sample_profile(rng),
                with_fit=False,
            )
        count = session.scalar(select(Recommendation.id))
        del count
    finally:
        session.close()


if __name__ == "__main__":
    seed()
    print("Catalog and sample golfers are in the database.")
    print(f"Demo login: {DEMO_EMAIL} / {DEMO_PASSWORD}")
