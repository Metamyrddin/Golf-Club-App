"""Request and response models. These drive the OpenAPI document."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    model_config = {
        "json_schema_extra": {
            "examples": [{"email": "ada@example.com", "password": "FitSheet-demo-1"}]
        }
    }


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    medical_storage: str


class UserOut(BaseModel):
    id: str
    email: EmailStr
    created_at: datetime


class ProfileIn(BaseModel):
    """All physical fields except age, height and gender are optional.

    Medical flags use a small controlled vocabulary:
    shoulder, back, wrist, elbow, arthritis, low_bone_density.
    """

    age: int | None = Field(default=None, ge=10, le=100)
    height_cm: float | None = Field(default=None, ge=122, le=220)
    gender: str | None = None
    weight_kg: float | None = Field(default=None, ge=35, le=200)
    body_type: str | None = None
    wrist_to_floor_cm: float | None = Field(default=None, ge=50, le=120)
    hand_size_cm: float | None = Field(default=None, ge=12, le=28)
    bench_press_kg: float | None = Field(default=None, ge=0, le=300)
    squat_kg: float | None = Field(default=None, ge=0, le=400)
    vo2_max: float | None = Field(default=None, ge=15, le=90)
    resting_hr: float | None = Field(default=None, ge=35, le=120)
    fitness_level: int | None = Field(default=None, ge=1, le=5)
    handicap: float | None = Field(default=None, ge=-8, le=54)
    swing_speed_mph: float | None = Field(default=None, ge=40, le=150)
    current_brand: str | None = None
    preferred_brands: list[str] = Field(default_factory=list)
    medical_flags: list[str] = Field(default_factory=list)
    medical_notes: str | None = Field(default=None, max_length=2000)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "age": 46,
                    "height_cm": 180,
                    "weight_kg": 86,
                    "gender": "male",
                    "body_type": "average",
                    "wrist_to_floor_cm": 89,
                    "handicap": 14,
                    "fitness_level": 3,
                    "preferred_brands": ["Titleist"],
                    "current_brand": "Callaway",
                    "medical_flags": [],
                }
            ]
        }
    }


class ProfileOut(ProfileIn):
    medical_storage: str


class RecommendIn(BaseModel):
    """Inline profile, or omit it and set use_saved_profile."""

    profile: ProfileIn | None = None
    use_saved_profile: bool = False
    save: bool = True


class FeedbackIn(BaseModel):
    taken_to_fitter: bool | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    fitter_notes: str | None = Field(default=None, max_length=2000)


class FeedbackOut(BaseModel):
    id: str
    taken_to_fitter: bool
    rating: int | None
    fitter_notes: str | None
