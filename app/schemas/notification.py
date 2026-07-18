from datetime import datetime
from pydantic import BaseModel, computed_field


class NotificationOut(BaseModel):
    id: str
    event_type: str
    description: str
    read: bool
    created_at: datetime
    amount: int | None = None

    @computed_field
    @property
    def amount_display(self) -> str | None:
        if self.amount is None:
            return None
        return f"\u20a6{self.amount:,.2f}"

    model_config = {"from_attributes": True}


class MarkReadRequest(BaseModel):
    ids: list[str]
