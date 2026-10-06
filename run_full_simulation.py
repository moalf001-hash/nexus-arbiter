from datetime import datetime, timezone, timedelta
import json
from uuid import uuid4

# 1. استيراد المكونات التي بنيناها
from src.core.schemas import (
    NegotiationPayload,
    SignedNegotiationMessage,
    ActionType,
    ItemType,
    CurrencyType
)
from src.core.fsm import NegotiationSession
from src.crypto.signatures import generate_keypair, sign_bytes
from src.arbiter.verification import (
    ArbiterEngine,
    SecurityAuditDeliverable,
    VulnerabilityFinding
)
from src.invoicing.invoice_generator import InvoiceGenerator

def print_separator(title):
    print(f"\n{'='*20} {title} {'='*20}")

def main():
    print_separator("المرحلة 1: تهيئة الهويات والمحافظ الرقمية")
    
    # محفظتك الشخصية لتلقي الأرباح
    OWNER_WALLET = "0xFaDeL_Platform_Owner_USDC_Wallet"
    
    # إنشاء هويات الوكلاء (مفاتيح تشفير ومحافظ افتراضية)
    buyer_priv, buyer_pub = generate_keypair()
    buyer_pub_hex = buyer_pub.public_bytes_raw().hex()
    buyer_wallet = "0xBuyerCorp_Enterprise_Wallet"
    buyer_id = "agent:buyer_corp"

    seller_priv, seller_pub = generate_keypair()
    seller_pub_hex = seller_pub.public_bytes_raw().hex()
    seller_wallet = "0xSellerSec_Auditor_Wallet"
    seller_id = "agent:seller_audit"

    print(f"[+] محفظة مالك المنصة (أرباحك) : {OWNER_WALLET}")
    print(f"[+] وكيل المشتري                 : {buyer_id} | محفظته: {buyer_wallet}")
    print(f"[+] وكيل البائع                  : {seller_id} | محفظته: {seller_wallet}")

    # أرصدة المحافظ الافتراضية الأولية
    balances = {
        OWNER_WALLET: 0.0,
        buyer_wallet: 1000.0,
        seller_wallet: 0.0,
        "ESCROW_CONTRACT": 0.0
    }

    print_separator("المرحلة 2: دورة التفاوض التشفيري (FSM)")
    session_id = uuid4()
    session = NegotiationSession(session_id=session_id)

    def send_negotiation_step(agent_id, priv_key, pub_hex, seq, action, payload):
        stub = SignedNegotiationMessage(
            session_id=session_id,
            sequence_id=seq,
            sender_agent_id=agent_id,
            action=action,
            payload=payload,
            public_key_hex=pub_hex,
            signature_hex="0" * 128
        )
        sig = sign_bytes(priv_key, stub.message_digest_bytes())
        msg = stub.model_copy(update={"signature_hex": sig})
        session.apply_transition(msg)
        return msg

    # عرض أولي من المشتري: 500 USDC
    p1 = NegotiationPayload(item_type=ItemType.SECURITY_AUDIT, price_unit=500.0, quantity=1, sla_hours=24)
    send_negotiation_step(buyer_id, buyer_priv, buyer_pub_hex, 1, ActionType.PROPOSE, p1)
    print(f"[*] الخطوة 1: المشتري يعرض 500.0 USDC (الحالة: {session.status.value})")

    # عرض مقابل من البائع: 600 USDC
    p2 = NegotiationPayload(item_type=ItemType.SECURITY_AUDIT, price_unit=600.0, quantity=1, sla_hours=24)
    send_negotiation_step(seller_id, seller_priv, seller_pub_hex, 2, ActionType.COUNTER, p2)
    print(f"[*] الخطوة 2: البائع يطلب 600.0 USDC (الحالة: {session.status.value})")

    # موافقة المشتري وتوقيع الاتفاق
    send_negotiation_step(buyer_id, buyer_priv, buyer_pub_hex, 3, ActionType.ACCEPT, p2)
    print(f"[*] الخطوة 3: المشتري يوافق ويقفل العقد (الحالة: {session.status.value})")
    
    agreed_deal = session.agreed_payload
    deal_price = agreed_deal.price_unit

    print_separator("المرحلة 3: قفل الضمان المالي في العقد الذكي (Escrow)")
    # محاكاة دالة lockFunds في Solidity
    balances[buyer_wallet] -= deal_price
    balances["ESCROW_CONTRACT"] += deal_price
    deadline_ts = (datetime.now(timezone.utc) + timedelta(hours=agreed_deal.sla_hours)).timestamp()

    print(f"[+] تم سحب {deal_price} USDC من محفظة المشتري وتجميدها في خزينة العقد الذكي.")
    print(f"    - رصيد المشتري المتبقي    : {balances[buyer_wallet]} USDC")
    print(f"    - رصيد خزينة العقد الذكي   : {balances['ESCROW_CONTRACT']} USDC")
    print(f"    - مهلة التسليم القصوى (SLA): {agreed_deal.sla_hours} ساعة")

    print_separator("المرحلة 4: تسليم مخرجات الخدمة وفحص التحكيم الحتمي")
    # البائع ينفذ العمل وينشئ التقرير
    audit_report = SecurityAuditDeliverable(
        session_id=str(session_id),
        target="https://core-banking.api.internal",
        findings=[
            VulnerabilityFinding(
                id="SEC-091",
                severity="CRITICAL",
                component="/v1/auth/jwt",
                description="Algorithm confusion flaw leading to signature bypass"
            )
        ],
        summary="فحص كامل للمنافذ واكتشاف ثغرة مصادقة حرجة مع توثيق طريقة المعالجة."
    )
    raw_report_json = json.dumps(audit_report.model_dump(mode="json"), separators=(",", ":"))
    report_signature = sign_bytes(seller_priv, raw_report_json.encode("utf-8"))

    # فحص محرك التحكيم
    verification = ArbiterEngine.verify_proof_of_delivery(
        raw_deliverable_json=raw_report_json,
        expected_session_id=str(session_id),
        seller_pub_key_hex=seller_pub_hex,
        delivery_signature_hex=report_signature,
        deadline_timestamp=deadline_ts
    )

    if not verification.is_valid:
        print(f"[-] فشل التحكيم: {verification.reason}")
        return

    print(f"[+] محرك التحكيم: {verification.reason}")
    print(f"[+] بصمة التقرير المعتمد (SHA-256): {verification.deliverable_hash}")

    print_separator("المرحلة 5: الفوترة الضريبية والتسوية المالية الآلية")
    # إنشاء الفاتورة الضريبية
    invoice = InvoiceGenerator.create_invoice(
        session_id=str(session_id),
        buyer_id=buyer_id,
        seller_id=seller_id,
        item_description="Smart Contract & Core Banking Security Assessment",
        amount_usdc=deal_price,
        deliverable_hash=verification.deliverable_hash
    )

    # محاكاة دالة settleAndSplit في Solidity
    fee_amount = invoice.financials.platform_fee_amount
    seller_amount = invoice.financials.seller_net_amount

    balances["ESCROW_CONTRACT"] -= deal_price
    balances[OWNER_WALLET] += fee_amount
    balances[seller_wallet] += seller_amount

    print(f"[+] تم إصدار الفاتورة الضريبية الرسمية رقم: {invoice.invoice_id}")
    print(f"    - البصمة المشفرة للفاتورة (Invoice Hash): {invoice.invoice_hash()}")
    print("\n--- تقرير الأرصدة والتحويلات النهائية بعد إتمام الصفقة ---")
    print(f"1. محفظتك الخاصة (أرباح المنصة 1.5%) : +{balances[OWNER_WALLET]} USDC")
    print(f"2. محفظة الوكيل البائع (صافي المستحق)  : +{balances[seller_wallet]} USDC")
    print(f"3. رصيد العقد الذكي (تصفير الخزينة)    : {balances['ESCROW_CONTRACT']} USDC")
    print(f"4. رصيد المشتري بعد سداد الفاتورة      : {balances[buyer_wallet]} USDC")

    print_separator("تمت دورة التعاقد والتحكيم والتسوية بنجاح 100%")

if __name__ == "__main__":
    main()