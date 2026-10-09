from datetime import datetime, timezone
import hashlib
import hmac
import json
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

# Import schemas and cryptographic utilities directly from the unified package
from nexus_arbiter.schemas import ItemType
from nexus_arbiter.crypto.signatures import verify_signature

class VulnerabilityFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    severity: str = Field(pattern="^(CRITICAL|HIGH|MEDIUM|LOW|INFO)$")
    component: str
    description: str

class SecurityAuditDeliverable(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    item_type: ItemType = ItemType.SECURITY_AUDIT
    target: str
    findings: list[VulnerabilityFinding]
    summary: str
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def canonical_hash(self) -> str:
        """Generate canonical SHA-256 digest of the deliverable to bind it to the ledger and on-chain contract."""
        data = self.model_dump(mode="json")
        canonical_str = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

class VerificationResult(BaseModel):
    is_valid: bool
    reason: str
    deliverable_hash: Optional[str] = None
    sla_passed: bool

class ArbiterEngine:
    @staticmethod
    def verify_proof_of_delivery(
        raw_deliverable_json: str,
        expected_session_id: str,
        seller_pub_key_hex: str,
        delivery_signature_hex: str,
        deadline_timestamp: float
    ) -> VerificationResult:
        """
        Deterministic arbitration check for Proof of Delivery (PoD) prior to releasing escrowed funds on-chain.
        """
        # 1. Verify seller's Ed25519 cryptographic signature over raw deliverable payload
        try:
            is_sig_valid = verify_signature(
                public_key_hex=seller_pub_key_hex,
                signature_hex=delivery_signature_hex,
                data=raw_deliverable_json.encode("utf-8")
            )
        except Exception as e:
            return VerificationResult(
                is_valid=False,
                reason=f"Cryptographic verification error: Invalid key or signature encoding ({e})",
                sla_passed=True
            )

        if not is_sig_valid:
            return VerificationResult(
                is_valid=False,
                reason="Verification failed: Seller delivery signature is invalid or has been tampered with",
                sla_passed=True
            )

        # 2. Validate deliverable structure against schema specification
        try:
            deliverable_dict = json.loads(raw_deliverable_json)
            deliverable = SecurityAuditDeliverable(**deliverable_dict)
        except Exception as e:
            return VerificationResult(
                is_valid=False,
                reason=f"Verification failed: Deliverable payload does not match required schema ({e})",
                sla_passed=True
            )

        # 3. Ensure session ID matches using constant-time comparison against timing attacks
        if not hmac.compare_digest(deliverable.session_id, expected_session_id):
            return VerificationResult(
                is_valid=False,
                reason=f"Verification failed: Deliverable session ID mismatch ({deliverable.session_id})",
                sla_passed=True
            )

        # 4. Enforce SLA deadline compliance
        now_ts = datetime.now(timezone.utc).timestamp()
        if now_ts > deadline_timestamp:
            return VerificationResult(
                is_valid=False,
                reason="Delivery failed: Service Level Agreement (SLA) deadline exceeded",
                sla_passed=False
            )

        # 5. All assertions passed; compute canonical hash for on-chain settlement release
        return VerificationResult(
            is_valid=True,
            reason="Delivery verified: Payload schema, cryptographic signature, and SLA deadline validated successfully",
            deliverable_hash=deliverable.canonical_hash(),
            sla_passed=True
        )