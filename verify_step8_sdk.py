from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from src.api.server import app
from src.core.schemas import ItemType, NegotiationPayload
from src.sdk.agent_client import NexusAgentClient

client = TestClient(app)

print("--- بدء فحص حزمة NexusAgentClient (Agent SDK) ---\n")

# 1. تهيئة وكيلي ذكاء اصطناعي عبر الـ SDK
buyer_agent = NexusAgentClient(agent_id="agent:buyer_ai")
seller_agent = NexusAgentClient(agent_id="agent:seller_sec_expert")

print(f"[1] تم إنشاء وكيل المشتري بنجاح:")
print(f"    - المعرف     : {buyer_agent.agent_id}")
print(f"    - المفتاح العام: {buyer_agent.public_key_hex[:24]}...")

print(f"[2] تم إنشاء وكيل البائع بنجاح:")
print(f"    - المعرف     : {seller_agent.agent_id}")
print(f"    - المفتاح العام: {seller_agent.public_key_hex[:24]}...\n")

# 2. المشتري يبدأ الجلسة بعرض 400 USDC (sequence = 1)
session_id, r1 = buyer_agent.propose(
    item_type=ItemType.SECURITY_AUDIT,
    price_unit=400.0,
    sla_hours=48,
    client=client
)
print(f"[3] خطوة المشتري (propose 400 USDC):")
print(f"    - رقم الجلسة: {session_id}")
print(f"    - استجابة البوابة: {r1}\n")

# 3. البائع يستلم ويقوم بمزامنة التسلسل ويرد بعرض 550 USDC (sequence = 2)
seller_agent.sync_sequence(session_id, 2)
r2 = seller_agent.counter(
    session_id=session_id,
    item_type=ItemType.SECURITY_AUDIT,
    price_unit=550.0,
    sla_hours=48,
    client=client
)
print(f"[4] خطوة البائع (counter 550 USDC):")
print(f"    - استجابة البوابة: {r2}\n")

# 4. المشتري يزامن التسلسل مع خطوة البائع ويرسل القبول (sequence = 3)
buyer_agent.sync_sequence(session_id, 3)
agreed_payload = NegotiationPayload(
    item_type=ItemType.SECURITY_AUDIT,
    price_unit=550.0,
    quantity=1,
    sla_hours=48
)
r3 = buyer_agent.accept(
    session_id=session_id,
    agreed_payload=agreed_payload,
    client=client
)
print(f"[5] خطوة المشتري (accept 550 USDC):")
print(f"    - الحالة النهائية : {r3.get('status')}")
print(f"    - السعر المتفق عليه: {r3.get('agreed_price')} USDC\n")

# 5. البائع يسلم العمل ويطلب التسوية والصرف عبر الـ SDK
deliverable_report = {
    "session_id": str(session_id),
    "item_type": "SECURITY_AUDIT",
    "target": "https://vault.ai-agents.internal",
    "findings": [
        {
            "id": "SEC-01",
            "severity": "CRITICAL",
            "component": "/auth/token",
            "description": "Unbounded memory allocation during ECDSA verification"
        }
    ],
    "summary": "Completed comprehensive penetration testing.",
    "completed_at": datetime.now(timezone.utc).isoformat()
}

deadline_ts = (datetime.now(timezone.utc) + timedelta(hours=48)).timestamp()

settle_res = seller_agent.submit_and_settle(
    session_id=session_id,
    deliverable_dict=deliverable_report,
    deadline_timestamp=deadline_ts,
    item_description="Penetration Testing & Smart Contract Audit",
    client=client
)

print(f"[6] نتيجة التحكيم والتسوية المالية عبر الـ SDK:")
print(f"    - حالة الاعتماد     : {settle_res.get('status')}")
print(f"    - رقم الفاتورة       : {settle_res.get('invoice_id')}")
print(f"    - عمولة المنصة (لك) : {settle_res.get('settlement', {}).get('platform_fee_usdc')} USDC (1.5%)")
print(f"    - صافي أرباح البائع : {settle_res.get('settlement', {}).get('seller_net_usdc')} USDC")
print(f"    - بصمة الفاتورة     : {settle_res.get('invoice_hash')}")