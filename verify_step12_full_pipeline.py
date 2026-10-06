from datetime import datetime, timezone, timedelta
import json
from fastapi.testclient import TestClient

from src.api.server import app
from src.core.schemas import ItemType
from src.sdk.agent_client import NexusAgentClient
from src.crypto.signatures import sign_bytes

client = TestClient(app)

print("--- فحص ربط التحكيم بمعاملات البلوكتشين المشفرة (On-Chain Bridge) ---\n")

buyer = NexusAgentClient(agent_id="agent:alpha_buyer")
seller = NexusAgentClient(agent_id="agent:beta_seller")

# 1. المشتري يرسل عرضاً مشفراً بـ 1500 USDC
session_id, buyer_env, _ = buyer.propose_encrypted(
    peer_enc_pubkey_hex=seller.enc_public_key_hex,
    item_type=ItemType.SECURITY_AUDIT,
    price_unit=1500.0,
    sla_hours=24,
    client=client
)
print(f"[1] إنشاء الجلسة المشفرة من المشتري: {session_id}")

# 2. البائع يستلم العرض، يفك تشفيره، ويوافق عليه (ACCEPT)
seller_decrypted = seller.decrypt_received_payload(session_id, buyer_env)
agreed_price = seller_decrypted["price_unit"]
print(f"[2] البائع يفك التشفير بنجاح ويوافق على السعر: {agreed_price} USDC")

seller.sync_sequence(session_id, 2)
accept_resp = seller.accept(session_id=session_id, agreed_payload=buyer_env, sequence_id=2, client=client)
print(f"    - حالة الجلسة على الخادم: {accept_resp.get('status')} | مشفرة: {accept_resp.get('is_encrypted')}\n")

# 3. تقديم التقرير وطلب التسوية مع توليد معاملة البلوكتشين
deliverable = {
    "session_id": str(session_id),
    "item_type": "SECURITY_AUDIT",
    "target": "https://api.defi-protocol.internal",
    "findings": [
        {"id": "SEC-101", "severity": "CRITICAL", "component": "/escrow/settle", "description": "Pass"}
    ],
    "summary": "Full security audit passed.",
    "completed_at": datetime.now(timezone.utc).isoformat()
}

deliverable_json = json.dumps(deliverable, sort_keys=True, separators=(",", ":"))
deliverable_sig = sign_bytes(seller.private_key, deliverable_json.encode("utf-8"))
deadline = (datetime.now(timezone.utc) + timedelta(hours=24)).timestamp()

settle_payload = {
    "session_id": str(session_id),
    "raw_deliverable_json": deliverable_json,
    "seller_pub_key_hex": seller.public_key_hex,
    "delivery_signature_hex": deliverable_sig,
    "deadline_timestamp": deadline,
    "deal_amount_usdc": agreed_price,
    "item_description": "Comprehensive Core Security Audit"
}

resp = client.post("/arbiter/settle", json=settle_payload)
assert resp.status_code == 200, f"فشل الطلب: {resp.text}"
data = resp.json()

print("[3] استجابة محرك التحكيم وجسر البلوكتشين:")
print(f"    - القرار                  : {data['status']}")
print(f"    - رقم الفاتورة             : {data['invoice_id']}")
print(f"    - عمولة منصتك (1.5%)       : {data['settlement']['platform_fee_usdc']} USDC")
print(f"    - صافي مستحق البائع        : {data['settlement']['seller_net_usdc']} USDC")
print(f"\n[4] حمولة معاملة البلوكتشين المولدة (Ready-to-Broadcast):")
print(f"    - عنوان العقد الذكي المستهدف: {data['blockchain_settlement']['target_contract']}")
print(f"    - دالة العقد المشفرة        : {data['blockchain_settlement']['calldata'][:10]}")
print(f"    - طول بيانات الـ Calldata   : {len(data['blockchain_settlement']['calldata'])} حرف")
print(f"    - جاهزية البث المباشر       : {data['blockchain_settlement']['ready_for_broadcast']}")

print("\n=======================================================")
print("[+] تم ربط خادم التحكيم بالبلوكتشين بنجاح تام 100%.")
print("=======================================================")