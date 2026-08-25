import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import Operator

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 180_000)
    return f"{salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split("$", 1)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 180_000)
        return hmac.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


def make_token(op: Operator) -> str:
    payload = {
        "sub": str(op.id),
        "username": op.username,
        "role": op.role,
        "name": op.full_name,
        "badge": op.badge_no,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.jwt_hours),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_alg)


def current_operator(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    access_token: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> Operator:
    raw = creds.credentials if creds else access_token
    if not raw:
        raise HTTPException(401, "Authentication required")
    try:
        data = jwt.decode(raw, settings.secret_key, algorithms=[settings.jwt_alg])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired session")
    op = db.get(Operator, int(data["sub"]))
    if not op:
        raise HTTPException(401, "Operator not found")
    return op
