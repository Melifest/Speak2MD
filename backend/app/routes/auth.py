from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, status, Depends

from ..db import SessionLocal
from ..models import User, RefreshToken
from ..settings import settings
from ..utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    get_current_user,
)
from ..schemas import (
    AuthRegisterRequest,
    AuthLoginRequest,
    RefreshRequest,
    AuthTokensResponse,
    UserProfile,
)

router = APIRouter()


@router.post("/auth/register", response_model=UserProfile)
def register(payload: AuthRegisterRequest):
    # регаем нового пользователя по username/паролю
    with SessionLocal() as db:
        existing = db.query(User).filter(User.username == payload.username).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

        user = User(
            username=payload.username,
            password_hash=hash_password(payload.password),
            full_name=payload.full_name,
            plan="free",
            role="user",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        return UserProfile(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            email=user.email,
            plan=user.plan,
        )


@router.post("/auth/login", response_model=AuthTokensResponse)
def login(payload: AuthLoginRequest):
    # вход тоже по username/паролю, выдаём пару токенов
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == payload.username, User.is_active == True).first()
        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

        access_token = create_access_token(user)
        refresh_plain = generate_refresh_token()
        refresh = RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_plain),
            expires_at=datetime.utcnow() + timedelta(seconds=settings.REFRESH_TOKEN_EXPIRES_SECONDS),
            revoked=False,
        )
        db.add(refresh)
        db.commit()

        return AuthTokensResponse(
            access_token=access_token,
            refresh_token=refresh_plain,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRES_SECONDS,
        )


@router.post("/auth/refresh", response_model=AuthTokensResponse)
def refresh(payload: RefreshRequest):
    #меняем refresh на новый, выдаём новый access
    with SessionLocal() as db:
        token_hash = hash_refresh_token(payload.refresh_token)
        rt = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked == False,
                RefreshToken.expires_at > datetime.utcnow(),
            )
            .first()
        )
        if not rt:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

        user = db.query(User).filter(User.id == rt.user_id, User.is_active == True).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

        new_refresh_plain = generate_refresh_token()
        new_rt = RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(new_refresh_plain),
            expires_at=datetime.utcnow() + timedelta(seconds=settings.REFRESH_TOKEN_EXPIRES_SECONDS),
            revoked=False,
        )
        rt.revoked = True
        rt.replaced_by = new_rt.id
        db.add(new_rt)
        db.commit()

        return AuthTokensResponse(
            access_token=create_access_token(user),
            refresh_token=new_refresh_plain,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRES_SECONDS,
        )


from fastapi import Header

@router.get("/me", response_model=UserProfile)
def me(authorization: str = Header(None)):
    # профиль текущего пользователя
    user = get_current_user(authorization)
    return UserProfile(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        plan=user.plan,
    )