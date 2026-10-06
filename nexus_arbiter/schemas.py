from datetime import datetime, timezone
from enum import Enum
import json
from typing import Union
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
    price_unit: float = Field(gt=0, description="Unit price in USDC (must be greater than 0)")
    quantity: int = Field(ge=1, description="Quantity (minimum 1)")
    currency: CurrencyType = CurrencyType.USDC
    sla_hours: int = Field(ge=1, le=720, description="SLA duration in hours (1-720)")

    def canonical_bytes(self) -> bytes:
        data = self.model_dump(mode="json")
        return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")

class EncryptedPayloadEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nonce_hex: str = Field(min_length=24, max_length=24, description="12-byte Nonce (hex-encoded)")
    ciphertext_hex: str = Field(description="ChaCha20-Poly1305 Ciphertext (hex-encoded)")
    sender_enc_pubkey_hex: str = Field(min_length=64, max_length=64, description="X25519 Ephemeral Public Key")

    def canonical_bytes(self) -> bytes:
        data = self.model_dump(mode="json")
        return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")

class PriceCommitment(BaseModel):
    """Cryptographic commitment binding the encrypted price to the buyer's signature to prevent seller spoofing."""
    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    agreed_amount_usdc: float = Field(gt=0, description="Agreed settlement price in USDC")
    buyer_agent_id: str
    seller_agent_id: str
    buyer_pubkey_hex: str = Field(min_length=64, max_length=64, description="Buyer's Ed25519 Public Key")
    buyer_signature_hex: str = Field(min_length=128, max_length=128, description="Buyer's Ed25519 Signature over commitment digest")

    def digest_bytes(self) -> bytes:
        data = {
            "session_id": str(self.session_id),
            "agreed_amount_usdc": self.agreed_amount_usdc,
            "buyer_agent_id": self.buyer_agent_id,
            "seller_agent_id": self.seller_agent_id
        }
        return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")

class SignedNegotiationMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    sequence_id: int = Field(ge=1, description="Monotonically increasing sequence number")
    sender_agent_id: str = Field(pattern=r"^agent:[a-z0-9_\-\.]+$", description="Unique agent identifier (agent:<id>)")
    action: ActionType
    payload: Union[NegotiationPayload, EncryptedPayloadEnvelope]
    public_key_hex: str = Field(min_length=64, max_length=64, description="Sender's Ed25519 Public Key")
    signature_hex: str = Field(min_length=128, max_length=128, description="Ed25519 signature over message digest")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def message_digest_bytes(self) -> bytes:
        payload_data = json.loads(self.payload.canonical_bytes().decode("utf-8"))
        envelope = {
            "session_id": str(self.session_id),
            "sequence_id": self.sequence_id,
            "sender_agent_id": self.sender_agent_id,
            "action": self.action.value,
            "payload": payload_data
        }
        return json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")