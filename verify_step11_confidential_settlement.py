from datetime import datetime, timezone, timedelta
import json
from fastapi.testclient import TestClient

from src.api.server import app
from src.core.schemas import ItemType
from src.sdk.agent_client import NexusAgentClient
from src.crypto.signatures import sign_bytes

client = TestClient(app)

print("--- فحص دورة التعاقد والتحكيم المشفرة بالكامل حتى التسوية المالية ---\n")

buyer = NexusAgentClient(agent_id="agent:alpha_buyer")
seller = NexusAgentClient(agent_id="agent:beta_seller")

# 1. عرض أولي مشفر (1200 USDC)
session_id, buyer_env, _ = buyer.propose_encrypted(
    peer_enc_pubkey_hex=seller.enc_public_key_hex,
    item_type=ItemType.SECURITY_AUDIT,
    price_unit=1200.0,
    sla_hours=48,
    client=client
)
print(f"[1] المشتري يرسل عرضاً مشفراً (الجلسة: {session_id})")

# 2. عرض مقابل مشفر (1450 USDC)
seller.sync_sequence(session_id, 2)
seller_env, _ = seller.counter_encrypted(
    peer_enc_pubkey_hex=buyer.enc_public_key_hex,
    session_id=session_id,
    item_type=ItemType.SECURITY_AUDIT,
    price_unit=1450.0,
    sla_hours=48,
    sequence_id=2,
    client=client
)
print("[2] البائع يرد بعرض مقابل مشفر بـ 1450 USDC")

# 3. المشتري يفك تشفير العرض ويوافق عليه (ACCEPT)
buyer_decrypted = buyer.decrypt_received_payload(session_id, seller_env)
agreed_price = buyer_decrypted["price_unit"]
print(f"[3] المشتري يفك التشفير بنجاح ويوافق على السعر: {agreed_price} USDC")

buyer.sync_sequence(session_id, 3)
accept_resp = buyer.accept(
    session_id=session_id,
    agreed_payload=seller_env,
    sequence_id=3,
    client=client
)
print(f"    - حالة الجلسة على الخادم: {accept_resp.get('status')} | مشفرة: {accept_resp.get('is_encrypted')}\n")

# 4. تسليم التقرير والتحكيم والتسوية المالية
deliverable = {
    "session_id": str(session_id),
    "item_type": "SECURITY_AUDIT",
    "target": "https://vault.core.internal",
    "findings": [
        {"id": "SEC-09", "severity": "HIGH", "component": "/crypto/x25519", "description": "Strict scalar check passed"}
    ],
    "summary": "Confidential audit completed successfully.",
    "completed_at": datetime.now(timezone.utc).isoformat()
}

deliverable_json = json.dumps(deliverable, sort_keys=True, separators=(",", ":"))
deliverable_sig = sign_bytes(seller.private_key, deliverable_json.encode("utf-8"))
deadline = (datetime.now(timezone.utc) + timedelta(hours=48)).timestamp()

settle_payload = {
    "session_id": str(session_id),
    "raw_deliverable_json": deliverable_json,
    "seller_pub_key_hex": seller.public_key_hex,
    "delivery_signature_hex": deliverable_sig,
    "deadline_timestamp": deadline,
    "deal_amount_usdc": agreed_price,
    "item_description": "Confidential Zero-Knowledge Security Audit"
}

settle_resp = client.post("/arbiter/settle", json=settle_payload)
assert settle_resp.status_code == 200, f"فشل التسوية: {settle_resp.text}"
settle_data = settle_resp.json()

print("[4] نتيجة التحكيم والتسوية المالية للصفقة المشفرة:")
print(f"    - حالة الاعتماد        : {settle_data['status']}")
print(f"    - رقم الفاتورة الضريبية : {settle_data['invoice_id']}")
print(f"    - إجمالي الصفقة        : {settle_data['settlement']['total_usdc']} USDC")
print(f"    - أرباحك الصافية (1.5%): {settle_data['settlement']['platform_fee_usdc']} USDC (تم اقتطاعها آلياً)")
print(f"    - صافي مستحق البائع   : {settle_data['settlement']['seller_net_usdc']} USDC")
print(f"    - بصمة الفاتورة المشفرة: {settle_data['invoice_hash']}")
print("\n[+] اكتملت دورة الحياة المشفرة بالكامل بنجاح 100%.")