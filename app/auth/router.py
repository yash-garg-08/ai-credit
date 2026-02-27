from fastapi import APIRouter

from app.auth import service
from app.auth.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.core.dependencies import DbSession

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(body: RegisterRequest, db: DbSession) -> UserResponse:
    user = await service.register_user(db, body.email, body.password)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: DbSession) -> TokenResponse:
    token = await service.authenticate_user(db, body.email, body.password)
    return TokenResponse(access_token=token)
