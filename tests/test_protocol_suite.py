import pytest
from datetime import datetime, timezone, timedelta
import json
from fastapi.testclient import TestClient

from src.api.server import app
from nexus_arbiter.schemas import ItemType
from src.sdk.agent_client import NexusAgentClient
from nexus_arbiter.crypto.signatures import generate_keypair, sign_bytes, verify_signature

client = TestClient(app)

@pytest.fixture
def agents():
    buyer = NexusAgentClient(agent_id="agent:test_buyer")
    seller = NexusAgentClient(agent_id="agent:test_seller")
    return buyer, seller

def test_health_check():
    """التحقق من جاهزية الخادم وحالة التحصين الأمني."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["hardened"] is True
    assert data["security"]["anti_spoofing"] == "ENFORCED"

def test_crypto_signatures():
    """التحقق من سلامة تواقيع Ed25519 رياضياً."""
    priv, pub = generate_keypair()
    pub_hex = pub.public_bytes_raw().hex()
    msg = b"NexusArbiter-Integrity-Check"
    sig = sign_bytes(priv, msg)
    assert verify_signature(pub_hex, sig, msg) is True
    assert verify_signature(pub_hex, sig, b"Tampered-Data") is False

def test_e2ee_negotiation_and_settlement(agents):
    """اختبار الدورة الكاملة: تفاوض مشفر -> قبول -> التزام سعر -> تحكيم وتسوية."""
    buyer, seller = agents

    # 1. عرض أولي مشفر
    session_id, buyer_env, _ = buyer.propose_encrypted(
        peer_enc_pubkey_hex=seller.enc_public_key_hex,
        item_type=ItemType.SECURITY_AUDIT,
        price_unit=1000.0,
        sla_hours=24,
        client=client
    )

    # 2. قبول البائع
    seller.sync_sequence(session_id, 2)
    seller_decrypted = seller.decrypt_received_payload(session_id, buyer_env)
    assert seller_decrypted["price_unit"] == 1000.0

    seller.accept(session_id=session_id, agreed_payload=buyer_env, sequence_id=2, client=client)

    # 3. توقيع التزام السعر لمنع التلاعب
    commitment = buyer.create_price_commitment(
        session_id=session_id,
        agreed_amount_usdc=1000.0,
        seller_agent_id=seller.agent_id
    )

    # 4. تسليم التقرير والتسوية واعتماد العمولة
    report = {
        "session_id": str(session_id),
        "item_type": "SECURITY_AUDIT",
        "target": "https://test.internal",
        "findings": [],
        "summary": "Passed",
        "completed_at": datetime.now(timezone.utc).isoformat()
    }
    deadline = (datetime.now(timezone.utc) + timedelta(hours=24)).timestamp()

    settle_resp = seller.submit_and_settle(
        session_id=session_id,
        deliverable_dict=report,
        deadline_timestamp=deadline,
        deal_amount_usdc=1000.0,
        price_commitment=commitment,
        client=client
    )

    assert settle_resp["status"] == "APPROVED"
    assert settle_resp["settlement"]["total_usdc"] == 1000.0
    assert settle_resp["settlement"]["platform_fee_usdc"] == 15.0  # اقتطاع 1.5%
    assert settle_resp["settlement"]["seller_net_usdc"] == 985.0

def test_anti_price_spoofing_guard(agents):
    """التأكد من صد أي محاولة لتضخيم السعر المشفر دون توقيع المشتري."""
    buyer, seller = agents

    session_id, buyer_env, _ = buyer.propose_encrypted(
        peer_enc_pubkey_hex=seller.enc_public_key_hex,
        item_type=ItemType.SECURITY_AUDIT,
        price_unit=500.0,
        client=client
    )
    seller.sync_sequence(session_id, 2)
    seller.accept(session_id=session_id, agreed_payload=buyer_env, sequence_id=2, client=client)

    commitment = buyer.create_price_commitment(session_id, 500.0, seller.agent_id)

    report = {"session_id": str(session_id), "item_type": "SECURITY_AUDIT"}
    raw_json = json.dumps(report, sort_keys=True, separators=(",", ":"))
    sig = sign_bytes(seller.private_key, raw_json.encode("utf-8"))

    # محاولة التسوية بـ 5000 USDC بدلاً من 500 USDC
    spoofed_req = {
        "session_id": str(session_id),
        "raw_deliverable_json": raw_json,
        "seller_pub_key_hex": seller.public_key_hex,
        "delivery_signature_hex": sig,
        "deadline_timestamp": (datetime.now(timezone.utc) + timedelta(hours=24)).timestamp(),
        "deal_amount_usdc": 5000.0,
        "price_commitment": commitment.model_dump(mode="json"),
        "item_description": "Spoof Attack"
    }
    resp = client.post("/arbiter/settle", json=spoofed_req)
    assert resp.status_code == 403

def test_dos_large_payload_protection():
    """التأكد من رفض الحزم التي تتجاوز سعة 128 KB لحماية الذاكرة."""
    junk = "A" * (150 * 1024)
    resp = client.post("/negotiate/step", json={"junk": junk})
    assert resp.status_code == 413