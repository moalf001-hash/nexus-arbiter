import pytest
import json
from fastapi.testclient import TestClient
from nexus_arbiter.schemas import ActionType, ItemType
from src.api.server import app
from src.auth.middleware import verify_tenant_access
from src.sdk.agent_client import NexusAgentClient

# Mock tenant authentication for automated tests
app.dependency_overrides[verify_tenant_access] = lambda: {
    "tenant_id": "test_tenant_dev",
    "tier": "enterprise",
    "name": "Automated Testing Suite"
}

client = TestClient(app)


@pytest.fixture
def agents():
    buyer = NexusAgentClient("agent:buyer_test")
    seller = NexusAgentClient("agent:seller_test")
    return buyer, seller


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    assert data["protocol"] == "NexusArbiter"


def test_crypto_signatures(agents):
    buyer, _ = agents
    assert len(buyer.public_key_hex) == 64
    assert len(buyer.enc_public_key_hex) == 64


def test_e2ee_negotiation_and_settlement(agents):
    buyer, seller = agents

    # 1. Propose Encrypted (Sequence 1)
    session_id, buyer_env, _ = buyer.propose_encrypted(
        peer_enc_pubkey_hex=seller.enc_public_key_hex,
        item_type=ItemType.SECURITY_AUDIT,
        price_unit=1000.0,
        sla_hours=24,
        client=client
    )
    assert session_id is not None

    # 2. Seller Accepts with Sequence 2
    accept_res = seller._sign_and_post_step(
        session_id=session_id,
        action=ActionType.ACCEPT,
        payload=buyer_env,
        sequence_id=2,
        client=client
    )
    assert accept_res["status"] == "ACCEPTED"

    # 3. Buyer Issues Price Commitment
    commitment = buyer.create_price_commitment(
        session_id=session_id,
        seller_agent_id=seller.agent_id,
        agreed_amount_usdc=1000.0
    )

    # 4. Seller Signs Deliverable Matching SecurityAuditDeliverable Schema
    deliverable_dict = {
        "session_id": str(session_id),
        "target": "smart_contract_core",
        "findings": [],
        "summary": "Protocol audited successfully with zero critical vulnerabilities."
    }
    deliverable_json = json.dumps(deliverable_dict)
    delivery_sig = seller.private_key.sign(deliverable_json.encode("utf-8")).hex()

    settle_payload = {
        "session_id": str(session_id),
        "raw_deliverable_json": deliverable_json,
        "seller_pub_key_hex": seller.public_key_hex,
        "delivery_signature_hex": delivery_sig,
        "deadline_timestamp": 9999999999.0,
        "deal_amount_usdc": 1000.0,
        "price_commitment": commitment.model_dump(mode="json"),
        "item_description": "Smart Contract Protocol Security Audit"
    }

    settle_res = client.post("/arbiter/settle", json=settle_payload)
    assert settle_res.status_code == 200, f"Settle failed: {settle_res.text}"
    settle_data = settle_res.json()
    assert settle_data["status"] == "APPROVED"
    assert settle_data["settlement"]["platform_fee_usdc"] == 15.0  # 1.5% take rate


def test_anti_price_spoofing_guard(agents):
    buyer, seller = agents

    session_id, buyer_env, _ = buyer.propose_encrypted(
        peer_enc_pubkey_hex=seller.enc_public_key_hex,
        item_type=ItemType.SECURITY_AUDIT,
        price_unit=500.0,
        client=client
    )

    # Seller accepts with Sequence 2
    accept_res = seller._sign_and_post_step(
        session_id=session_id,
        action=ActionType.ACCEPT,
        payload=buyer_env,
        sequence_id=2,
        client=client
    )
    assert accept_res["status"] == "ACCEPTED"

    # Buyer signs commitment for 500 USDC
    commitment = buyer.create_price_commitment(
        session_id=session_id,
        seller_agent_id=seller.agent_id,
        agreed_amount_usdc=500.0
    )

    deliverable_dict = {
        "session_id": str(session_id),
        "target": "smart_contract_core",
        "findings": [],
        "summary": "Audit completed."
    }
    deliverable_json = json.dumps(deliverable_dict)
    delivery_sig = seller.private_key.sign(deliverable_json.encode("utf-8")).hex()

    # Attacker tries to settle with inflated price (1000 USDC)
    tampered_payload = {
        "session_id": str(session_id),
        "raw_deliverable_json": deliverable_json,
        "seller_pub_key_hex": seller.public_key_hex,
        "delivery_signature_hex": delivery_sig,
        "deadline_timestamp": 9999999999.0,
        "deal_amount_usdc": 1000.0,
        "price_commitment": commitment.model_dump(mode="json")
    }

    res = client.post("/arbiter/settle", json=tampered_payload)
    assert res.status_code == 403
    assert "Price spoofing detected" in res.json()["detail"]


def test_dos_large_payload_protection():
    giant_payload = {"data": "X" * (200 * 1024)}
    res = client.post("/negotiate/step", json=giant_payload)
    assert res.status_code == 413
