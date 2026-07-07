import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_user, verify_pin
from app.core.database import get_db
from app.models.user import User
from app.services.meroe_service import request_payout, lookup_bank_account, get_banks

router = APIRouter()

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Bank endpoints - now using Meroe (Nomba DVA) instead of mock data
# ---------------------------------------------------------------------------

@router.get("/banks")
async def list_banks(_: User = Depends(get_current_user)):
    """
    Returns supported Nigerian banks from Meroe.
    Response format: [{ bankCode, bankName, nipCode, logo }]
    """
    return await get_banks()


class ResolveRequest(BaseModel):
    bank_code: str
    account_number: str

    @field_validator("account_number")
    @classmethod
    def validate_nuban(cls, v: str) -> str:
        if len(v) != 10 or not v.isdigit():
            raise ValueError("Account number must be 10 digits")
        return v


@router.post("/resolve")
async def resolve_account(body: ResolveRequest, _: User = Depends(get_current_user)):
    """
    Resolves a bank account name via Meroe's bank lookup endpoint.
    Response format: { accountNumber, accountName }
    """
    return await lookup_bank_account(body.account_number, body.bank_code)


class SendMoneyRequest(BaseModel):
    bank_code: str
    account_number: str
    account_name: str
    amount: int  # kobo (smallest unit)
    narration: str = "Transfer"
    pin: str  # 4-digit transaction PIN

    @field_validator("amount")
    @classmethod
    def positive_amount(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 4:
            raise ValueError("PIN must be exactly 4 digits")
        return v


@router.post("/send")
async def send_money(
    body: SendMoneyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Initiates a payout via Meroe BaaS infrastructure.
    Requires 4-digit transaction PIN for security.
    """
    if not current_user.meroe_customer_id:
        raise HTTPException(status_code=503, detail="Customer not provisioned on Meroe yet")

    # Verify transaction PIN
    if not current_user.pin_set:
        raise HTTPException(status_code=403, detail="Transaction PIN not set. Please set your PIN first.")
    if not verify_pin(body.pin, current_user.transaction_pin_hash):
        raise HTTPException(status_code=401, detail="Invalid transaction PIN")

    idempotency_key = f"ZOLA-{uuid.uuid4().hex[:16].upper()}"

    try:
        result = await request_payout(
            meroe_customer_id=current_user.meroe_customer_id,
            bank_code=body.bank_code,
            account_number=body.account_number,
            account_name=body.account_name,
            amount_kobo=body.amount,
            narration=body.narration,
            idempotency_key=idempotency_key,
        )
        logger.info(
            "Successfully initiated payout for Zola user %s (Meroe customer %s). "
            "Amount: %d kobo, Bank: %s, Account: %s",
            current_user.id,
            current_user.meroe_customer_id,
            body.amount,
            body.bank_code,
            body.account_number,
        )
        return result
    except HTTPException as exc:
        # Log the Meroe error details
        logger.error(
            "Meroe payout failed for Zola user %s (Meroe customer %s). "
            "HTTPException: status_code=%s, detail=%s. "
            "Amount: %d kobo, Bank: %s, Account: %s",
            current_user.id,
            current_user.meroe_customer_id,
            exc.status_code,
            exc.detail,
            body.amount,
            body.bank_code,
            body.account_number,
        )
        raise
    except Exception as exc:
        # Log unexpected errors
        logger.exception(
            "Unexpected error during payout for Zola user %s (Meroe customer %s): %s. "
            "Amount: %d kobo, Bank: %s, Account: %s",
            current_user.id,
            current_user.meroe_customer_id,
            str(exc),
            body.amount,
            body.bank_code,
            body.account_number,
        )
        raise HTTPException(
            status_code=503,
            detail="Unable to process transfer. Please try again later.",
        )