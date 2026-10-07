import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timezone, timedelta
from nexus_arbiter.schemas import ItemType
from src.sdk.agent_client import NexusAgentClient

def main():
    print("=================================================================")
    print("   تشغيل وكلاء مستقلين عبر شبكة HTTP الحية (http://127.0.0.1:8000)   ")
    print("=================================================================\n")

    # تهيئة الوكيلين مع تحديد رابط السيرفر الحي
    buyer = NexusAgentClient(agent_id="agent:live_buyer", gateway_url="http://127.0.0.1:8000")
    seller = NexusAgentClient(agent_id="agent:live_seller", gateway_url="http://127.0.0.1:8000")

    print(f"[+] وكيل المشتري الحي: {buyer.agent_id}")
    print(f"[+] وكيل البائع الحي : {seller.agent_id}\n")

    # 1. إرسال عرض أولي مشفر بـ 1600 USDC عبر طلب HTTP POST حقيقي
    session_id, buyer_env, resp1 = buyer.propose_encrypted(
        peer_enc_pubkey_hex=seller.enc_public_key_hex,
        item_type=ItemType.SECURITY_AUDIT,
        price_unit=1600.0,
        sla_hours=24
    )
    print(f"[1] تم إرسال العرض الأولي المشفر عبر الشبكة:")
    print(f"    - معرف الجلسة   : {session_id}")
    print(f"    - استجابة الخادم: {resp1}\n")

    # 2. البائع يفك التشفير ويوافق على العرض عبر الشبكة
    seller.sync_sequence(session_id, 2)
    seller_decrypted = seller.decrypt_received_payload(session_id, buyer_env)
    agreed_price = seller_decrypted["price_unit"]
    print(f"[2] البائع فك التشفير ووافق على السعر: {agreed_price} USDC")

    accept_resp = seller.accept(session_id=session_id, agreed_payload=buyer_env, sequence_id=2)
    print(f"    - حالة الجلسة على الخادم: {accept_resp['status']}\n")

    # 3. المشتري يوقّع التزام السعر لمنع التلاعب
    commitment = buyer.create_price_commitment(
        session_id=session_id,
        agreed_amount_usdc=agreed_price,
        seller_agent_id=seller.agent_id
    )

    # 4. البائع يقدم التقرير ويطلب التسوية واقتطاع العمولة
    report = {
        "session_id": str(session_id),
        "item_type": "SECURITY_AUDIT",
        "target": "https://production.core.api",
        "findings": [{"id": "SEC-PROD", "severity": "LOW", "component": "/live/check", "description": "Safe"}],
        "summary": "Live network execution verified.",
        "completed_at": datetime.now(timezone.utc).isoformat()
    }
    deadline = (datetime.now(timezone.utc) + timedelta(hours=24)).timestamp()

    settle_data = seller.submit_and_settle(
        session_id=session_id,
        deliverable_dict=report,
        deadline_timestamp=deadline,
        deal_amount_usdc=agreed_price,
        price_commitment=commitment,
        item_description="Production Security Review"
    )

    print("======================= نتيجة التسوية الحية =======================")
    print(f"  حالة الاعتماد       : {settle_data['status']}")
    print(f"  رقم الفاتورة        : {settle_data['invoice_id']}")
    print(f"  إجمالي الصفقة       : {settle_data['settlement']['total_usdc']} USDC")
    print(f"  أرباحك كمنصة (1.5%) : {settle_data['settlement']['platform_fee_usdc']} USDC")
    print(f"  صافي البائع         : {settle_data['settlement']['seller_net_usdc']} USDC")
    print(f"  كود البلوكتشين      : {settle_data['blockchain_settlement']['calldata'][:24]}...")
    print("===================================================================")

if __name__ == "__main__":
    main()