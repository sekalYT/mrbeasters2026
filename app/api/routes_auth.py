"""
Маршруты аутентификации пользователей: вход, профиль, выход и поддержка OIDC SSO.
"""

from fastapi import APIRouter, HTTPException, status, Response, Depends
from app.models import UserCredentials, UserInfo, AuthResponse
from app.auth import authenticate_user, create_access_token, get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["Аутентификация"])


@router.post("/login", response_model=AuthResponse, summary="Вход по логину и паролю")
async def login(credentials: UserCredentials, response: Response):
    """
    Аутентификация пользователя по логину и паролю.
    Устанавливает cookie access_token и возвращает JWT токен.
    """
    user = authenticate_user(credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": user.username, "role": user.role, "auth_type": "password"})
    
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24
    )

    return AuthResponse(token=token, token_type="bearer", user=user)


@router.get("/me", response_model=UserInfo, summary="Получение текущего пользователя")
async def get_me(current_user: UserInfo = Depends(get_current_user)):
    """
    Возвращает информацию о текущем авторизованном пользователе.
    """
    return current_user


@router.post("/logout", summary="Завершение текущей сессии")
async def logout(response: Response):
    """
    Завершает сессию и очищает cookie авторизации.
    """
    response.delete_cookie(key="access_token")
    return {"message": "Успешный выход из системы"}


@router.get("/oidc/mock-login", response_model=AuthResponse, summary="Вход через OIDC (демо/mock)")
async def oidc_mock_login(response: Response):
    """
    Дополнительная функция: вход через корпоративный OIDC SSO провайдер.
    """
    user = UserInfo(username="oidc_analyst@aeza.net", role="analyst", auth_type="oidc")
    token = create_access_token({"sub": user.username, "role": user.role, "auth_type": "oidc"})
    
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24
    )
    return AuthResponse(token=token, token_type="bearer", user=user)
