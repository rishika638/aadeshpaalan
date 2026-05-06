from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.security import create_access_token, get_current_user


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    # NOTE: schema does not include passwords; production deployment should integrate with internal SSO.
    user = (await db.execute(select(User).where(User.email == payload.email))).scalars().first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid user")
    token = create_access_token(user_id=user.id, role=user.role.value)
    return TokenResponse(access_token=token, name=user.name, role=user.role.value)


@router.get("/me")
async def me(user: User = Depends(get_current_user)) -> dict:
    return {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "designation": user.designation,
        "department": user.department,
        "role": user.role.value,
    }

