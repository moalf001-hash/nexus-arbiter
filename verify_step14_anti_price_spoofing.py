from datetime import datetime, timezone, timedelta
import json
from fastapi.testclient import TestClient

from src.api.server import app
from src.core.schemas import ItemType
from src.sdk.agent_client import NexusAgentClient
from src.crypto.signatures import sign_bytes, generate_keypair

client = TestClient(app)

print("--- بدء اختبار الحصانة ضد التلاعب بالأسعار (Anti-Price Spoofing Test) ---\n")

buyer = NexusAgentClient(agent_id="agent:alpha_buyer")
seller = NexusAgentClient(agent_id="agent:beta_seller")

# 1. المشتري يرسل عرضاً مشفراً بـ 1250 USDC
session_id, buyer_env, _ = buyer.propose_encrypted(
    peer_enc_pubkey_hex=seller.enc_public_key_hex,
    item_type=ItemType.SECURITY_AUDIT,
    price_unit=1250.0,
    sla_hours=24,
    client=client
)
print(f"[+] تم إنشاء الجلسة المشفرة: {session_id}")

# 2. البائع يوافق على العرض
seller.sync_sequence(session_id, 2)
seller.accept(session_id=session_id, agreed_payload=buyer_env, sequence_id=2, client=client)
print("[+] البائع وافق على الصفقة المشفرة (1250 USDC).")

# 3. المشتري يُصدر وثيقة الالتزام التشفيري الموقعة (Price Commitment)
legit_commitment = buyer.create_price_commitment(
    session_id=session_id,
    agreed_amount_usdc=1250.0,
    seller_agent_id=seller.agent_id
)
print("[+] المشتري وقّع رياضياً على التزام السعر (1250 USDC).")

# تجهيز مخرجات التقرير
deliverable = {
    "session_id": str(session_id),
    "item_type": "SECURITY_AUDIT",
    "target": "https://secure.core",
    "findings": [],
    "summary": "Audit passed.",
    "completed_at": datetime.now(timezone.utc).isoformat()
}
deliverable_json = json.dumps(deliverable, sort_keys=True, separators=(",", ":"))
deliverable_sig = sign_bytes(seller.private_key, deliverable_json.encode("utf-8"))
deadline = (datetime.now(timezone.utc) + timedelta(hours=24)).timestamp()

# -------------------------------------------------------------
# اختبار أمني 1: هجوم بائع خبيث يطلب 5000 USDC بدلاً من 1250 USDC
# -------------------------------------------------------------
print("\n[*] محاكاة هجوم 1: البائع يطلب تسوية بـ 5000 USDC مع وثيقة 1250 USDC الأصلية...")
spoofed_payload_1 = {
    "session_id": str(session_id),
    "raw_deliverable_json": deliverable_json,
    "seller_pub_key_hex": seller.public_key_hex,
    "delivery_signature_hex": deliverable_sig,
    "deadline_timestamp": deadline,
    "deal_amount_usdc": 5000.0,  # السعر المضخم
    "price_commitment": legit_commitment.model_dump(mode="json"),
    "item_description": "Spoofed Settlement Attempt"
}

resp1 = client.post("/arbiter/settle", json=spoofed_payload_1)
assert resp1.status_code == 403, "ثغرة! الخادم قبل السعر المضخم!"
print(f"[1] تم صد الهجوم بنجاح (403 Forbidden): {resp1.json()['detail']}")

# -------------------------------------------------------------
# اختبار أمني 2: البائع يزور التزاماً جديداً بـ 5000 USDC بمفتاح مزيف
# -------------------------------------------------------------
print("\n[*] محاكاة هجوم 2: البائع يزور وثيقة التزام جديدة بـ 5000 USDC بتوقيع مفتاح مجهول...")
fake_priv, fake_pub = generate_keypair()
fake_commitment = legit_commitment.model_copy(update={
    "agreed_amount_usdc": 5000.0,
    "buyer_signature_hex": sign_bytes(fake_priv, legit_commitment.digest_bytes())
})

spoofed_payload_2 = {
    "session_id": str(session_id),
    "raw_deliverable_json": deliverable_json,
    "seller_pub_key_hex": seller.public_key_hex,
    "delivery_signature_hex": deliverable_sig,
    "deadline_timestamp": deadline,
    "deal_amount_usdc": 5000.0,
    "price_commitment": fake_commitment.model_dump(mode="json"),
    "item_description": "Forged Signature Attempt"
}

resp2 = client.post("/arbiter/settle", json=spoofed_payload_2)
assert resp2.status_code == 403, "ثغرة! الخادم قبل التوقيع المزور!"
print(f"[2] تم صد الهجوم بنجاح (403 Forbidden): {resp2.json()['detail']}")

# -------------------------------------------------------------
# اختبار السيناريو المشروع: تسوية بالسعر الموثق والموقع (1250 USDC)
# -------------------------------------------------------------
print("\n[*] فحص التسوية المشروعة (1250 USDC الموقعة أصولاً)...")
legit_payload = {
    "session_id": str(session_id),
    "raw_deliverable_json": deliverable_json,
    "seller_pub_key_hex": seller.public_key_hex,
    "delivery_signature_hex": deliverable_sig,
    "deadline_timestamp": deadline,
    "deal_amount_usdc": 1250.0,
    "price_commitment": legit_commitment.model_dump(mode="json"),
    "item_description": "Legitimate Audit Settlement"
}

resp3 = client.post("/arbiter/settle", json=legit_payload)
assert resp3.status_code == 200, f"فشل التسوية المشروعة: {resp3.text}"
res3_data = resp3.json()

print(f"[3] نجاح التسوية المعتمدة أصولاً:")
print(f"    - القرار                  : {res3_data['status']}")
print(f"    - الفاتورة المعتمدة        : {res3_data['invoice_id']}")
print(f"    - قيمة الصفقة الدقيقة      : {res3_data['settlement']['total_usdc']} USDC")
print(f"    - عمولة منصتك المحمية      : {res3_data['settlement']['platform_fee_usdc']} USDC")

print("\n=======================================================")
print("[+] تم إغلاق الثغرة الحرجة بنجاح تام: التلاعب بالأسعار مستحيل رياضياً!")
print("=======================================================")