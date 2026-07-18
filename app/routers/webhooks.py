import logging
from fastapi import APIRouter, BackgroundTasks, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import User
from app.models.notification import Notification
from app.models.transfer_ref import TransferRef
from app.utils.email import send_notification_email

logger = logging.getLogger(__name__)
router = APIRouter()

KNOWN_EVENTS = {"PAYMENT.RECEIVED", "TRANSFER.SUCCESS", "TRANSFER.FAILED", "webhook.test"}


@router.post("/meroe", status_code=200)
async def meroe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    body = await request.json()
    logger.info(f"Meroe webhook received: {body}")

    event_type = body.get("event")
    if event_type not in KNOWN_EVENTS:
        return {"received": True}

    if event_type == "webhook.test":
        return {"received": True}

    user = None
    amount = body.get("amount")

    if event_type == "PAYMENT.RECEIVED":
        customer_id = body.get("customerId")
        if not customer_id:
            logger.warning(f"PAYMENT.RECEIVED missing customerId: {body}")
            return {"received": True}
        result = await db.execute(select(User).where(User.meroe_customer_id == customer_id))
        user = result.scalar_one_or_none()

    elif event_type in ("TRANSFER.SUCCESS", "TRANSFER.FAILED"):
        merchant_tx_ref = body.get("merchantTxRef")
        if not merchant_tx_ref:
            logger.warning(f"{event_type} missing merchantTxRef: {body}")
            return {"received": True}
        result = await db.execute(
            select(TransferRef).where(TransferRef.merchant_tx_ref == merchant_tx_ref)
        )
        transfer_ref = result.scalar_one_or_none()
        if transfer_ref:
            result = await db.execute(select(User).where(User.id == transfer_ref.user_id))
            user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"No Zola user found for webhook: {body}")
        return {"received": True}

    amount_naira_str = f"\u20a6{int(amount):,}" if amount is not None else None

    description_map = {
        "PAYMENT.RECEIVED": f"You received {amount_naira_str or 'funds'}",
        "TRANSFER.SUCCESS": f"Transfer of {amount_naira_str or 'funds'} completed",
        "TRANSFER.FAILED": f"Transfer of {amount_naira_str or 'funds'} failed",
    }
    description = description_map.get(event_type, event_type)

    notification = Notification(
        user_id=user.id,
        event_type=event_type,
        amount=int(amount) if amount is not None else None,
        description=description,
    )
    db.add(notification)
    await db.commit()

    if event_type in {"PAYMENT.RECEIVED", "TRANSFER.SUCCESS", "TRANSFER.FAILED"}:
        background_tasks.add_task(
            send_notification_email,
            to_email=user.email,
            to_name=user.full_name,
            event_type=event_type,
            amount_naira=amount_naira_str,
        )

    return {"received": True}
