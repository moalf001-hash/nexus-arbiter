from datetime import datetime, timezone
import hashlib
import json
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict

class InvoiceFeeBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subtotal_usdc: float
    platform_fee_percent: float = 1.5
    platform_fee_amount: float
    seller_net_amount: float
    currency: str = "USDC"

class TaxCompliantInvoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invoice_id: str = Field(default_factory=lambda: f"INV-{uuid4().hex[:8].upper()}")
    session_id: str
    buyer_id: str
    seller_id: str
    item_description: str
    deliverable_hash: str = Field(min_length=64, max_length=64, description="بصمة التقرير المستلم")
    financials: InvoiceFeeBreakdown
    blockchain_network: str = "Base Sepolia"
    issued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def canonical_bytes(self) -> bytes:
        """تحويل الفاتورة إلى صيغة قياسية محكمة لحساب البصمة الرقمية."""
        data = self.model_dump(mode="json")
        return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def invoice_hash(self) -> str:
        """توليد بصمة SHA-256 الرسمية للفاتورة لربطها بالمعاملة المالية."""
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

class InvoiceGenerator:
    @staticmethod
    def create_invoice(
        session_id: str,
        buyer_id: str,
        seller_id: str,
        item_description: str,
        amount_usdc: float,
        deliverable_hash: str
    ) -> TaxCompliantInvoice:
        """
        إنشاء وتوثيق الفاتورة الضريبية للصفقة واحتساب عمولة المنصة وحصص الأطراف.
        """
        fee_percent = 1.5
        fee_amount = round(amount_usdc * (fee_percent / 100), 2)
        seller_net = round(amount_usdc - fee_amount, 2)

        financials = InvoiceFeeBreakdown(
            subtotal_usdc=amount_usdc,
            platform_fee_percent=fee_percent,
            platform_fee_amount=fee_amount,
            seller_net_amount=seller_net,
            currency="USDC"
        )

        return TaxCompliantInvoice(
            session_id=session_id,
            buyer_id=buyer_id,
            seller_id=seller_id,
            item_description=item_description,
            deliverable_hash=deliverable_hash,
            financials=financials
        )