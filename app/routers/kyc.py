from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.security import get_current_user
from app.core.database import get_db
from app.core.meroe_client import meroe_post
from app.models.user import User

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/status")
async def kyc_status(current_user: User = Depends(get_current_user)):
    """Returns the user's current KYC state."""
    return {
        "tier": current_user.kyc_tier,
        "bvnVerified": current_user.bvn_verified,
        "idVerified": current_user.id_verified,
        "limits": _tier_limits(current_user.kyc_tier),
    }


class BvnRequest(BaseModel):
    bvn: str

    @field_validator("bvn")
    @classmethod
    def validate_bvn(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 11:
            raise ValueError("BVN must be exactly 11 digits")
        return v


@router.post("/bvn")
async def submit_bvn(
    body: BvnRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submits BVN to Meroe, which validates and encrypts it.
    On success mirrors Tier 2 state locally.
    """
    if current_user.bvn_verified:
        raise HTTPException(status_code=409, detail="BVN already verified")
    if not current_user.meroe_customer_id:
        raise HTTPException(status_code=503, detail="Customer not provisioned on Meroe")

    try:
        # Update KYC tier on Meroe
        await meroe_post(
            f"/v1/customers/{current_user.meroe_customer_id}/kyc",
            {"kycTier": "TIER_2"},
        )
        logger.info(
            "Successfully updated KYC tier to TIER_2 for Meroe customer %s (Zola user %s)",
            current_user.meroe_customer_id,
            current_user.id,
        )

        # Mirror locally
        current_user.kyc_tier = 2
        current_user.bvn_verified = True
        await db.commit()

        return {
            "success": True,
            "newTier": 2,
            "limits": _tier_limits(2),
        }
    except HTTPException as exc:
        # Log the Meroe error details
        logger.error(
            "Meroe KYC update failed for Zola user %s (Meroe customer %s). "
            "HTTPException: status_code=%s, detail=%s",
            current_user.id,
            current_user.meroe_customer_id,
            exc.status_code,
            exc.detail,
        )
        raise
    except Exception as exc:
        # Log unexpected errors
        logger.exception(
            "Unexpected error during BVN submission for Zola user %s (Meroe customer %s): %s",
            current_user.id,
            current_user.meroe_customer_id,
            str(exc),
        )
        raise HTTPException(
            status_code=503,
            detail="Unable to update KYC status. Please try again later.",
        )


@router.post("/id-document")
async def submit_id_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Accepts an ID document upload.
    In demo: the upload is accepted and Tier 3 is granted.
    In production: forward to Meroe's document endpoint for review.
    """
    if not current_user.bvn_verified:
        raise HTTPException(status_code=400, detail="BVN must be verified before ID submission")
    if current_user.id_verified:
        raise HTTPException(status_code=409, detail="ID already verified")

    try:
        # TODO: in production, stream the file to Meroe's document endpoint
        # For demo, just promote to Tier 3
        await meroe_post(
            f"/v1/customers/{current_user.meroe_customer_id}/kyc",
            {"kycTier": "TIER_3"},
        )
        logger.info(
            "Successfully updated KYC tier to TIER_3 for Meroe customer %s (Zola user %s)",
            current_user.meroe_customer_id,
            current_user.id,
        )

        current_user.kyc_tier = 3
        current_user.id_verified = True
        await db.commit()

        return {
            "success": True,
            "newTier": 3,
            "limits": _tier_limits(3),
            "fileName": file.filename,
        }
    except HTTPException as exc:
        # Log the Meroe error details
        logger.error(
            "Meroe KYC update failed for Zola user %s (Meroe customer %s). "
            "HTTPException: status_code=%s, detail=%s",
            current_user.id,
            current_user.meroe_customer_id,
            exc.status_code,
            exc.detail,
        )
        raise
    except Exception as exc:
        # Log unexpected errors
        logger.exception(
            "Unexpected error during ID document submission for Zola user %s (Meroe customer %s): %s",
            current_user.id,
            current_user.meroe_customer_id,
            str(exc),
        )
        raise HTTPException(
            status_code=503,
            detail="Unable to update KYC status. Please try again later.",
        )


def _tier_limits(tier: int) -> dict:
    return {
        1: {"daily": 50_000_00},    # ₦50,000 in kobo
        2: {"daily": 500_000_00},   # ₦500,000
        3: {"daily": 5_000_000_00}, # ₦5,000,000
    }.get(tier, {"daily": 50_000_00})