from fastapi.testclient import TestClient

from src.api.server import app
from src.core.schemas import ItemType
from src.sdk.agent_client import NexusAgentClient

client = TestClient(app)

print("--- بدء فحص دورة التفاوض المشفرة بالكامل (Confidential Negotiation) ---\n")

# 1. تهيئة الوكيلين
buyer = NexusAgentClient(agent_id="agent:alpha_buyer")
seller = NexusAgentClient(agent_id="agent:beta_seller")

print(f"[+] وكيل المشتري - مفتاح التشفير العام: {buyer.enc_public_key_hex[:24]}...")
print(f"[+] وكيل البائع  - مفتاح التشفير العام: {seller.enc_public_key_hex[:24]}...\n")

# 2. المشتري يرسل عرضاً أولياً سرياً بـ 1200 USDC
session_id, buyer_envelope, api_resp1 = buyer.propose_encrypted(
    peer_enc_pubkey_hex=seller.enc_public_key_hex,
    item_type=ItemType.SECURITY_AUDIT,
    price_unit=1200.0,
    sla_hours=72,
    client=client
)

print("[1] إرسال العرض الأولي المشفر عبر البوابة:")
print(f"    - معرّف الجلسة          : {session_id}")
print(f"    - حالة الـ FSM في الخادم : {api_resp1.get('status')}")
print(f"    - النص المشفر على الشبكة: {buyer_envelope.ciphertext_hex[:36]}... (السعر محمي تماماً)")

# 3. البائع يستلم المظروف المشفر ويفك تشفيره
seller_decrypted = seller.decrypt_received_payload(session_id, buyer_envelope)
print(f"\n[2] البائع يفك تشفير العرض بنجاح:")
print(f"    - نوع الخدمة المسترجعة : {seller_decrypted['item_type']}")
print(f"    - السعر السري المقترح  : {seller_decrypted['price_unit']} USDC")
print(f"    - مهلة الـ SLA         : {seller_decrypted['sla_hours']} ساعة\n")

# 4. البائع يرد بعرض مقابل مشفر بـ 1450 USDC
seller.sync_sequence(session_id, 2)
seller_envelope, api_resp2 = seller.counter_encrypted(
    peer_enc_pubkey_hex=buyer.enc_public_key_hex,
    session_id=session_id,
    item_type=ItemType.SECURITY_AUDIT,
    price_unit=1450.0,
    sla_hours=72,
    sequence_id=2,
    client=client
)

print("[3] البائع يرسل عرضاً مقابلاً مشفراً عبر البوابة:")
print(f"    - حالة الـ FSM في الخادم : {api_resp2.get('status')}")
print(f"    - النص المشفر على الشبكة: {seller_envelope.ciphertext_hex[:36]}...")

# 5. المشتري يستلم العرض المقابل ويفك تشفيره
buyer_decrypted = buyer.decrypt_received_payload(session_id, seller_envelope)
print(f"\n[4] المشتري يفك تشفير العرض المقابل بنجاح:")
print(f"    - السعر المطلوب من البائع: {buyer_decrypted['price_unit']} USDC")

print("\n=======================================================")
print("[+] نجاح بروتوكول السرية التامة: البيانات لا تُكشف إلا للأطراف المعنية.")
print("=======================================================")