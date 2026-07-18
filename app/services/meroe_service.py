"""
Meroe (NombaVault) service layer.
Handles customer provisioning at registration, and exposes
helpers used by the wallet/transfer routers.
"""
import uuid
import logging
from dataclasses import dataclass
from app.core.meroe_client import meroe_post, meroe_get

logger = logging.getLogger(__name__)


@dataclass
class ProvisionResult:
    customer_id: str
    nuban: str | None
    bank_name: str | None


async def provision_meroe_customer(user) -> ProvisionResult | None:
    """
    Called once at Zola registration. Creates a Meroe customer + virtual account.
    Returns a ProvisionResult with customer_id, nuban, and bank_name — or None on failure.
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
        va = data.get("virtualAccount") or {}
        nuban = va.get("accountNumber")
        bank_name = va.get("bankName")
        logger.info(
            "Successfully provisioned Meroe customer for Zola user %s (email: %s). "
            "Meroe customer ID: %s, NUBAN: %s",
            user.id,
            user.email,
            customer_id,
            nuban,
        )
        return ProvisionResult(customer_id=customer_id, nuban=nuban, bank_name=bank_name)
    except Exception as exc:
        logger.error(
            "Meroe customer provisioning failed for Zola user %s (email: %s). "
            "Error: %s. Payload: externalRef=%s, fullName=%s, email=%s",
            user.id,
            user.email,
            str(exc),
            payload.get("externalRef"),
            payload.get("fullName"),
            payload.get("email"),
        )
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


async def lookup_bank_account(account_number: str, bank_code: str) -> dict:
    """
    Look up a bank account name via Meroe's bank lookup endpoint.
    Calls POST /v1/transfers/bank/lookup.
    Returns { accountNumber, accountName } (extracted from response data).
    """
    payload = {
        "accountNumber": account_number,
        "bankCode": bank_code,
    }
    response = await meroe_post("/v1/transfers/bank/lookup", payload)
    # Handle both list and dict responses
    if isinstance(response, list):
        data = response[0] if response else {}
    elif isinstance(response, dict):
        data = response.get("data", response)
    else:
        data = {}
    # Map to the expected format (nombadva uses accountNumber, accountName)
    return {
        "accountNumber": data.get("accountNumber") or data.get("account_number"),
        "accountName": data.get("accountName") or data.get("account_name"),
    }


async def get_banks() -> list[dict]:
    """
    Fetch the list of supported banks from Meroe.
    Calls GET /v1/transfers/banks.
    Returns list of { bankCode, bankName, nipCode, logo } (mapped from response).
    """
    response = await meroe_get("/v1/transfers/banks")
    # Handle both list and dict responses
    if isinstance(response, list):
        data = response
    elif isinstance(response, dict):
        data = response.get("data", response)
    else:
        return []
    
    if isinstance(data, list):
        # Map from Meroe's format to nombadva's format
        return [
            {
                "bankCode": b.get("code") or b.get("bankCode"),
                "bankName": b.get("name") or b.get("bankName"),
                "nipCode": b.get("nipCode"),
                "logo": b.get("logo", ""),
            }
            for b in data
        ]
    return []
