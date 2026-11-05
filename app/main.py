"""Fairway Ledger API and fitting desk."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.routes import router as api_router
from app.db import init_db
from app.seed import seed
from app.settings import medical_storage
from app.web.routes import router as web_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Path(__file__).resolve().parent.parent.joinpath("data").mkdir(exist_ok=True)
    init_db()
    seed()
    yield


app = FastAPI(
    title="Fairway Ledger",
    version=__version__,
    summary="Auditable golf-club recommendations for a fitting desk.",
    description=(
        "Rule-based fitting for a full bag. Three houses in v1: Titleist, "
        "TaylorMade, Callaway. Every recommendation explains flex, length, lie, "
        "grip and the medical adjustments that ran last.\n\n"
        f"Medical storage on this process: **{medical_storage()}**. "
        "Set MEDICAL_FERNET_KEY before pointing the app at a shared database. "
        "Do not log request bodies.\n\n"
        "Authenticate with `Authorization: Bearer` or the `access_token` cookie "
        "set by login. Age, height and gender are the only required fitting inputs."
    ),
    lifespan=lifespan,
)
app.include_router(api_router)
app.include_router(web_router)
app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent / "static")), name="static")


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "version": __version__, "medical_storage": medical_storage()}
