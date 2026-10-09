import sys
import os
import time
import requests
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

BASE_URL = "http://127.0.0.1:8000"

def generate_ed25519_keypair():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    return private_key, pub_bytes.hex()

def run_api_integration_tests():
    print("=" * 65)
    print("NexusArbiter: Marketplace Registry API Integration Test")
    print("=" * 65)

    # Health Check
    try:
        health_resp = requests.get(f"{BASE_URL}/health", timeout=5)
        assert health_resp.status_code == 200, f"Expected 200, got {health_resp.status_code}"
        print("[PASS] System Health Check passed.")
    except Exception as e:
        print(f"[FAIL] Unable to connect to server at {BASE_URL}: {e}")
        print("       Please ensure uvicorn is running.")
        sys.exit(1)

    priv_key, pub_key_hex = generate_ed25519_keypair()
    agent_id = "agent_gpu_cluster_01"
    endpoint = "https://api.compute-provider.net/v1"
    nonce = int(time.time())

    # 1. Test Valid Agent Registration (Expected: 201 Created)
    canonical = f"REGISTER:{agent_id}:{pub_key_hex}:{endpoint}:{nonce}".encode("utf-8")
    sig_hex = priv_key.sign(canonical).hex()

    valid_payload = {
        "agent_id": agent_id,
        "public_key_hex": pub_key_hex,
        "endpoint_url": endpoint,
        "capabilities": [
            {
                "name": "High-Throughput GPU Inference",
                "category": "compute",
                "description": "8x H100 dedicated cluster for LLM evaluation",
                "price_usdc": 45.0,
                "sla_seconds": 1800
            }
        ],
        "nonce": nonce,
        "signature": sig_hex
    }

    res = requests.post(f"{BASE_URL}/registry/register", json=valid_payload, timeout=5)
    assert res.status_code == 201, f"Expected 201, got {res.status_code} - {res.text}"
    print("[PASS] Test 1: Valid agent successfully registered via API (HTTP 201).")

    # 2. Test Spoofed Signature (Expected: 403 Forbidden)
    spoofed_payload = dict(valid_payload)
    spoofed_payload["signature"] = "00" * 64
    res_spoof = requests.post(f"{BASE_URL}/registry/register", json=spoofed_payload, timeout=5)
    assert res_spoof.status_code == 403, f"Expected 403, got {res_spoof.status_code}"
    print("[PASS] Test 2: Spoofed signature rejected via API (HTTP 403).")

    # 3. Test SSRF Exploit URL (Expected: 400 Bad Request)
    ssrf_endpoint = "http://127.0.0.1:9000/admin"
    ssrf_canonical = f"REGISTER:attacker:{pub_key_hex}:{ssrf_endpoint}:{nonce}".encode("utf-8")
    ssrf_sig = priv_key.sign(ssrf_canonical).hex()

    ssrf_payload = dict(valid_payload)
    ssrf_payload["agent_id"] = "attacker_agent"
    ssrf_payload["endpoint_url"] = ssrf_endpoint
    ssrf_payload["signature"] = ssrf_sig

    res_ssrf = requests.post(f"{BASE_URL}/registry/register", json=ssrf_payload, timeout=5)
    assert res_ssrf.status_code == 400, f"Expected 400, got {res_ssrf.status_code}"
    print("[PASS] Test 3: SSRF internal IP blocked via API (HTTP 400).")

    # 4. Test Marketplace Search & Filtering (Expected: 200 OK)
    res_search = requests.get(f"{BASE_URL}/registry/search?category=compute&max_price=50", timeout=5)
    assert res_search.status_code == 200, f"Expected 200, got {res_search.status_code}"
    search_data = res_search.json()
    assert search_data["total_matches"] >= 1, "Expected at least 1 match"
    print(f"[PASS] Test 4: Search returned {search_data['total_matches']} matching active service(s) (HTTP 200).")

    print("=" * 65)
    print("ALL API INTEGRATION TESTS PASSED SUCCESSFULLY")
    print("=" * 65)

if __name__ == "__main__":
    run_api_integration_tests()
