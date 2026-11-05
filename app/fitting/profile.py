"""Normalised golfer profile. Every field except age, height and gender is optional."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


def normalize_gender(value: str | None) -> str:
    key = (value or "").strip().lower()
    if key in {"m", "male", "man"}:
        return "male"
    if key in {"f", "female", "woman", "w"}:
        return "female"
    return "unspecified"


def normalize_body_type(value: str | None) -> str | None:
    if not value:
        return None
    key = value.strip().lower()
    aliases = {
        "ecto": "ectomorph",
        "ectomorph": "ectomorph",
        "lean": "ectomorph",
        "meso": "mesomorph",
        "mesomorph": "mesomorph",
        "athletic": "athletic",
        "average": "average",
        "muscular": "athletic",
        "endo": "endomorph",
        "endomorph": "endomorph",
        "heavy": "heavy",
        "stocky": "heavy",
    }
    return aliases.get(key, key)


@dataclass
class GolferProfile:
    age: int
    height_cm: float
    gender: str
    weight_kg: float | None = None
    body_type: str | None = None
    wrist_to_floor_cm: float | None = None
    hand_size_cm: float | None = None
    bench_press_kg: float | None = None
    squat_kg: float | None = None
    vo2_max: float | None = None
    resting_hr: float | None = None
    fitness_level: int | None = None
    handicap: float | None = None
    swing_speed_mph: float | None = None
    current_brand: str | None = None
    preferred_brands: list[str] = field(default_factory=list)
    medical_flags: list[str] = field(default_factory=list)
    medical_notes: str | None = None

    def normalized(self) -> GolferProfile:
        return GolferProfile(
            age=int(self.age),
            height_cm=float(self.height_cm),
            gender=normalize_gender(self.gender),
            weight_kg=_pos(self.weight_kg),
            body_type=normalize_body_type(self.body_type),
            wrist_to_floor_cm=_pos(self.wrist_to_floor_cm),
            hand_size_cm=_pos(self.hand_size_cm),
            bench_press_kg=_pos(self.bench_press_kg),
            squat_kg=_pos(self.squat_kg),
            vo2_max=_pos(self.vo2_max),
            resting_hr=_pos(self.resting_hr),
            fitness_level=int(self.fitness_level) if self.fitness_level else None,
            handicap=float(self.handicap) if self.handicap is not None else None,
            swing_speed_mph=_pos(self.swing_speed_mph),
            current_brand=(self.current_brand or None),
            preferred_brands=[b for b in (self.preferred_brands or []) if b],
            medical_flags=_flags(self.medical_flags),
            medical_notes=(self.medical_notes or None),
        )

    def to_dict(self) -> dict:
        return asdict(self.normalized())


def _pos(value: float | None) -> float | None:
    if value is None:
        return None
    number = float(value)
    if number <= 0:
        return None
    return number


def _flags(flags: list[str] | None) -> list[str]:
    cleaned: list[str] = []
    for flag in flags or []:
        key = flag.strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "shoulder": "shoulder",
            "shoulders": "shoulder",
            "rotator": "shoulder",
            "rotator_cuff": "shoulder",
            "back": "back",
            "lumbar": "back",
            "low_back": "back",
            "spine": "back",
            "wrist": "wrist",
            "wrists": "wrist",
            "elbow": "elbow",
            "golfers_elbow": "elbow",
            "tennis_elbow": "elbow",
            "arthritis": "arthritis",
            "osteoarthritis": "arthritis",
            "low_bone_density": "low_bone_density",
            "osteoporosis": "low_bone_density",
            "osteopenia": "low_bone_density",
            "bone_density": "low_bone_density",
        }
        name = aliases.get(key)
        if name and name not in cleaned:
            cleaned.append(name)
    return cleaned
