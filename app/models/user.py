import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Meroe customer reference — set after provisioning
    meroe_customer_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # KYC state mirrored locally (source of truth stays in Meroe)
    kyc_tier: Mapped[int] = mapped_column(default=1)
    bvn_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    id_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Transaction PIN for transfer security
    transaction_pin_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pin_set: Mapped[bool] = mapped_column(Boolean, default=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
