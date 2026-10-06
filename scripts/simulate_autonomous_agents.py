import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import time
import json
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from src.api.server import app
from src.core.schemas import ItemType
from src.sdk.agent_client import NexusAgentClient

client = TestClient(app)

class AutonomousBuyerAgent:
    """وكيل مشتري يتخذ قرارات المساومة ذاتياً."""
    def __init__(self, agent_id: str, max_budget_usdc: float, initial_offer_usdc: float):
        self.sdk = NexusAgentClient(agent_id=agent_id)
        self.max_budget = max_budget_usdc
        self.current_offer = initial_offer_usdc
        self.step_increment = 100.0  # مقدار رفع العرض في كل جولة

    def evaluate_counter_offer(self, seller_price: float) -> tuple[str, float]:
        """تقييم عرض البائع: إما القبول أو الرفع أو الرفض التام."""
        if seller_price <= self.max_budget:
            # إذا كان السعر ضمن الميزانية، يقبل الصفقة
            return "ACCEPT", seller_price
        
        # محاولة تقديم عرض جديد أعلى ما لم يتجاوز الميزانية
        new_offer = self.current_offer + self.step_increment
        if new_offer <= self.max_budget:
            self.current_offer = new_offer
            return "COUNTER", new_offer
        
        return "REJECT", 0.0

class AutonomousSellerAgent:
    """وكيل بائع يحدد استراتيجية التسعير وهامش الربح ذاتياً."""
    def __init__(self, agent_id: str, reserve_price_usdc: float, initial_price_usdc: float):
        self.sdk = NexusAgentClient(agent_id=agent_id)
        self.reserve_price = reserve_price_usdc  # الحد الأدنى المقبول
        self.current_asking_price = initial_price_usdc
        self.step_decrement = 150.0  # مقدار خفض السعر لتقديم تنازل

    def evaluate_bid(self, buyer_price: float) -> tuple[str, float]:
        """تقييم عرض المشتري: القبول أو تقديم سعر مخفض أو الرفض."""
        if buyer_price >= self.current_asking_price or buyer_price >= self.reserve_price:
            return "ACCEPT", buyer_price
        
        # تقديم سعر مقابل مخفض لا يقل عن الحد الأدنى (Reserve Price)
        new_price = max(self.current_asking_price - self.step_decrement, self.reserve_price)
        if new_price <= self.current_asking_price:
            self.current_asking_price = new_price
            return "COUNTER", new_price
            
        return "REJECT", 0.0

def run_autonomous_negotiation_loop():
    print("=================================================================")
    print("   بدء محاكاة بروتوكول NexusArbiter للتفاوض المستقل بين AI Agents   ")
    print("=================================================================\n")

    # 1. إعداد الوكلاء بمعاييرهم الاقتصادية الخاصة
    buyer = AutonomousBuyerAgent(
        agent_id="agent:enterprise_buyer",
        max_budget_usdc=1800.0,
        initial_offer_usdc=1300.0
    )
    seller = AutonomousSellerAgent(
        agent_id="agent:secops_provider",
        reserve_price_usdc=1500.0,
        initial_price_usdc=2100.0
    )

    print(f"[*] وكيل المشتري: {buyer.sdk.agent_id} | الميزانية القصوى: {buyer.max_budget} USDC")
    print(f"[*] وكيل البائع : {seller.sdk.agent_id}  | الحد الأدنى للقبول: {seller.reserve_price} USDC\n")

    # 2. الجولة الأولى: المشتري يبدأ بعرض مشفر أولي
    session_id, last_envelope, _ = buyer.sdk.propose_encrypted(
        peer_enc_pubkey_hex=seller.sdk.enc_public_key_hex,
        item_type=ItemType.SECURITY_AUDIT,
        price_unit=buyer.current_offer,
        sla_hours=48,
        client=client
    )
    print(f"[الجولة 1] المشتري يبدأ بعرض سري مشفر: {buyer.current_offer} USDC")

    seq = 2
    round_num = 1
    agreed_final_price = None

    # 3. حلقة التفاوض الذاتي (Autonomous Bargaining Loop)
    while round_num <= 10:
        round_num += 1
        
        # --- خطوة البائع ---
        seller.sdk.sync_sequence(session_id, seq)
        decrypted_buyer_offer = seller.sdk.decrypt_received_payload(session_id, last_envelope)
        bid = decrypted_buyer_offer["price_unit"]
        
        seller_decision, seller_val = seller.evaluate_bid(bid)
        
        if seller_decision == "ACCEPT":
            print(f"[الجولة {round_num}] البائع قرر ذاتياً قبول عرض المشتري: {bid} USDC!")
            seller.sdk.accept(session_id, last_envelope, sequence_id=seq, client=client)
            agreed_final_price = bid
            break
        elif seller_decision == "COUNTER":
            print(f"[الجولة {round_num}] البائع رفض {bid} USDC ورد بعرض مقابل مشفر: {seller_val} USDC")
            last_envelope, _ = seller.sdk.counter_encrypted(
                peer_enc_pubkey_hex=buyer.sdk.enc_public_key_hex,
                session_id=session_id,
                item_type=ItemType.SECURITY_AUDIT,
                price_unit=seller_val,
                sla_hours=48,
                sequence_id=seq,
                client=client
            )
            seq += 1
        else:
            print(f"[!] البائع رفض إكمال الصفقة.")
            break

        # --- خطوة المشتري ---
        round_num += 1
        buyer.sdk.sync_sequence(session_id, seq)
        decrypted_seller_offer = buyer.sdk.decrypt_received_payload(session_id, last_envelope)
        asking = decrypted_seller_offer["price_unit"]

        buyer_decision, buyer_val = buyer.evaluate_counter_offer(asking)

        if buyer_decision == "ACCEPT":
            print(f"[الجولة {round_num}] المشتري قرر ذاتياً قبول عرض البائع: {asking} USDC!")
            buyer.sdk.accept(session_id, last_envelope, sequence_id=seq, client=client)
            agreed_final_price = asking
            break
        elif buyer_decision == "COUNTER":
            print(f"[الجولة {round_num}] المشتري رفع عرضه السري إلى: {buyer_val} USDC")
            last_envelope, _ = buyer.sdk.counter_encrypted(
                peer_enc_pubkey_hex=seller.sdk.enc_public_key_hex,
                session_id=session_id,
                item_type=ItemType.SECURITY_AUDIT,
                price_unit=buyer_val,
                sla_hours=48,
                sequence_id=seq,
                client=client
            )
            seq += 1
        else:
            print(f"[!] المشتري رفض الاستمرار في التفاوض لتجاوز الميزانية.")
            break

    assert agreed_final_price is not None, "فشلت المحاكاة في الوصول لاتفاق ذاتي."

    print(f"\n[+] تم إبرام العقد بنجاح على السعر العادل: {agreed_final_price} USDC")
    print(f"[+] حالة الجلسة المشفرة: تم إغلاق وتثبيت العقد بحالة (ACCEPTED)\n")

    # 4. التنفيذ الآلي: البائع يسلم تقرير الفحص ويطلب الصرف المالي
    print("[*] وكيل البائع ينفذ الفحص الأمني ويقدم إثبات التسليم المشفر (PoD)...")
    audit_report = {
        "session_id": str(session_id),
        "item_type": "SECURITY_AUDIT",
        "target": "https://vault.autonomous-agents.network",
        "findings": [
            {"id": "AUTO-01", "severity": "MEDIUM", "component": "/escrow/worker", "description": "Verified thread-safety"}
        ],
        "summary": "Autonomous execution and cryptographic compliance validated.",
        "completed_at": datetime.now(timezone.utc).isoformat()
    }

    deadline = (datetime.now(timezone.utc) + timedelta(hours=48)).timestamp()
    
    price_commitment = buyer.sdk.create_price_commitment(
        session_id=session_id,
        agreed_amount_usdc=agreed_final_price,
        seller_agent_id=getattr(seller, "agent_id", seller.sdk.agent_id)
    )

    settle_result = seller.sdk.submit_and_settle(
        session_id=session_id,
        price_commitment=price_commitment,
        deliverable_dict=audit_report,
        deadline_timestamp=deadline,
        deal_amount_usdc=agreed_final_price,
        item_description="Automated Penetration Testing by SecOps Agent",
        client=client
    )

    print("\n======================= تقرير التسوية النهائي =======================")
    print(f"  معرّف الجلسة          : {session_id}")
    print(f"  حالة التحكيم          : {settle_result['status']}")
    print(f"  رقم الفاتورة المحفوظة : {settle_result['invoice_id']}")
    print(f"  قيمة الصفقة الإجمالية : {settle_result['settlement']['total_usdc']} USDC")
    print(f"  أرباحك كمنصة (1.5%)   : {settle_result['settlement']['platform_fee_usdc']} USDC (جاهزة للسحب)")
    print(f"  صافي أرباح البائع     : {settle_result['settlement']['seller_net_usdc']} USDC")
    print(f"  كود تنفيذ البلوكتشين  : {settle_result['blockchain_settlement']['calldata'][:24]}...")
    print("=====================================================================")
    print("[+] انتهت المحاكاة الذاتية بنجاح تام: تم التفاوض والتعاقد والتسوية آلياً بالكامل!")

if __name__ == "__main__":
    run_autonomous_negotiation_loop()