import time
import secrets
import hashlib
import jwt
from typing import List, Optional
from fastapi import Header, HTTPException, status, Depends
from passlib.context import CryptContext

from ..settings import settings
from ..db import SessionLocal
from ..models import User

# bcrypt - классика (заведись пожалуйтса)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__truncate_error=False)


def hash_password(password: str) -> str:
    # хеш пароля
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    # проверка пяроля против сохраненного хеша
    return pwd_context.verify(password, password_hash)


def create_access_token(user: User, expires_in: Optional[int] = None) -> str:
    # короткоживущий access JWT с базовыми клаймами
    if expires_in is None:
        expires_in = settings.ACCESS_TOKEN_EXPIRES_SECONDS
    now = int(time.time())
    payload = {
        "sub": user.id,
        "username": user.username,
        "role": user.role,
        "iat": now,
        "exp": now + expires_in,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    # декодинг и валидиров...инг access JWT
    return jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
        audience=settings.JWT_AUDIENCE,
        issuer=settings.JWT_ISSUER,
    )


def generate_refresh_token() -> str:
    # ОПАКУЕ(opaque)-строка для refresh
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    # в БД только хеш- чтоб даже при утечке БД нельзя было использовать токен
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_current_user(authorization: Optional[str] = Header(None)):
    # Достаём Bearer токен из заголовка, далее возвращаем пользователя
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        data = decode_access_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_id = data.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token subject missing")

    with SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
        return user


def require_roles(roles: List[str]):
    #простой RBAC: завернём зависимость в функцию
    def _dep(user=Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return _dep