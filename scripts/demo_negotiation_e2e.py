import time
import httpx
from uuid import uuid4

from src.sdk.agent_client import NexusAgentClient
from nexus_arbiter.schemas import ItemType, NegotiationPayload, ActionType

GATEWAY_URL = "http://127.0.0.1:8000"

print("================================================================")
print("🤖 NexusArbiter E2E Autonomous Negotiation & Settlement Demo")
print("================================================================")

# 1. إنشاء مفتاح B2B API Key جديد
print("\n[1] Registering enterprise tenant and obtaining API key...")
admin_resp = httpx.post(f"{GATEWAY_URL}/api/admin/tenants", json={
    "name": "Autonomous Agent Network Corp",
    "tier": "enterprise",
    "monthly_limit": 500
})
tenant_data = admin_resp.json()
api_key = tenant_data["api_key"]
print(f"  [+] Tenant Created: {tenant_data['name']} (ID: {tenant_data['tenant_id']})")
print(f"  [+] API Key Issued: {tenant_data['prefix']}...")

client = httpx.Client(headers={"X-Nexus-API-Key": api_key}, timeout=60.0)

# 2. تهيئة وكيل المشتري ووكيل البائع
print("\n[2] Initializing autonomous agents with Ed25519 & X25519 keypairs...")
buyer = NexusAgentClient(agent_id="agent:buyer_ai_researcher", gateway_url=GATEWAY_URL)
seller = NexusAgentClient(agent_id="agent:seller_gpu_cluster", gateway_url=GATEWAY_URL)
print(f"  [+] Buyer PubKey:  {buyer.public_key_hex[:16]}...")
print(f"  [+] Seller PubKey: {seller.public_key_hex[:16]}...")

# 3. خطوة العرض المبدئي من المشتري (PROPOSE)
session_id = uuid4()
print(f"\n[3] Step 1: Buyer initiates session {session_id} with PROPOSE...")
propose_payload = NegotiationPayload(
    item_type=ItemType.SECURITY_AUDIT,
    price_unit=1200.0,
    quantity=1,
    sla_hours=48
)
res_1 = buyer._sign_and_post_step(session_id, ActionType.PROPOSE, propose_payload, sequence_id=1, client=client)
print(f"  [+] Status: {res_1['status']} | Expected next seq: {res_1['sequence_id'] + 1}")

# 4. رد البائع بعرض مضاد (COUNTER)
print("\n[4] Step 2: Seller counters price to 1500.0 USDC...")
counter_payload = NegotiationPayload(
    item_type=ItemType.SECURITY_AUDIT,
    price_unit=1500.0,
    quantity=1,
    sla_hours=48
)
res_2 = seller._sign_and_post_step(session_id, ActionType.COUNTER, counter_payload, sequence_id=2, client=client)
print(f"  [+] Status: {res_2['status']} | Expected next seq: {res_2['sequence_id'] + 1}")

# 5. قبول المشتري للعرض النهائي (ACCEPT)
print("\n[5] Step 3: Buyer accepts the counter-offer at 1500.0 USDC...")
res_3 = buyer.accept(session_id, agreed_payload=counter_payload, sequence_id=3, client=client)
print(f"  [+] Final Session State: {res_3['status']} | Terminal Price: ${res_3['agreed_price']} USDC")

# 6. تسليم مخرجات العمل وطلب التحكيم المالي (PROOF OF DELIVERY & SETTLE)
print("\n[6] Step 4: Seller submits canonical deliverable for settlement...")
deliverable = {
    "session_id": str(session_id),
    "item_type": "SECURITY_AUDIT",
    "target": "smart-contract-vault-v2",
    "findings": [
        {
            "id": "VULN-001",
            "severity": "HIGH",
            "component": "WithdrawalModule",
            "description": "Missing reentrancy guard on external calls"
        }
    ],
    "summary": "Full security audit executed successfully with zero critical vulnerabilities.",
    "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
}

deadline = time.time() + 7200
settle_res = seller.submit_and_settle(
    session_id=session_id,
    deliverable_dict=deliverable,
    deadline_timestamp=deadline,
    deal_amount_usdc=1500.0,
    item_description="Automated AI Smart Contract Audit",
    client=client
)

print("\n================================================================")
print("✅ ARBITRATION & ON-CHAIN SETTLEMENT SUCCESSFUL!")
print(f"  [+] Invoice ID:       {settle_res['invoice_id']}")
print(f"  [+] Deliverable Hash: {settle_res['deliverable_hash'][:24]}...")
print(f"  [+] Total Escrow:     ${settle_res['settlement']['total_usdc']} USDC")
print(f"  [+] Platform Fee:     ${settle_res['settlement']['platform_fee_usdc']} USDC (1.5%)")
print(f"  [+] Seller Net:       ${settle_res['settlement']['seller_net_usdc']} USDC")
print(f"  [+] Calldata Ready:   {settle_res['blockchain_settlement']['calldata'][:32]}...")
print("================================================================")