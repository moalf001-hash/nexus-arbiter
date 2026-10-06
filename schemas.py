from datetime import datetime, timezone
from enum import Enum
import json
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

class ActionType(str, Enum):
    PROPOSE = "PROPOSE"
    COUNTER = "COUNTER"
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"

class ItemType(str, Enum):
    SECURITY_AUDIT = "SECURITY_AUDIT"
    COMPUTE_RESOURCE = "COMPUTE_RESOURCE"
    DATASET_ACCESS = "DATASET_ACCESS"

class CurrencyType(str, Enum):
    USDC = "USDC"

class NegotiationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_type: ItemType
    price_unit: float = Field(gt=0, description="سعر الوحدة بـ USDC أكبر من صفر")
    quantity: int = Field(ge=1, description="الكمية الإلزامية لا تقل عن 1")
    currency: CurrencyType = CurrencyType.USDC
    sla_hours: int = Field(ge=1, le=720, description="مدة الـ SLA بالساعات")

    def canonical_bytes(self) -> bytes:
        data = self.model_dump(mode="json")
        return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")

class SignedNegotiationMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    sequence_id: int = Field(ge=1)
    sender_agent_id: str = Field(pattern=r"^agent:[a-z0-9_\-\.]+$")
    action: ActionType
    payload: NegotiationPayload
    public_key_hex: str = Field(min_length=64, max_length=64)
    signature_hex: str = Field(min_length=128, max_length=128)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def message_digest_bytes(self) -> bytes:
        envelope = {
            "session_id": str(self.session_id),
            "sequence_id": self.sequence_id,
            "sender_agent_id": self.sender_agent_id,
            "action": self.action.value,
            "payload": json.loads(self.payload.canonical_bytes().decode("utf-8"))
        }
        return json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")