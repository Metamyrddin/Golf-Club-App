"""Auth dependencies. Cookie or bearer token, same JWT."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import db_session
from app.models import User
from app.security import decode_access_token

bearer = HTTPBearer(auto_error=False)


def get_db(session: Session = Depends(db_session)) -> Session:
    return session


def _token_from_request(
    request: Request, credentials: HTTPAuthorizationCredentials | None
) -> str | None:
    if credentials and credentials.scheme.lower() == "bearer":
        return credentials.credentials
    return request.cookies.get("access_token")


def current_user_optional(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: Session = Depends(get_db),
) -> User | None:
    token = _token_from_request(request, credentials)
    if not token:
        return None
    user_id = decode_access_token(token)
    if not user_id:
        return None
    return session.get(User, user_id)


def current_user(user: User | None = Depends(current_user_optional)) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="Login required.")
    return user
