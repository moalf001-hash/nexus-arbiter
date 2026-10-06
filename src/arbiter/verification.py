from datetime import datetime, timezone
import hashlib
import json
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from src.core.schemas import ItemType
from src.crypto.signatures import verify_signature

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
        """توليد بصمة SHA-256 للمخرجات لربطها بالمعاملة المالية والفاتورة."""
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
        فحص حتمي وشامل لإثبات التسليم قبل إعطاء أمر فك حجز الأموال للعقد الذكي.
        """
        # 1. فحص سلامة التوقيع الرقمي للبائع على مخرجات العمل
        is_sig_valid = verify_signature(
            public_key_hex=seller_pub_key_hex,
            signature_hex=delivery_signature_hex,
            data=raw_deliverable_json.encode("utf-8")
        )
        if not is_sig_valid:
            return VerificationResult(
                is_valid=False,
                reason="فشل التحقق: توقيع البائع على مخرجات التسليم غير صالح أو تم التلاعب به",
                sla_passed=True
            )

        # 2. فحص مطابقة هيكلية التقرير للنموذج القياسي
        try:
            deliverable_dict = json.loads(raw_deliverable_json)
            deliverable = SecurityAuditDeliverable(**deliverable_dict)
        except Exception as e:
            return VerificationResult(
                is_valid=False,
                reason=f"فشل التحقق: مخرجات التسليم لا تطابق معايير الـ Schema المطلوبة ({e})",
                sla_passed=True
            )

        # 3. التأكد من تطابق معرف الجلسة
        if deliverable.session_id != expected_session_id:
            return VerificationResult(
                is_valid=False,
                reason=f"فشل التحقق: معرف الجلسة في التقرير غير مطابق ({deliverable.session_id})",
                sla_passed=True
            )

        # 4. فحص الالتزام بمهلة الـ SLA
        now_ts = datetime.now(timezone.utc).timestamp()
        if now_ts > deadline_timestamp:
            return VerificationResult(
                is_valid=False,
                reason="فشل التسليم: تم تجاوز مهلة الـ SLA المتفق عليها في العقد",
                sla_passed=False
            )

        # في حال اجتياز جميع الفحوصات بنجاح
        return VerificationResult(
            is_valid=True,
            reason="نجح التسليم: المخرجات مطابقة 100% والتوقيع والمهلة الزمنية صحيحة",
            deliverable_hash=deliverable.canonical_hash(),
            sla_passed=True
        )