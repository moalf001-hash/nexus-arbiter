from datetime import datetime, timezone, timedelta
import json
from uuid import uuid4
from fastapi.testclient import TestClient

from src.api.server import app
from src.core.schemas import NegotiationPayload, SignedNegotiationMessage, ActionType, ItemType, CurrencyType
from src.crypto.signatures import generate_keypair, sign_bytes
from src.arbiter.verification import SecurityAuditDeliverable, VulnerabilityFinding

client = TestClient(app)

print("--- بدء فحص بوابة FastAPI لخادم NexusArbiter ---\n")

# 1. فحص الصحة (Health Check)
res = client.get("/health")
print(f"[1] فحص حالة الخادم (/health): {res.status_code} - {res.json()}")

# 2. إعداد أطراف الصفقة
buyer_priv, buyer_pub = generate_keypair()
seller_priv, seller_pub = generate_keypair()
session_id = uuid4()

buyer_pub_hex = buyer_pub.public_bytes_raw().hex()
seller_pub_hex = seller_pub.public_bytes_raw().hex()

def send_api_msg(agent_id, priv, pub_hex, seq, action, payload):
    stub = SignedNegotiationMessage(
        session_id=session_id,
        sequence_id=seq,
        sender_agent_id=agent_id,
        action=action,
        payload=payload,
        public_key_hex=pub_hex,
        signature_hex="0" * 128
    )
    sig = sign_bytes(priv, stub.message_digest_bytes())
    msg_dict = stub.model_copy(update={"signature_hex": sig}).model_dump(mode="json")
    return client.post("/negotiate/step", json=msg_dict)

# عرض أولي: 500 USDC
p1 = NegotiationPayload(item_type=ItemType.SECURITY_AUDIT, price_unit=500.0, quantity=1, sla_hours=24)
r1 = send_api_msg("agent:buyer", buyer_priv, buyer_pub_hex, 1, ActionType.PROPOSE, p1)
print(f"[2] إرسال عرض المشتري (500 USDC): كود الاستجابة {r1.status_code} | الحالة: {r1.json().get('status')}")

# عرض مقابل: 600 USDC
p2 = NegotiationPayload(item_type=ItemType.SECURITY_AUDIT, price_unit=600.0, quantity=1, sla_hours=24)
r2 = send_api_msg("agent:seller", seller_priv, seller_pub_hex, 2, ActionType.COUNTER, p2)
print(f"[3] إرسال عرض البائع المقابل (600 USDC): كود الاستجابة {r2.status_code} | الحالة: {r2.json().get('status')}")

# قبول المشتري
r3 = send_api_msg("agent:buyer", buyer_priv, buyer_pub_hex, 3, ActionType.ACCEPT, p2)
print(f"[4] إرسال قبول العقد: كود الاستجابة {r3.status_code} | السعر المقفل: {r3.json().get('agreed_price')} USDC")

# 3. تسليم العمل والتحكيم عبر نقطة /arbiter/settle
report = SecurityAuditDeliverable(
    session_id=str(session_id),
    target="https://api.gateway.internal",
    findings=[
        VulnerabilityFinding(id="SEC-01", severity="HIGH", component="/auth", description="Weak secret token")
    ],
    summary="تم اكتشاف الثغرة وتأكيد الحماية."
)
report_json = json.dumps(report.model_dump(mode="json"), separators=(",", ":"))
report_sig = sign_bytes(seller_priv, report_json.encode("utf-8"))
deadline = (datetime.now(timezone.utc) + timedelta(hours=24)).timestamp()

settle_payload = {
    "session_id": str(session_id),
    "raw_deliverable_json": report_json,
    "seller_pub_key_hex": seller_pub_hex,
    "delivery_signature_hex": report_sig,
    "deadline_timestamp": deadline,
    "item_description": "API Gateway Security Review"
}

r_settle = client.post("/arbiter/settle", json=settle_payload)
print(f"\n[5] استدعاء محرك التحكيم والتسوية (/arbiter/settle): كود الاستجابة {r_settle.status_code}")
settle_data = r_settle.json()
print(f"    - حالة الاعتماد     : {settle_data.get('status')}")
print(f"    - رقم الفاتورة       : {settle_data.get('invoice_id')}")
print(f"    - عمولة المنصة (لك) : {settle_data.get('settlement', {}).get('platform_fee_usdc')} USDC")
print(f"    - صافي البائع       : {settle_data.get('settlement', {}).get('seller_net_usdc')} USDC")