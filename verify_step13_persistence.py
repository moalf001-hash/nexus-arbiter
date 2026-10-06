from datetime import datetime, timezone, timedelta
import json
import sqlite3
from fastapi.testclient import TestClient

from src.api.server import app
from src.core.schemas import ItemType
from src.sdk.agent_client import NexusAgentClient
from src.crypto.signatures import sign_bytes

client = TestClient(app)

print("--- بدء فحص طبقة التخزين الدائم (SQLite Persistence Audit) ---\n")

buyer = NexusAgentClient(agent_id="agent:alpha_buyer")
seller = NexusAgentClient(agent_id="agent:beta_seller")

# 1. إرسال عرض مشفر بـ 2000 USDC
session_id, buyer_env, _ = buyer.propose_encrypted(
    peer_enc_pubkey_hex=seller.enc_public_key_hex,
    item_type=ItemType.SECURITY_AUDIT,
    price_unit=2000.0,
    sla_hours=48,
    client=client
)
print(f"[1] إنشاء الجلسة في قاعدة البيانات: {session_id}")

# 2. البائع يوافق على العرض
seller_decrypted = seller.decrypt_received_payload(session_id, buyer_env)
agreed_price = seller_decrypted["price_unit"]

seller.sync_sequence(session_id, 2)
seller.accept(session_id=session_id, agreed_payload=buyer_env, sequence_id=2, client=client)
print("[2] تم تسجيل موافقة البائع وتثبيت الحالة في SQLite.")

# 3. تقديم التقرير واعتماد التسوية
deliverable = {
    "session_id": str(session_id),
    "item_type": "SECURITY_AUDIT",
    "target": "https://defi-lending.protocol.internal",
    "findings": [
        {"id": "SEC-500", "severity": "HIGH", "component": "/liquidations", "description": "Strict boundary checks verified"}
    ],
    "summary": "Persistence validation audit passed.",
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
    "item_description": "Smart Contract Lending Pool Audit"
}

resp = client.post("/arbiter/settle", json=settle_payload)
assert resp.status_code == 200, f"فشل التسوية: {resp.text}"
settle_res = resp.json()
print(f"[3] تمت التسوية وإصدار الفاتورة: {settle_res['invoice_id']}")

# 4. الاستعلام المباشر من ملف قاعدة البيانات nexus_arbiter.db للتحقق من الحفظ على القرص الصلب
print("\n--- التحقق من السجلات المخزنة على القرص الصلب (nexus_arbiter.db) ---")
conn = sqlite3.connect("nexus_arbiter.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# التحقق من جدول الجلسات
cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (str(session_id),))
session_row = cursor.fetchone()
print(f"[+] جدول الجلسات (Sessions):")
print(f"    - الحالة المسجلة : {session_row['status']}")
print(f"    - أطراف العقد    : المشتري ({session_row['buyer_id']}) <-> البائع ({session_row['seller_id']})")

# التحقق من جدول الرسائل والتواقيع
cursor.execute("SELECT COUNT(*) as msg_count FROM messages WHERE session_id = ?", (str(session_id),))
msg_count = cursor.fetchone()["msg_count"]
print(f"\n[+] سجل التدقيق والتواقيع (Messages):")
print(f"    - عدد الرسائل والتواقيع الموثقة تشفيرياً: {msg_count} رسائل")

# التحقق من جدول الفواتير
cursor.execute("SELECT * FROM invoices WHERE session_id = ?", (str(session_id),))
inv_row = cursor.fetchone()
print(f"\n[+] جدول الفواتير الضريبية (Invoices):")
print(f"    - رقم الفاتورة           : {inv_row['invoice_id']}")
print(f"    - إجمالي الصفقة          : {inv_row['total_usdc']} USDC")
print(f"    - عمولة المنصة المخزنة   : {inv_row['platform_fee_usdc']} USDC (1.5%)")
print(f"    - صافي البائع             : {inv_row['seller_net_usdc']} USDC")
print(f"    - هاش الفاتورة المشفر     : {inv_row['invoice_hash']}")
print(f"    - كود البلوكتشين المخزن   : {inv_row['blockchain_calldata'][:20]}...")

conn.close()
print("\n=======================================================")
print("[+] نجاح التخزين الدائم: كل البيانات محفوظة على القرص وغير قابلة للضياع!")
print("=======================================================")