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
from app.units import cm_to_ft_in, cm_to_inches, ft_in_to_cm, inches_to_cm, kg_to_lb, lb_to_kg

# Stored as-is. Body size is converted to the metric columns.
_PASSTHROUGH = (
    "age",
    "gender",
    "body_type",
    "vo2_max",
    "resting_hr",
    "fitness_level",
    "handicap",
    "swing_speed_mph",
    "current_brand",
    "preferred_brands",
)


def profile_to_golfer(data: ProfileIn) -> GolferProfile:
    if data.age is None or data.height_ft is None or not data.gender:
        raise HTTPException(
            status_code=422,
            detail="Age, height, and gender are required to build a fitting.",
        )
    height_cm = ft_in_to_cm(data.height_ft, data.height_in or 0)
    if not 122 <= height_cm <= 220:
        raise HTTPException(status_code=422, detail="Height must be between 4'0\" and 7'2\".")
    return GolferProfile(
        age=data.age,
        height_cm=height_cm,
        gender=data.gender,
        weight_kg=lb_to_kg(data.weight_lb) if data.weight_lb else None,
        body_type=data.body_type,
        wrist_to_floor_cm=inches_to_cm(data.wrist_to_floor_in) if data.wrist_to_floor_in else None,
        hand_size_cm=inches_to_cm(data.hand_size_in) if data.hand_size_in else None,
        bench_press_kg=lb_to_kg(data.bench_press_lb) if data.bench_press_lb else None,
        squat_kg=lb_to_kg(data.squat_lb) if data.squat_lb else None,
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


def _metric_updates(data: ProfileIn) -> dict:
    """Map a US-unit profile onto the metric columns. Only sent fields are written."""
    sent = data.model_fields_set
    updates: dict = {}
    if "height_ft" in sent or "height_in" in sent:
        if data.height_ft is None:
            updates["height_cm"] = None
        else:
            updates["height_cm"] = ft_in_to_cm(data.height_ft, data.height_in or 0)
    if "weight_lb" in sent:
        updates["weight_kg"] = lb_to_kg(data.weight_lb) if data.weight_lb else None
    if "wrist_to_floor_in" in sent:
        updates["wrist_to_floor_cm"] = (
            inches_to_cm(data.wrist_to_floor_in) if data.wrist_to_floor_in else None
        )
    if "hand_size_in" in sent:
        updates["hand_size_cm"] = inches_to_cm(data.hand_size_in) if data.hand_size_in else None
    if "bench_press_lb" in sent:
        updates["bench_press_kg"] = lb_to_kg(data.bench_press_lb) if data.bench_press_lb else None
    if "squat_lb" in sent:
        updates["squat_kg"] = lb_to_kg(data.squat_lb) if data.squat_lb else None
    for key in _PASSTHROUGH:
        if key in sent:
            updates[key] = getattr(data, key)
    return updates


def upsert_profile(session: Session, user: User, data: ProfileIn) -> Profile:
    row = session.scalar(select(Profile).where(Profile.user_id == user.id))
    if row is None:
        row = Profile(user_id=user.id)
        session.add(row)
    for key, value in _metric_updates(data).items():
        setattr(row, key, value)
    if "medical_flags" in data.model_fields_set:
        row.medical_flags = seal(data.medical_flags or [])
    if "medical_notes" in data.model_fields_set:
        row.medical_notes = seal(data.medical_notes) if data.medical_notes else None
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
    height_ft, height_in = cm_to_ft_in(row.height_cm) if row.height_cm else (None, None)
    return {
        "age": row.age,
        "height_ft": height_ft,
        "height_in": height_in,
        "gender": row.gender,
        "weight_lb": kg_to_lb(row.weight_kg) if row.weight_kg else None,
        "body_type": row.body_type,
        "wrist_to_floor_in": cm_to_inches(row.wrist_to_floor_cm) if row.wrist_to_floor_cm else None,
        "hand_size_in": cm_to_inches(row.hand_size_cm) if row.hand_size_cm else None,
        "bench_press_lb": kg_to_lb(row.bench_press_kg) if row.bench_press_kg else None,
        "squat_lb": kg_to_lb(row.squat_kg) if row.squat_kg else None,
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


def profile_in_from_golfer(profile: GolferProfile) -> ProfileIn:
    """Build an API profile from the metric engine profile. Used by the seed."""
    golfer = profile.normalized()
    feet, inches = cm_to_ft_in(golfer.height_cm)
    return ProfileIn(
        age=golfer.age,
        height_ft=feet,
        height_in=inches,
        gender=golfer.gender,
        weight_lb=kg_to_lb(golfer.weight_kg) if golfer.weight_kg else None,
        body_type=golfer.body_type,
        wrist_to_floor_in=cm_to_inches(golfer.wrist_to_floor_cm) if golfer.wrist_to_floor_cm else None,
        hand_size_in=cm_to_inches(golfer.hand_size_cm) if golfer.hand_size_cm else None,
        bench_press_lb=kg_to_lb(golfer.bench_press_kg) if golfer.bench_press_kg else None,
        squat_lb=kg_to_lb(golfer.squat_kg) if golfer.squat_kg else None,
        vo2_max=golfer.vo2_max,
        resting_hr=golfer.resting_hr,
        fitness_level=golfer.fitness_level,
        handicap=golfer.handicap,
        swing_speed_mph=golfer.swing_speed_mph,
        current_brand=golfer.current_brand,
        preferred_brands=list(golfer.preferred_brands or []),
        medical_flags=list(golfer.medical_flags or []),
        medical_notes=golfer.medical_notes,
    )


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
