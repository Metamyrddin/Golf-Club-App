"""HTML fitting desk. The API remains the source of record; these pages post into it."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session
from pathlib import Path

from app.api.deps import current_user_optional, get_db
from app.catalog.data import BRANDS
from app.fitting.rulebook import RULES
from app.models import Brand, ClubHead, Shaft, User
from app.schemas import LoginIn, ProfileIn, RegisterIn
from app.security import create_access_token, hash_password, verify_password
from app.services import (
    build_recommendation,
    load_recommendation,
    profile_out,
    public_recommendation,
    upsert_profile,
)
from sqlalchemy import func, select

from app.models import Recommendation

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

DEMOS: dict[str, dict] = {
    "average": {
        "age": 46,
        "height_ft": 5,
        "height_in": 11,
        "weight_lb": 190,
        "gender": "male",
        "body_type": "average",
        "wrist_to_floor_in": 35,
        "handicap": 14,
        "fitness_level": 3,
        "squat_lb": 220,
        "preferred_brands": ["Titleist"],
        "current_brand": "Callaway",
        "medical_flags": [],
    },
    "strong": {
        "age": 24,
        "height_ft": 6,
        "height_in": 1,
        "weight_lb": 181,
        "gender": "male",
        "body_type": "athletic",
        "wrist_to_floor_in": 36.2,
        "handicap": 2,
        "fitness_level": 5,
        "squat_lb": 375,
        "bench_press_lb": 265,
        "preferred_brands": ["TaylorMade"],
        "medical_flags": [],
    },
    "senior": {
        "age": 74,
        "height_ft": 5,
        "height_in": 8,
        "weight_lb": 172,
        "gender": "male",
        "body_type": "average",
        "handicap": 22,
        "preferred_brands": [],
        "medical_flags": [],
    },
    "injured": {
        "age": 52,
        "height_ft": 5,
        "height_in": 6,
        "weight_lb": 163,
        "gender": "female",
        "body_type": "average",
        "wrist_to_floor_in": 32,
        "handicap": 18,
        "fitness_level": 2,
        "preferred_brands": ["Callaway"],
        "medical_flags": ["shoulder", "arthritis"],
        "medical_notes": "Cleared to play. Shoulder is the left, lead side.",
    },
}


def _ctx(request: Request, user: User | None, **extra):
    return {
        "request": request,
        "user": user,
        "brands": [brand["name"] for brand in BRANDS if brand.get("has_driver")],
        **extra,
    }


def _profile_from_form(form) -> ProfileIn:
    def optional(name: str, cast):
        raw = (form.get(name) or "").strip()
        if raw == "":
            return None
        return cast(raw)

    flags = [value for value in form.getlist("medical_flags") if value]
    brands = [value for value in form.getlist("preferred_brands") if value]
    return ProfileIn(
        age=optional("age", int),
        height_ft=optional("height_ft", int),
        height_in=optional("height_in", float),
        weight_lb=optional("weight_lb", float),
        gender=(form.get("gender") or "").strip() or None,
        body_type=(form.get("body_type") or "").strip() or None,
        wrist_to_floor_in=optional("wrist_to_floor_in", float),
        hand_size_in=optional("hand_size_in", float),
        bench_press_lb=optional("bench_press_lb", float),
        squat_lb=optional("squat_lb", float),
        vo2_max=optional("vo2_max", float),
        resting_hr=optional("resting_hr", float),
        fitness_level=optional("fitness_level", int),
        handicap=optional("handicap", float),
        swing_speed_mph=optional("swing_speed_mph", float),
        current_brand=(form.get("current_brand") or "").strip() or None,
        preferred_brands=brands,
        medical_flags=flags,
        medical_notes=(form.get("medical_notes") or "").strip() or None,
    )


def _form_dict(data: ProfileIn) -> dict:
    return data.model_dump()


@router.get("/")
def home(
    request: Request,
    demo: str | None = None,
    user: User | None = Depends(current_user_optional),
):
    form = DEMOS.get(demo or "", {})
    return templates.TemplateResponse(
        request,
        "home.html",
        _ctx(request, user, form=form, error=None, demo=demo),
    )


@router.post("/fit")
async def fit(
    request: Request,
    user: User | None = Depends(current_user_optional),
    session: Session = Depends(get_db),
):
    form = await request.form()
    try:
        data = _profile_from_form(form)
    except (ValidationError, ValueError) as exc:
        return templates.TemplateResponse(
            request,
            "home.html",
            _ctx(request, user, form=dict(form), error=str(exc), demo=None),
            status_code=422,
        )
    try:
        _rec_id, result = build_recommendation(session, user, data, save=True)
    except HTTPException as exc:
        return templates.TemplateResponse(
            request,
            "home.html",
            _ctx(request, user, form=_form_dict(data), error=exc.detail, demo=None),
            status_code=exc.status_code,
        )
    return templates.TemplateResponse(
        request,
        "results.html",
        _ctx(request, user, result=result, error=None),
    )


@router.get("/catalog")
def catalog_page(
    request: Request,
    user: User | None = Depends(current_user_optional),
    session: Session = Depends(get_db),
):
    brands = session.scalars(select(Brand).order_by(Brand.name)).all()
    heads = session.scalars(select(ClubHead).order_by(ClubHead.club_type, ClubHead.model)).all()
    shafts = session.scalars(select(Shaft).order_by(Shaft.model)).all()
    return templates.TemplateResponse(
        request,
        "catalog.html",
        _ctx(request, user, brand_rows=brands, heads=heads, shafts=shafts),
    )


@router.get("/rules")
def rules_page(request: Request, user: User | None = Depends(current_user_optional)):
    return templates.TemplateResponse(
        request,
        "rules.html",
        _ctx(request, user, rules=[{"id": key, "text": text} for key, text in RULES.items()]),
    )


@router.get("/saved")
def saved(
    request: Request,
    user: User | None = Depends(current_user_optional),
    session: Session = Depends(get_db),
):
    rows = []
    if user is not None:
        found = session.scalars(
            select(Recommendation)
            .where(Recommendation.user_id == user.id)
            .order_by(Recommendation.created_at.desc())
        ).all()
        rows = [public_recommendation(row) for row in found]
    return templates.TemplateResponse(request, "saved.html", _ctx(request, user, rows=rows))


@router.get("/sheet/{rec_id}")
def sheet(
    rec_id: str,
    request: Request,
    user: User | None = Depends(current_user_optional),
    session: Session = Depends(get_db),
):
    try:
        result = public_recommendation(load_recommendation(session, rec_id, user))
    except HTTPException:
        return templates.TemplateResponse(
            request, "home.html", _ctx(request, user, form={}, error="That sheet is not available.", demo=None), status_code=404
        )
    return templates.TemplateResponse(request, "results.html", _ctx(request, user, result=result))


@router.get("/login")
def login_page(request: Request, user: User | None = Depends(current_user_optional)):
    return templates.TemplateResponse(request, "auth.html", _ctx(request, user, mode="login", error=None))


@router.post("/login")
def login_submit(
    request: Request,
    email: str = Form(),
    password: str = Form(),
    session: Session = Depends(get_db),
):
    from app.models import User as UserModel

    user = session.scalar(select(UserModel).where(func.lower(UserModel.email) == email.lower().strip()))
    if user is None or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request,
            "auth.html",
            _ctx(request, None, mode="login", error="Email or password is wrong."),
            status_code=401,
        )
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        "access_token",
        create_access_token(user.id),
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
        path="/",
    )
    return response


@router.get("/register")
def register_page(request: Request, user: User | None = Depends(current_user_optional)):
    return templates.TemplateResponse(request, "auth.html", _ctx(request, user, mode="register", error=None))


@router.post("/register")
def register_submit(
    request: Request,
    email: str = Form(),
    password: str = Form(),
    session: Session = Depends(get_db),
):
    try:
        body = RegisterIn(email=email, password=password)
    except ValidationError as exc:
        return templates.TemplateResponse(
            request,
            "auth.html",
            _ctx(request, None, mode="register", error="Use a real email and a password of at least 8 characters."),
            status_code=422,
        )
    existing = session.scalar(select(User).where(func.lower(User.email) == body.email.lower()))
    if existing:
        return templates.TemplateResponse(
            request,
            "auth.html",
            _ctx(request, None, mode="register", error="That email is already registered."),
            status_code=409,
        )
    user = User(email=body.email.lower(), password_hash=hash_password(body.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        "access_token",
        create_access_token(user.id),
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
        path="/",
    )
    return response


@router.post("/logout")
def logout() -> RedirectResponse:
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("access_token", path="/")
    return response


@router.post("/profile")
async def save_profile(
    request: Request,
    user: User | None = Depends(current_user_optional),
    session: Session = Depends(get_db),
):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    form = await request.form()
    try:
        data = _profile_from_form(form)
    except (ValidationError, ValueError):
        return templates.TemplateResponse(
            request,
            "home.html",
            _ctx(request, user, form=dict(form), error="Check the numbers and try again.", demo=None),
            status_code=422,
        )
    upsert_profile(session, user, data)
    return RedirectResponse("/saved", status_code=303)


@router.get("/account")
def account(
    request: Request,
    user: User | None = Depends(current_user_optional),
    session: Session = Depends(get_db),
):
    profile = None
    if user is not None and user.profile is not None:
        profile = profile_out(user.profile)
    return templates.TemplateResponse(request, "account.html", _ctx(request, user, profile=profile))
