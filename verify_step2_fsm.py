from uuid import uuid4
from src.core.schemas import NegotiationPayload, SignedNegotiationMessage, ActionType, ItemType, CurrencyType
from src.core.fsm import NegotiationSession, SessionStatus, FSMException
from src.crypto.signatures import generate_keypair, sign_bytes

# إعداد وكيلين: مشتري وبائع
buyer_priv, buyer_pub = generate_keypair()
seller_priv, seller_pub = generate_keypair()

buyer_id = "agent:buyer_corp"
seller_id = "agent:seller_audit"

buyer_pub_hex = buyer_pub.public_bytes_raw().hex()
seller_pub_hex = seller_pub.public_bytes_raw().hex()

session_id = uuid4()
session = NegotiationSession(session_id=session_id)

def create_msg(agent_id, priv_key, pub_hex, seq, action, payload):
    stub = SignedNegotiationMessage(
        session_id=session_id,
        sequence_id=seq,
        sender_agent_id=agent_id,
        action=action,
        payload=payload,
        public_key_hex=pub_hex,
        signature_hex="0" * 128
    )
    sig = sign_bytes(priv_key, stub.message_digest_bytes())
    return stub.model_copy(update={"signature_hex": sig})

# الخطوة 1: المشتري يقدم عرضا أوليا (PROPOSE) بـ 500 دولار
p1 = NegotiationPayload(item_type=ItemType.SECURITY_AUDIT, price_unit=500.0, quantity=1, sla_hours=24)
msg1 = create_msg(buyer_id, buyer_priv, buyer_pub_hex, 1, ActionType.PROPOSE, p1)
session.apply_transition(msg1)
print(f"[1] بدء الجلسة: الحالة = {session.status.value}")

# الخطوة 2: اختبار مخالفة الأدوار (المشتري يحاول إرسال عرض ثان فورا)
try:
    bad_msg = create_msg(buyer_id, buyer_priv, buyer_pub_hex, 2, ActionType.COUNTER, p1)
    session.apply_transition(bad_msg)
    print("[-] فشل: تم تمرير رسالة مخالفة للأدوار!")
except FSMException as e:
    print(f"[2] نجاح صد مخالفة الأدوار: تم رفض الإرسال المتتالي ({e})")

# الخطوة 3: البائع يقدم عرضا مقابلا (COUNTER) بـ 600 دولار
p2 = NegotiationPayload(item_type=ItemType.SECURITY_AUDIT, price_unit=600.0, quantity=1, sla_hours=24)
msg2 = create_msg(seller_id, seller_priv, seller_pub_hex, 2, ActionType.COUNTER, p2)
session.apply_transition(msg2)
print(f"[3] رد البائع بعرض مقابل: الحالة = {session.status.value}")

# الخطوة 4: المشتري يوافق على عرض الـ 600 دولار (ACCEPT)
msg3 = create_msg(buyer_id, buyer_priv, buyer_pub_hex, 3, ActionType.ACCEPT, p2)
session.apply_transition(msg3)
print(f"[4] إتمام الاتفاق: الحالة = {session.status.value}")
print(f"    السعر النهائي المتفق عليه والمقفل: {session.agreed_payload.price_unit} USDC")

# الخطوة 5: اختبار محاولة تعديل السعر بعد التوقيع
try:
    p_exploit = NegotiationPayload(item_type=ItemType.SECURITY_AUDIT, price_unit=100.0, quantity=1, sla_hours=24)
    msg4 = create_msg(seller_id, seller_priv, seller_pub_hex, 4, ActionType.COUNTER, p_exploit)
    session.apply_transition(msg4)
    print("[-] فشل: سمح بتعديل عقد منتهي!")
except FSMException:
    print("[5] نجاح قفل العقد: تم حظر أي تعديل بعد حالة ACCEPTED")
