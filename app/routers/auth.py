from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, AuthResponse, UserOut
from app.services.meroe_service import provision_meroe_customer

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check duplicate email
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        full_name=body.full_name,
        email=body.email,
        phone=body.phone,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    await db.flush()  # get user.id before provisioning

    # Provision a Meroe customer + virtual account
    try:
        meroe_id = await provision_meroe_customer(user)
        if meroe_id is None:
            # Meroe provisioning failed - rollback user creation
            logger.error(
                "Meroe customer provisioning failed for user %s (email: %s). "
                "Rolling back user registration.",
                user.id,
                user.email,
            )
            await db.rollback()
            raise HTTPException(
                status_code=503,
                detail="Unable to provision customer account. Please try again later.",
            )
        user.meroe_customer_id = meroe_id
        logger.info(
            "Successfully provisioned Meroe customer %s for Zola user %s (email: %s)",
            meroe_id,
            user.id,
            user.email,
        )
    except HTTPException:
        # Re-raise HTTPException from Meroe client (already has proper error)
        await db.rollback()
        raise
    except Exception as exc:
        # Catch any other unexpected errors
        logger.exception(
            "Unexpected error during Meroe provisioning for user %s (email: %s): %s",
            user.id,
            user.email,
            str(exc),
        )
        await db.rollback()
        raise HTTPException(
            status_code=503,
            detail="Unable to provision customer account. Please try again later.",
        )

    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)
    return AuthResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account suspended")

    token = create_access_token(user.id)
    return AuthResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)