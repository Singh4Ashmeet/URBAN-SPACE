from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from fastapi import Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import RefreshToken, User

AUTH_ENABLED = os.environ.get("URBANSHIELD_AUTH_ENABLED", "true").lower() not in {"0", "false", "no", "off"}
AUTH_SECRET = os.environ.get("URBANSHIELD_AUTH_SECRET", "change-me-local-dev-only")
ACCESS_TOKEN_MINUTES = int(os.environ.get("URBANSHIELD_ACCESS_TOKEN_MINUTES", "45"))
REFRESH_TOKEN_DAYS = int(os.environ.get("URBANSHIELD_REFRESH_TOKEN_DAYS", "7"))
SEED_PASSWORD = os.environ.get("URBANSHIELD_SEED_PASSWORD", "UrbanShield123!")

ROLES = {"ADMIN", "OPERATOR", "AUDITOR", "VIEWER"}
MUTATION_ROLES = {"ADMIN", "OPERATOR"}
AUDIT_ROLES = {"ADMIN", "AUDITOR"}
ADMIN_ROLES = {"ADMIN"}

ph = PasswordHasher()


class UserOut(BaseModel):
    id: int
    username: str
    displayName: str
    role: str


class AuthResponse(BaseModel):
    accessToken: str
    refreshToken: str
    expiresAt: str
    user: UserOut


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refreshToken: str


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def _sign(payload: str) -> str:
    digest = hmac.new(AUTH_SECRET.encode("utf-8"), payload.encode("ascii"), hashlib.sha256).digest()
    return _b64url(digest)


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return ph.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError):
        return False


def refresh_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def user_to_out(user: User) -> UserOut:
    return UserOut(id=user.id, username=user.username, displayName=user.display_name, role=user.role)


def create_access_token(user: User) -> tuple[str, datetime]:
    expires_at = utcnow() + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user.username,
        "uid": user.id,
        "role": user.role,
        "type": "access",
        "exp": int(expires_at.timestamp()),
        "iat": int(utcnow().timestamp()),
    }
    signing_input = f"{_b64url(json.dumps(header, separators=(',', ':')).encode('utf-8'))}.{_b64url(json.dumps(payload, separators=(',', ':')).encode('utf-8'))}"
    return f"{signing_input}.{_sign(signing_input)}", expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="Invalid access token")
    signing_input = f"{parts[0]}.{parts[1]}"
    expected = _sign(signing_input)
    if not hmac.compare_digest(expected, parts[2]):
        raise HTTPException(status_code=401, detail="Invalid access token")
    try:
        payload = json.loads(_b64url_decode(parts[1]))
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid access token")
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid access token")
    if int(payload.get("exp", 0)) < int(utcnow().timestamp()):
        raise HTTPException(status_code=401, detail="Access token expired")
    return payload


def issue_tokens(db: Session, user: User, request: Request | None = None) -> AuthResponse:
    access_token, expires_at = create_access_token(user)
    refresh_token = secrets.token_urlsafe(32)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=refresh_token_hash(refresh_token),
            expires_at=utcnow() + timedelta(days=REFRESH_TOKEN_DAYS),
            created_at=utcnow(),
            user_agent=request.headers.get("user-agent") if request else None,
        )
    )
    user.last_login_at = utcnow()
    db.flush()
    return AuthResponse(
        accessToken=access_token,
        refreshToken=refresh_token,
        expiresAt=expires_at.isoformat(),
        user=user_to_out(user),
    )


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not AUTH_ENABLED:
        user = db.execute(select(User).where(User.role == "ADMIN").order_by(User.id)).scalar_one_or_none()
        if user:
            return user
        user = User(username="dev-admin", display_name="Development Admin", password_hash=hash_password(SEED_PASSWORD), role="ADMIN", is_active=1)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = decode_access_token(authorization.split(" ", 1)[1].strip())
    user = db.execute(select(User).where(User.id == int(payload["uid"]))).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def require_roles(*roles: str) -> Callable[[User], User]:
    allowed = {role.upper() for role in roles}

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user

    return dependency


def actor_name(user: User | None) -> str | None:
    return user.username if user else None


def seed_users(db: Session) -> None:
    defaults = [
        ("admin", "UrbanShield Admin", "ADMIN"),
        ("operator", "UrbanShield Operator", "OPERATOR"),
        ("auditor", "UrbanShield Auditor", "AUDITOR"),
        ("viewer", "UrbanShield Viewer", "VIEWER"),
    ]
    changed = False
    for username, display_name, role in defaults:
        user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if user is None:
            db.add(
                User(
                    username=username,
                    display_name=display_name,
                    password_hash=hash_password(SEED_PASSWORD),
                    role=role,
                    is_active=1,
                    created_at=utcnow(),
                    updated_at=utcnow(),
                )
            )
            changed = True
        elif user.role != role:
            user.role = role
            user.updated_at = utcnow()
            changed = True
    if changed:
        db.flush()
