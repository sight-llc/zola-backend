"""
Meroe (NombaVault) service layer.
Handles customer provisioning at registration, and exposes
helpers used by the wallet/transfer routers.
"""
import uuid
import logging
from app.core.meroe_client import meroe_post, meroe_get

logger = logging.getLogger(__name__)


async def provision_meroe_customer(user) -> str | None:
    """
    Called once at Zola registration. Creates a Meroe customer + virtual account.
    Returns the Meroe customer UUID, or None if provisioning fails (non-blocking for demo).
    """
    # externalRef must be unique per app — we use Zola's user id
    payload = {
        "externalRef": f"ZOLA-{user.id}",
        "fullName": user.full_name,
        "email": user.email,
        "phone": user.phone or "",
        "kycTier": "TIER_1",
        "metadata": {"source": "zola-app"},
    }
    try:
        data = await meroe_post("/v1/customers", payload)
        customer_id = data.get("id")
        logger.info("Provisioned Meroe customer %s for Zola user %s", customer_id, user.id)
        return customer_id
    except Exception as exc:
        # In a demo context we log and continue — user can still log in
        logger.warning("Meroe provisioning failed for %s: %s", user.email, exc)
        return None


async def get_balance(meroe_customer_id: str) -> dict:
    return await meroe_get(f"/v1/customers/{meroe_customer_id}/balance")


async def get_customer(meroe_customer_id: str) -> dict:
    return await meroe_get(f"/v1/customers/{meroe_customer_id}")


async def get_transactions(meroe_customer_id: str, limit: int = 20, cursor: str | None = None) -> dict:
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor
    return await meroe_get(f"/v1/customers/{meroe_customer_id}/transactions", params=params)


async def request_payout(
    meroe_customer_id: str,
    bank_code: str,
    account_number: str,
    account_name: str,
    amount_kobo: int,
    narration: str,
    idempotency_key: str,
) -> dict:
    payload = {
        "customerId": meroe_customer_id,
        "amount": amount_kobo,
        "destinationBankCode": bank_code,
        "destinationAccountNumber": account_number,
        "destinationAccountName": account_name,
        "narration": narration,
        "merchantTxRef": idempotency_key,
    }
    return await meroe_post("/v1/transfers", payload)
