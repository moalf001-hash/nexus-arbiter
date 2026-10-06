"""
NexusArbiter SDK - Quickstart Example
Demonstrates initializing an autonomous agent and signing an Anti-Price Spoofing Commitment.
"""

from uuid import uuid4
from nexus_arbiter import NexusAgentClient

def main():
    print("==================================================")
    print("   NexusArbiter SDK - Autonomous Buyer Demo")
    print("==================================================")

    # 1. Initialize Autonomous Buyer Agent Client
    buyer = NexusAgentClient(
        agent_id="agent:enterprise_buyer_demo",
        gateway_url="https://simple-filled-starts-faqs.trycloudflare.com"
    )

    print(f"\n[+] Agent ID: {buyer.agent_id}")
    print(f"[+] Ed25519 Cryptographic Public Key:\n    {buyer.public_key_hex}")

    # 2. Negotiate & Define Settlement Terms
    session_id = uuid4()
    agreed_price = 1800.0  # USDC
    seller_id = "agent:secops_provider"

    print(f"\n[*] Signing Buyer Price Commitment (Anti-Price Spoofing)...")
    print(f"    - Session ID     : {session_id}")
    print(f"    - Agreed Price   : {agreed_price} USDC")
    print(f"    - Seller Agent ID: {seller_id}")

    # 3. Cryptographically Sign the Price Commitment
    commitment = buyer.create_price_commitment(
        session_id=session_id,
        agreed_amount_usdc=agreed_price,
        seller_agent_id=seller_id
    )

    print("\n[+] Cryptographic Commitment Signed Successfully:")
    print(f"    - Ed25519 Signature:\n      {commitment.buyer_signature_hex[:32]}...{commitment.buyer_signature_hex[-16:]}")
    print("==================================================")
    print("[✓] Ready for integration into autonomous agent workflows.")

if __name__ == "__main__":
    main()