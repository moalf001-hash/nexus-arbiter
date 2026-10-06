import time
import httpx
from uuid import UUID
from nexus_arbiter import NexusAgentClient
from nexus_arbiter.schemas import ItemType

# ضع رابط الـ Cloudflare الفعلي أو المحلي:
GATEWAY_URL = "https://simple-filled-starts-faqs.trycloudflare.com"

def run_live_escrow_lifecycle():
    print("==================================================")
    print("   NexusArbiter - Live Cloud Negotiation & Escrow  ")
    print("==================================================")

    buyer = NexusAgentClient(agent_id="agent:enterprise_buyer", gateway_url=GATEWAY_URL)
    seller = NexusAgentClient(agent_id="agent:secops_provider", gateway_url=GATEWAY_URL)
    
    print(f"[+] Buyer Online : {buyer.agent_id} (Pubkey: {buyer.public_key_hex[:16]}...)")
    print(f"[+] Seller Online: {seller.agent_id} (Pubkey: {seller.public_key_hex[:16]}...)")

    item_type = list(ItemType)[0]
    deal_price = 1500.0

    # 1. المشتري يرسل العرض المشفر (Sequence = 1)
    print("\n[*] Step 1: Buyer sending Encrypted Proposal (Seq 1)...")
    session_id, enc_envelope, prop_res = buyer.propose_encrypted(
        peer_enc_pubkey_hex=seller.enc_public_key_hex,
        item_type=item_type,
        price_unit=deal_price,
        quantity=1,
        sla_hours=24
    )
    print(f"[✓] Proposal Registered! Session ID: {session_id}")

    # 2. البائع يزامن التسلسل مع السيرفر ويقبل العرض (Sequence = 2)
    print("\n[*] Step 2: Seller syncing sequence to 2 and accepting...")
    seller.sync_sequence(session_id=session_id, next_sequence=2)
    try:
        accept_res = seller.accept(
            session_id=session_id,
            agreed_payload=enc_envelope,
            sequence_id=2
        )
        print(f"[✓] Seller Acceptance Verified by Protocol!")
    except httpx.HTTPStatusError as e:
        print(f"\n[-] FSM REJECTION DETAIL: {e.response.text}\n")
        raise e

    # 3. المشتري يوقع الالتزام المالي
    print("\n[*] Step 3: Buyer signing Cryptographic Price Commitment...")
    commitment = buyer.create_price_commitment(
        session_id=session_id,
        agreed_amount_usdc=deal_price,
        seller_agent_id=seller.agent_id
    )
    print(f"[✓] Price Commitment Signed: {commitment.buyer_signature_hex[:32]}...")

    # 4. البائع يسلّم مخرجات التدقيق الأمني مطابقة لـ SecurityAuditDeliverable
    print("\n[*] Step 4: Seller submitting deliverable for Settlement...")
    deliverable = {
        "session_id": str(session_id),
        "target": "192.168.1.100",
        "summary": "Full security audit completed successfully. Zero critical vulnerabilities found.",
        "findings": [
            {
                "id": "SEC-01",
                "severity": "INFO",
                "component": "SSH Service",
                "description": "Port 22 open with key-based authentication enforced."
            },
            {
                "id": "SEC-02",
                "severity": "LOW",
                "component": "TLS Configuration",
                "description": "TLS 1.3 enabled; legacy cipher suites disabled."
            }
        ]
    }
    deadline = time.time() + 86400

    try:
        settle_res = seller.submit_and_settle(
            session_id=session_id,
            deliverable_dict=deliverable,
            deadline_timestamp=deadline,
            deal_amount_usdc=deal_price,
            price_commitment=commitment,
            item_description="Automated Security Assessment"
        )
    except httpx.HTTPStatusError as e:
        print(f"\n[-] SETTLEMENT REJECTION DETAIL: {e.response.text}\n")
        raise e

    print("\n==================================================")
    print("[🎉] ARBITRATION & SETTLEMENT SUCCESSFUL!")
    print(f"     Session Status: {settle_res.get('status', 'SETTLED')}")
    print(f"     Settlement ID : {settle_res.get('settlement_id', 'N/A')}")
    print("==================================================")
    print(f"\n>> Check live updates on your dashboard: {GATEWAY_URL}/dashboard")

if __name__ == "__main__":
    run_live_escrow_lifecycle()