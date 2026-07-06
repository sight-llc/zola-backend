from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.security import get_current_user
from app.models.user import User
from app.services.meroe_service import get_balance as meroe_get_balance, get_customer as meroe_get_customer, get_transactions as meroe_get_transactions

router = APIRouter()


def _require_meroe(user: User):
    if not user.meroe_customer_id:
        raise HTTPException(status_code=503, detail="Customer not yet provisioned on Meroe. Try again shortly.")
    return user.meroe_customer_id


@router.get("/balance")
async def get_balance(current_user: User = Depends(get_current_user)):
    """
    Returns the customer's wallet balance from Meroe.
    Shape: { available, spendable, inflightDebit, currency }
    """
    mid = _require_meroe(current_user)
    return await meroe_get_balance(mid)


@router.get("/virtual-account")
async def get_virtual_account(current_user: User = Depends(get_current_user)):
    """
    Returns the customer's dedicated virtual account (Nomba Bank account number).
    Reads from the Meroe customer record.
    """
    mid = _require_meroe(current_user)
    data = await meroe_get_customer(mid)
    va = data.get("virtualAccount")
    if not va:
        raise HTTPException(status_code=404, detail="Virtual account not found")
    return {
        "accountNumber": va.get("accountNumber"),
        "bankName": va.get("bankName", "Nomba Bank"),
        "accountName": va.get("accountName") or current_user.full_name,
    }


@router.get("/transactions")
async def get_transactions(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
):
    """
    Paginated transaction list from Meroe's ledger.
    Returns { items: [...], nextCursor }
    """
    mid = _require_meroe(current_user)
    return await meroe_get_transactions(mid, limit=limit, cursor=cursor)