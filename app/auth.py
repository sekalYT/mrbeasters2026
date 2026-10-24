"""
Модуль аутентификации и авторизации пользователей.
Поддерживает проверку логина и пароля, валидацию JWT-токенов и интеграцию с OIDC SSO.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import (
    SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES,
    ADMIN_USERNAME, ADMIN_PASSWORD
)
from app.models import UserInfo

security = HTTPBearer(auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Создание подписанного JWT-токена доступа.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    if isinstance(encoded_jwt, bytes):
        encoded_jwt = encoded_jwt.decode('utf-8')
    return encoded_jwt


def verify_token(token: str) -> dict:
    """
    Проверка подписи и срока действия токена.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный или истекший токен авторизации",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> UserInfo:
    """
    Извлечение и проверка токена текущего пользователя из заголовка Authorization или куки.
    """
    token: Optional[str] = None
    if credentials:
        token = credentials.credentials
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация (отсутствует токен)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(token)
    username = payload.get("sub")
    role = payload.get("role", "marketer")
    auth_type = payload.get("auth_type", "password")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректный токен: субъект не указан"
        )
    return UserInfo(username=username, role=role, auth_type=auth_type)


def authenticate_user(username: str, password: str) -> Optional[UserInfo]:
    """
    Проверка учетных данных пользователя по логину и паролю.
    """
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        return UserInfo(username=username, role="admin", auth_type="password")
    return None
