import uuid
import random
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from app.core.security import get_current_user
from app.models.user import User
from app.services.meroe_service import request_payout

router = APIRouter()


# ---------------------------------------------------------------------------
# Mock bank list (will be replaced with Meroe lookup endpoint when ready)
# ---------------------------------------------------------------------------

NG_BANKS = [
    {"code": "058", "name": "GTBank"},
    {"code": "011", "name": "First Bank"},
    {"code": "044", "name": "Access Bank"},
    {"code": "057", "name": "Zenith Bank"},
    {"code": "033", "name": "UBA"},
    {"code": "50211", "name": "Kuda"},
    {"code": "999992", "name": "Opay"},
    {"code": "50515", "name": "Moniepoint"},
    {"code": "232", "name": "Sterling Bank"},
    {"code": "035", "name": "Wema Bank"},
    {"code": "070", "name": "Fidelity Bank"},
    {"code": "214", "name": "FCMB"},
    {"code": "032", "name": "Union Bank"},
    {"code": "221", "name": "Stanbic IBTC"},
]

MOCK_NAMES = [
    "Emeka Okonkwo", "Aisha Bello", "Oluwaseun Adeyemi",
    "Chinaza Uche", "Ibrahim Musa", "Ngozi Anyanwu", "Tobi Ogundipe",
]


@router.get("/banks")
async def list_banks(_: User = Depends(get_current_user)):
    """
    Returns supported Nigerian banks.
    TODO: swap with Meroe bank-list endpoint when available.
    """
    return {"banks": NG_BANKS}


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
    Resolves a bank account name.
    TODO: swap with Meroe account-lookup endpoint when available.
    """
    bank = next((b for b in NG_BANKS if b["code"] == body.bank_code), None)
    if not bank:
        raise HTTPException(status_code=400, detail="Unknown bank code")

    # Mock: derive a deterministic name from the last digit
    idx = int(body.account_number[-1]) % len(MOCK_NAMES)
    return {
        "accountName": MOCK_NAMES[idx],
        "bankName": bank["name"],
        "accountNumber": body.account_number,
    }


class SendMoneyRequest(BaseModel):
    bank_code: str
    account_number: str
    account_name: str
    amount: int  # kobo (smallest unit)
    narration: str = "Transfer"

    @field_validator("amount")
    @classmethod
    def positive_amount(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v


@router.post("/send")
async def send_money(body: SendMoneyRequest, current_user: User = Depends(get_current_user)):
    """
    Initiates a payout via Meroe BaaS infrastructure.
    Meroe handles debit, ledgering, and Nomba disbursement.
    Bank lookup/resolve is still mocked (endpoint pending).
    """
    if not current_user.meroe_customer_id:
        raise HTTPException(status_code=503, detail="Customer not provisioned on Meroe yet")

    idempotency_key = f"ZOLA-{uuid.uuid4().hex[:16].upper()}"

    result = await request_payout(
        meroe_customer_id=current_user.meroe_customer_id,
        bank_code=body.bank_code,
        account_number=body.account_number,
        account_name=body.account_name,
        amount_kobo=body.amount,
        narration=body.narration,
        idempotency_key=idempotency_key,
    )
    return result
