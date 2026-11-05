"""REST surface. The OpenAPI schema is generated from these routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user, current_user_optional, get_db
from app.catalog.data import get_catalog
from app.exporting import recommendation_csv, recommendation_pdf
from app.fitting.rulebook import RULES
from app.models import Brand, ClubHead, Recommendation, Shaft, User
from app.schemas import (
    FeedbackIn,
    FeedbackOut,
    LoginIn,
    ProfileIn,
    ProfileOut,
    RecommendIn,
    RegisterIn,
    TokenOut,
    UserOut,
)
from app.security import create_access_token, hash_password, verify_password
from app.services import (
    build_recommendation,
    load_recommendation,
    profile_in_from_row,
    profile_out,
    public_recommendation,
    upsert_profile,
)
from app.settings import medical_storage

router = APIRouter(prefix="/api")


def _token_response(user: User, response: Response) -> TokenOut:
    token = create_access_token(user.id)
    # Browser UI reads the cookie. API clients read the JSON body.
    response.set_cookie(
        "access_token",
        token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
        path="/",
    )
    return TokenOut(access_token=token, medical_storage=medical_storage())


@router.post("/auth/register", response_model=TokenOut, tags=["auth"])
def register(body: RegisterIn, response: Response, session: Session = Depends(get_db)) -> TokenOut:
    email = body.email.lower()
    existing = session.scalar(select(User).where(func.lower(User.email) == email))
    if existing:
        raise HTTPException(status_code=409, detail="An account with that email already exists.")
    user = User(email=email, password_hash=hash_password(body.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return _token_response(user, response)


@router.post("/auth/login", response_model=TokenOut, tags=["auth"])
def login(body: LoginIn, response: Response, session: Session = Depends(get_db)) -> TokenOut:
    user = session.scalar(select(User).where(func.lower(User.email) == body.email.lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is wrong.")
    return _token_response(user, response)


@router.post("/auth/logout", tags=["auth"])
def logout(response: Response) -> dict:
    response.delete_cookie("access_token", path="/")
    return {"ok": True}


@router.get("/auth/me", response_model=UserOut, tags=["auth"])
def me(user: User = Depends(current_user)) -> User:
    return user


@router.get("/profile", response_model=ProfileOut, tags=["profile"])
def get_profile(user: User = Depends(current_user), session: Session = Depends(get_db)) -> dict:
    if user.profile is None:
        raise HTTPException(status_code=404, detail="No profile yet.")
    # relationship may be expired; reload
    session.refresh(user)
    if user.profile is None:
        raise HTTPException(status_code=404, detail="No profile yet.")
    return profile_out(user.profile)


@router.put("/profile", response_model=ProfileOut, tags=["profile"])
def put_profile(
    body: ProfileIn,
    user: User = Depends(current_user),
    session: Session = Depends(get_db),
) -> dict:
    row = upsert_profile(session, user, body)
    return profile_out(row)


@router.post("/recommendations", tags=["recommendations"])
def create_recommendation(
    body: RecommendIn,
    user: User | None = Depends(current_user_optional),
    session: Session = Depends(get_db),
) -> dict:
    if body.use_saved_profile:
        if user is None or user.profile is None:
            raise HTTPException(status_code=400, detail="No saved profile to fit from. Log in and save one.")
        data = profile_in_from_row(user.profile)
    elif body.profile is not None:
        data = body.profile
    else:
        raise HTTPException(status_code=422, detail="Provide a profile or set use_saved_profile.")
    _rec_id, result = build_recommendation(session, user, data, save=body.save)
    return result


@router.get("/recommendations", tags=["recommendations"])
def list_recommendations(
    user: User = Depends(current_user),
    session: Session = Depends(get_db),
) -> list[dict]:
    rows = session.scalars(
        select(Recommendation)
        .where(Recommendation.user_id == user.id)
        .order_by(Recommendation.created_at.desc())
    ).all()
    summary = []
    for row in rows:
        result = public_recommendation(row)
        target = result["target"]
        summary.append(
            {
                "id": row.id,
                "created_at": result["created_at"],
                "flex": target["flex"],
                "swing_speed_mph": target["swing_speed_mph"],
                "head_category": target["head_category"],
                "taken_to_fitter": row.taken_to_fitter,
                "rating": row.rating,
                "brands": [bag["brand"] for bag in result["sets"]],
            }
        )
    return summary


@router.get("/recommendations/{rec_id}", tags=["recommendations"])
def get_recommendation(
    rec_id: str,
    user: User | None = Depends(current_user_optional),
    session: Session = Depends(get_db),
) -> dict:
    return public_recommendation(load_recommendation(session, rec_id, user))


@router.post("/recommendations/{rec_id}/feedback", response_model=FeedbackOut, tags=["recommendations"])
def feedback(
    rec_id: str,
    body: FeedbackIn,
    user: User = Depends(current_user),
    session: Session = Depends(get_db),
) -> FeedbackOut:
    row = load_recommendation(session, rec_id, user)
    if row.user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the owner can record fitter feedback.")
    if body.taken_to_fitter is not None:
        row.taken_to_fitter = body.taken_to_fitter
    if body.rating is not None:
        row.rating = body.rating
    if body.fitter_notes is not None:
        row.fitter_notes = body.fitter_notes
    session.commit()
    return FeedbackOut(
        id=row.id,
        taken_to_fitter=row.taken_to_fitter,
        rating=row.rating,
        fitter_notes=row.fitter_notes,
    )


@router.get("/recommendations/{rec_id}/export.csv", tags=["export"])
def export_csv(
    rec_id: str,
    user: User | None = Depends(current_user_optional),
    session: Session = Depends(get_db),
) -> Response:
    result = public_recommendation(load_recommendation(session, rec_id, user))
    return Response(
        content=recommendation_csv(result),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="fitting-{rec_id}.csv"'},
    )


@router.get("/recommendations/{rec_id}/export.pdf", tags=["export"])
def export_pdf(
    rec_id: str,
    user: User | None = Depends(current_user_optional),
    session: Session = Depends(get_db),
) -> Response:
    result = public_recommendation(load_recommendation(session, rec_id, user))
    return Response(
        content=recommendation_pdf(result),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="fitting-{rec_id}.pdf"'},
    )


@router.get("/recommendations/{rec_id}/export.json", tags=["export"])
def export_json(
    rec_id: str,
    user: User | None = Depends(current_user_optional),
    session: Session = Depends(get_db),
) -> dict:
    return public_recommendation(load_recommendation(session, rec_id, user))


@router.get("/catalog/brands", tags=["catalog"])
def catalog_brands(session: Session = Depends(get_db)) -> list[dict]:
    rows = session.scalars(select(Brand).order_by(Brand.name)).all()
    return [
        {"id": row.id, "name": row.name, "country": row.country, "blurb": row.blurb}
        for row in rows
    ]


@router.get("/catalog/heads", tags=["catalog"])
def catalog_heads(
    brand: str | None = None,
    club_type: str | None = None,
    session: Session = Depends(get_db),
) -> list[dict]:
    query = select(ClubHead, Brand).join(Brand, ClubHead.brand_id == Brand.id)
    if brand:
        query = query.where(Brand.name == brand)
    if club_type:
        query = query.where(ClubHead.club_type == club_type)
    rows = session.execute(query.order_by(Brand.name, ClubHead.club_type)).all()
    return [
        {
            "id": head.id,
            "brand": brand_row.name,
            "model": head.model,
            "club_type": head.club_type,
            "category": head.category,
            "launch": head.launch,
            "spin": head.spin,
            "lofts": head.lofts,
            "standard_loft": head.standard_loft,
            "pw_loft": head.pw_loft,
            "set_makeup": head.set_makeup,
            "blurb": head.blurb,
        }
        for head, brand_row in rows
    ]


@router.get("/catalog/shafts", tags=["catalog"])
def catalog_shafts(brand: str | None = None, session: Session = Depends(get_db)) -> list[dict]:
    query = select(Shaft, Brand).join(Brand, Shaft.brand_id == Brand.id)
    if brand:
        query = query.where(Brand.name == brand)
    rows = session.execute(query.order_by(Brand.name, Shaft.model)).all()
    return [
        {
            "id": shaft.id,
            "brand": brand_row.name,
            "model": shaft.model,
            "families": shaft.families,
            "profile": shaft.profile,
            "launch": shaft.launch,
            "flex_weights": shaft.flex_weights,
            "torque": shaft.torque,
            "blurb": shaft.blurb,
        }
        for shaft, brand_row in rows
    ]


@router.get("/rules", tags=["rules"])
def rules() -> dict:
    """The fitting rulebook, in the same words a fitter sees in source."""
    return {"rules": [{"id": key, "text": text} for key, text in RULES.items()]}


@router.get("/catalog/source-counts", tags=["catalog"])
def source_counts() -> dict:
    """In-memory catalog size. Useful when checking a seed without guessing."""
    catalog = get_catalog()
    return {
        "brands": len(catalog["brands"]),
        "heads": len(catalog["heads"]),
        "shafts": len(catalog["shafts"]),
    }
