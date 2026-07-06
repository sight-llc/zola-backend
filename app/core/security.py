from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib
import jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User

settings = get_settings()
bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    """
    Hash password with SHA-256 pre-hashing to handle passwords > 72 bytes.
    bcrypt has a 72-byte limit, so we pre-hash to allow longer passwords securely.
    """
    # Pre-hash with SHA-256 to handle long passwords
    sha256_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
    # bcrypt expects bytes, returns bytes - decode to string for storage
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(sha256_hash.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify password against hash.
    Applies the same SHA-256 pre-hash before verification.
    """
    sha256_hash = hashlib.sha256(plain.encode('utf-8')).hexdigest()
    return bcrypt.checkpw(sha256_hash.encode('utf-8'), hashed.encode('utf-8'))


def create_access_token(subject: str, extra: dict = None) -> str:
    payload = {
        "sub": subject,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes),
        **(extra or {}),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    

    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user