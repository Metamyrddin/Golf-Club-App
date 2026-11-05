"""Medical data at rest.

Flags and free-text notes are optional. When MEDICAL_FERNET_KEY is set
(urlsafe Fernet key), sensitive JSON is stored as {"_sealed": "<token>"} and
decrypted only inside the request that owns the row. Recommendation snapshots
are sealed the same way because they quote the medical flags in the rationale.

Without a key the payload is stored in clear JSON. That is acceptable for a
local demo and is not acceptable for a shared production database — set the
key, restrict DB access, and do not log request bodies.
"""

from __future__ import annotations

import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.settings import medical_fernet_key


def _fernet() -> Fernet | None:
    key = medical_fernet_key()
    if not key:
        return None
    return Fernet(key.encode() if isinstance(key, str) else key)


def seal(data: Any) -> Any:
    """Return a JSON-serialisable form of ``data`` safe to put in a JSON column."""
    if data is None:
        return None
    fernet = _fernet()
    if fernet is None:
        return data
    token = fernet.encrypt(json.dumps(data).encode("utf-8")).decode("utf-8")
    return {"_sealed": token}


def open_sealed(data: Any) -> Any:
    """Reverse :func:`seal`. Plain JSON (no key, or legacy rows) passes through."""
    if not isinstance(data, dict) or "_sealed" not in data:
        return data
    fernet = _fernet()
    if fernet is None:
        raise RuntimeError(
            "Row is sealed but MEDICAL_FERNET_KEY is not set. "
            "Refusing to return medical data rather than guess."
        )
    try:
        raw = fernet.decrypt(data["_sealed"].encode("utf-8"))
    except InvalidToken as exc:
        raise RuntimeError("Medical payload could not be decrypted with the current key.") from exc
    return json.loads(raw.decode("utf-8"))
