from uuid import uuid4
from src.core.schemas import NegotiationPayload, SignedNegotiationMessage, ActionType, ItemType, CurrencyType
from src.crypto.signatures import generate_keypair, sign_bytes, verify_signature

# 1. إنشاء مفاتيح الوكيل المشتري
priv_key, pub_key = generate_keypair()
pub_hex = pub_key.public_bytes_raw().hex()
session_id = uuid4()

payload = NegotiationPayload(
    item_type=ItemType.SECURITY_AUDIT,
    price_unit=450.0,
    quantity=1,
    currency=CurrencyType.USDC,
    sla_hours=24
)

# 2. بناء رسالة وتوقيعها
msg_stub = SignedNegotiationMessage(
    session_id=session_id,
    sequence_id=1,
    sender_agent_id="agent:buyer_audit",
    action=ActionType.PROPOSE,
    payload=payload,
    public_key_hex=pub_hex,
    signature_hex="0" * 128
)

data_to_sign = msg_stub.message_digest_bytes()
sig_hex = sign_bytes(priv_key, data_to_sign)

msg = msg_stub.model_copy(update={"signature_hex": sig_hex})

# 3. التحقق من الرسالة الأصلية
is_valid = verify_signature(msg.public_key_hex, msg.signature_hex, msg.message_digest_bytes())
print(f"[1] التحقق من الرسالة الأصلية: {'ناجح (VALID)' if is_valid else 'فاشل'}")

# 4. محاكاة هجوم رجل في المنتصف (MitM): محاولة تعديل السعر إلى 50
tampered_payload = NegotiationPayload(
    item_type=ItemType.SECURITY_AUDIT,
    price_unit=50.0,
    quantity=1,
    currency=CurrencyType.USDC,
    sla_hours=24
)
tampered_msg = msg.model_copy(update={"payload": tampered_payload})

is_tampered_valid = verify_signature(
    tampered_msg.public_key_hex,
    tampered_msg.signature_hex,
    tampered_msg.message_digest_bytes()
)
print(f"[2] محاولة تمرير رسالة معدلة: {'تم كشف الهجوم وحظر الرسالة' if not is_tampered_valid else 'فشلت الحماية'}")