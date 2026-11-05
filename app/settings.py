"""Environment configuration. No secrets are baked into source.

Production must set DATABASE_URL (PostgreSQL), JWT_SECRET, and
MEDICAL_FERNET_KEY. When MEDICAL_FERNET_KEY is absent, medical fields are
stored as ordinary JSON and the API reports medical_storage=plaintext so an
operator cannot miss it.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE = "sqlite:///" + str(ROOT / "data" / "golf_demo.db")


def database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_SQLITE)


def jwt_secret() -> str:
    return os.environ.get("JWT_SECRET", "dev-only-change-me")


def jwt_ttl_hours() -> int:
    return int(os.environ.get("JWT_TTL_HOURS", "168"))


def medical_fernet_key() -> str | None:
    key = os.environ.get("MEDICAL_FERNET_KEY", "").strip()
    return key or None


def medical_storage() -> str:
    return "fernet" if medical_fernet_key() else "plaintext"
