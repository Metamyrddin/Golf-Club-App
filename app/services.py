"""Profile persistence and recommendation records."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.fitting.engine import recommend
from app.fitting.profile import GolferProfile
from app.models import Profile, Recommendation, User
from app.privacy import open_sealed, seal
from app.schemas import ProfileIn
from app.settings import medical_storage


def profile_to_golfer(data: ProfileIn) -> GolferProfile:
    if data.age is None or data.height_cm is None or not data.gender:
        raise HTTPException(
            status_code=422,
            detail="age, height_cm and gender are required to build a fitting.",
        )
    return GolferProfile(
        age=data.age,
        height_cm=data.height_cm,
        gender=data.gender,
        weight_kg=data.weight_kg,
        body_type=data.body_type,
        wrist_to_floor_cm=data.wrist_to_floor_cm,
        hand_size_cm=data.hand_size_cm,
        bench_press_kg=data.bench_press_kg,
        squat_kg=data.squat_kg,
        vo2_max=data.vo2_max,
        resting_hr=data.resting_hr,
        fitness_level=data.fitness_level,
        handicap=data.handicap,
        swing_speed_mph=data.swing_speed_mph,
        current_brand=data.current_brand,
        preferred_brands=list(data.preferred_brands or []),
        medical_flags=list(data.medical_flags or []),
        medical_notes=data.medical_notes,
    )


def upsert_profile(session: Session, user: User, data: ProfileIn) -> Profile:
    row = session.scalar(select(Profile).where(Profile.user_id == user.id))
    if row is None:
        row = Profile(user_id=user.id)
        session.add(row)
    payload = data.model_dump(exclude_unset=True)
    medical_flags = payload.pop("medical_flags", None)
    medical_notes = payload.pop("medical_notes", None)
    for key, value in payload.items():
        setattr(row, key, value)
    if "medical_flags" in data.model_fields_set or medical_flags is not None:
        # Always seal the list we were given when the client sent the field.
        if "medical_flags" in data.model_fields_set:
            row.medical_flags = seal(medical_flags or [])
    if "medical_notes" in data.model_fields_set:
        row.medical_notes = seal(medical_notes) if medical_notes else None
    session.commit()
    session.refresh(row)
    return row


def profile_out(row: Profile) -> dict:
    flags = open_sealed(row.medical_flags) if row.medical_flags is not None else []
    notes = open_sealed(row.medical_notes) if row.medical_notes else None
    if not isinstance(flags, list):
        flags = []
    if not isinstance(notes, str):
        notes = None
    return {
        "age": row.age,
        "height_cm": row.height_cm,
        "gender": row.gender,
        "weight_kg": row.weight_kg,
        "body_type": row.body_type,
        "wrist_to_floor_cm": row.wrist_to_floor_cm,
        "hand_size_cm": row.hand_size_cm,
        "bench_press_kg": row.bench_press_kg,
        "squat_kg": row.squat_kg,
        "vo2_max": row.vo2_max,
        "resting_hr": row.resting_hr,
        "fitness_level": row.fitness_level,
        "handicap": row.handicap,
        "swing_speed_mph": row.swing_speed_mph,
        "current_brand": row.current_brand,
        "preferred_brands": row.preferred_brands or [],
        "medical_flags": flags,
        "medical_notes": notes,
        "medical_storage": medical_storage(),
    }


def profile_in_from_row(row: Profile) -> ProfileIn:
    return ProfileIn(**{k: v for k, v in profile_out(row).items() if k != "medical_storage"})


def build_recommendation(
    session: Session,
    user: User | None,
    data: ProfileIn,
    save: bool,
) -> tuple[str | None, dict]:
    result = recommend(profile_to_golfer(data))
    rec_id = None
    if save:
        row = Recommendation(
            user_id=user.id if user else None,
            profile_snapshot=seal(data.model_dump()),
            result=seal(result),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        rec_id = row.id
    result = dict(result)
    result["id"] = rec_id
    result["medical_storage"] = medical_storage()
    return rec_id, result


def load_recommendation(session: Session, rec_id: str, user: User | None) -> Recommendation:
    row = session.get(Recommendation, rec_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Recommendation not found.")
    if row.user_id and (user is None or row.user_id != user.id):
        raise HTTPException(status_code=404, detail="Recommendation not found.")
    return row


def public_recommendation(row: Recommendation) -> dict:
    result = open_sealed(row.result)
    result = dict(result)
    result["id"] = row.id
    result["created_at"] = row.created_at.isoformat()
    result["taken_to_fitter"] = row.taken_to_fitter
    result["rating"] = row.rating
    result["fitter_notes"] = row.fitter_notes
    result["medical_storage"] = medical_storage()
    return result
