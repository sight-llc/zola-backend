from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, get_current_user, hash_pin
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, AuthResponse, UserOut
from app.services.meroe_service import provision_meroe_customer
from app.utils.email import send_welcome_email
from pydantic import BaseModel, field_validator

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(body: RegisterRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
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
    nuban = None
    bank_name = None
    try:
        prov = await provision_meroe_customer(user)
        if prov is None:
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
        user.meroe_customer_id = prov.customer_id
        nuban = prov.nuban
        bank_name = prov.bank_name
        logger.info(
            "Successfully provisioned Meroe customer %s for Zola user %s (email: %s). NUBAN: %s",
            prov.customer_id,
            user.id,
            user.email,
            nuban,
        )
    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
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

    if nuban:
        background_tasks.add_task(
            send_welcome_email,
            to_email=user.email,
            to_name=user.full_name,
            nuban=nuban,
            bank_name=bank_name or "Nomba",
        )

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


class SetPinRequest(BaseModel):
    pin: str

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 4:
            raise ValueError("PIN must be exactly 4 digits")
        return v


@router.post("/pin")
async def set_pin(
    body: SetPinRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Set or update the 4-digit transaction PIN for the authenticated user.
    This PIN is required for all transfer operations.
    """
    if current_user.pin_set:
        raise HTTPException(status_code=409, detail="PIN already set. Use a different endpoint to change it.")

    current_user.transaction_pin_hash = hash_pin(body.pin)
    current_user.pin_set = True
    await db.commit()

    return {"success": True, "message": "Transaction PIN set successfully"}
