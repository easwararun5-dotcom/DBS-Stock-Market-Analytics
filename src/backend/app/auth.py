"""
Authentication and session management module for DBS Stock Market Analytics.

Features:
- Secure password hashing using bcrypt.
- JWT token generation, expiration, and decoding.
- HTTP-only cookie and Authorization header extraction.
- User identity dependency injection for protected endpoints.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import bcrypt
import jwt
from fastapi import Request, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import get_relational_db

JWT_SECRET = os.getenv("JWT_SECRET", "dbs-analytics-course-project-secret-key-2026")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hashes a plain-text password using bcrypt with a generated salt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain-text password against the stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Creates a signed JWT access token with an expiration timestamp."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and validates a JWT token signature and expiration."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except (jwt.PyJWTError, Exception):
        return None


def get_token_from_request(
    request: Request,
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[str]:
    """Extracts JWT token from Authorization header or HTTP-only cookie."""
    if auth_header and auth_header.credentials:
        return auth_header.credentials
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        if cookie_token.startswith("Bearer "):
            return cookie_token[7:]
        return cookie_token
    return None


def get_current_user(
    request: Request,
    token: Optional[str] = Depends(get_token_from_request),
    db: Session = Depends(get_relational_db),
) -> Dict[str, Any]:
    """
    FastAPI dependency that enforces authentication.
    Resolves the authenticated user from the database.
    Raises HTTP 401 if token is missing, expired, or invalid.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Please log in.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise credentials_exception

    user_id = payload.get("sub")
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        raise credentials_exception

    user_row = db.execute(
        text("SELECT user_id, username, email, full_name, role, created_at FROM app_user WHERE user_id = :uid"),
        {"uid": user_id},
    ).fetchone()

    if not user_row:
        raise credentials_exception

    return dict(user_row._mapping)


def get_optional_current_user(
    request: Request,
    token: Optional[str] = Depends(get_token_from_request),
    db: Session = Depends(get_relational_db),
) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency for optional authentication.
    Returns user dictionary if authenticated, or None if anonymous.
    """
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        if not payload or "sub" not in payload:
            return None
        user_id = int(payload["sub"])
        user_row = db.execute(
            text("SELECT user_id, username, email, full_name, role, created_at FROM app_user WHERE user_id = :uid"),
            {"uid": user_id},
        ).fetchone()
        return dict(user_row._mapping) if user_row else None
    except Exception:
        return None
