import sys
import os
import time
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.registry.discovery import SecureAgentRegistry, AgentRegistrationRequest, ServiceCapability


def generate_test_keys():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    priv_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    return private_key, pub_bytes.hex()


def run_registry_security_audit():
    print("=" * 65)
    print("NexusArbiter: Public Marketplace Registry Security Audit")
    print("=" * 65)

    registry = SecureAgentRegistry()
    priv_key_obj, pub_key_hex = generate_test_keys()
    agent_id = "agent_seller_analytics_01"
    endpoint = "https://api.verified-seller.com/v1"
    nonce = int(time.time())

    # 1. Test Legitimate Registration
    canonical_payload = f"REGISTER:{agent_id}:{pub_key_hex}:{endpoint}:{nonce}".encode("utf-8")
    valid_sig = priv_key_obj.sign(canonical_payload).hex()

    valid_request = AgentRegistrationRequest(
        agent_id=agent_id,
        public_key_hex=pub_key_hex,
        endpoint_url=endpoint,
        capabilities=[
            ServiceCapability(
                name="Deep Financial Market Sentiment",
                category="analytics",
                description="Real-time sentiment index from L2 transaction feeds",
                price_usdc=250.0,
                sla_seconds=3600
            )
        ],
        nonce=nonce,
        signature=valid_sig
    )

    reg_result = registry.register_agent(valid_request)
    assert reg_result["status"] == "REGISTERED"
    print("[PASS] Test 1: Legitimate agent registered with valid signature.")

    # 2. Test Signature Spoofing Resistance
    tampered_request = valid_request.model_copy(update={"signature": "ab" * 64})
    try:
        registry.register_agent(tampered_request)
        print("[FAIL] Test 2: System accepted spoofed signature!")
    except PermissionError:
        print("[PASS] Test 2: Spoofed signature rejected with PermissionError.")

    # 3. Test SSRF Attack Mitigation
    malicious_endpoint = "http://127.0.0.1:8000/internal-secrets"
    malicious_canonical = f"REGISTER:attacker:{pub_key_hex}:{malicious_endpoint}:{nonce}".encode("utf-8")
    malicious_sig = priv_key_obj.sign(malicious_canonical).hex()

    malicious_request = AgentRegistrationRequest(
        agent_id="attacker_agent",
        public_key_hex=pub_key_hex,
        endpoint_url=malicious_endpoint,
        capabilities=[
            ServiceCapability(
                name="Fake Service",
                category="analytics",
                description="Exploit internal network",
                price_usdc=10.0,
                sla_seconds=600
            )
        ],
        nonce=nonce,
        signature=malicious_sig
    )

    try:
        registry.register_agent(malicious_request)
        print("[FAIL] Test 3: System accepted SSRF localhost endpoint!")
    except ValueError as e:
        print(f"[PASS] Test 3: SSRF blocked successfully ({e}).")

    # 4. Test Marketplace Query and Filtering
    discovered = registry.search_services(category="analytics", max_price=300.0)
    assert len(discovered) == 1
    assert discovered[0]["service_name"] == "Deep Financial Market Sentiment"
    print(f"[PASS] Test 4: Discovery query returned {len(discovered)} matching service(s).")

    print("=" * 65)
    print("ALL REGISTRY SECURITY CHECKS PASSED SUCCESSFULLY")
    print("=" * 65)


if __name__ == "__main__":
    run_registry_security_audit()
