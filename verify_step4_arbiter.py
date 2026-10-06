from datetime import datetime, timezone, timedelta
import json
from uuid import uuid4

from src.arbiter.verification import ArbiterEngine, SecurityAuditDeliverable, VulnerabilityFinding
from src.crypto.signatures import generate_keypair, sign_bytes

print("--- بدء فحص محرك التحكيم الحتمي وإثبات التسليم ---\n")

# إعداد مفاتيح الوكيل البائع
seller_priv, seller_pub = generate_keypair()
seller_pub_hex = seller_pub.public_bytes_raw().hex()
session_id = str(uuid4())

# 1. بناء تقرير تسليم فحص أمني حقيقي ومطابق
deliverable_data = SecurityAuditDeliverable(
    session_id=session_id,
    target="https://api.client-service.com",
    findings=[
        VulnerabilityFinding(
            id="VULN-001",
            severity="HIGH",
            component="/api/v1/transfer",
            description="Missing reentrancy guard in withdrawal handler"
        )
    ],
    summary="تم اكتشاف ثغرة عالية الخطورة وتم توثيق مسار المعالجة."
)

raw_json = json.dumps(deliverable_data.model_dump(mode="json"), separators=(",", ":"))
signature_hex = sign_bytes(seller_priv, raw_json.encode("utf-8"))

# مهلة صالحة لمدة 24 ساعة في المستقبل
future_deadline = (datetime.now(timezone.utc) + timedelta(hours=24)).timestamp()

# فحص الحالة الأولى: تسليم صحيح
res1 = ArbiterEngine.verify_proof_of_delivery(
    raw_deliverable_json=raw_json,
    expected_session_id=session_id,
    seller_pub_key_hex=seller_pub_hex,
    delivery_signature_hex=signature_hex,
    deadline_timestamp=future_deadline
)
print(f"[1] فحص التسليم النظامي: {'ناجح (APPROVED)' if res1.is_valid else 'فاشل'}")
print(f"    - الهاش التشفيري للمخرجات: {res1.deliverable_hash}")
print(f"    - نتيجة المحرك: {res1.reason}\n")

# فحص الحالة الثانية: تأخر عن مهلة الـ SLA
past_deadline = (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()
res2 = ArbiterEngine.verify_proof_of_delivery(
    raw_deliverable_json=raw_json,
    expected_session_id=session_id,
    seller_pub_key_hex=seller_pub_hex,
    delivery_signature_hex=signature_hex,
    deadline_timestamp=past_deadline
)
print(f"[2] فحص تجاوز المهلة الزمنية (SLA Breach): {'تم الرفض بنجاح' if not res2.is_valid else 'فشل'}")
print(f"    - سبب الرفض: {res2.reason}\n")

# فحص الحالة الثالثة: محاولة التلاعب بالتقرير بعد التوقيع
tampered_json = raw_json.replace("HIGH", "LOW")
res3 = ArbiterEngine.verify_proof_of_delivery(
    raw_deliverable_json=tampered_json,
    expected_session_id=session_id,
    seller_pub_key_hex=seller_pub_hex,
    delivery_signature_hex=signature_hex,
    deadline_timestamp=future_deadline
)
print(f"[3] فحص كشف تزوير التقرير: {'تم كشف التعديل ورفض الاستلام' if not res3.is_valid else 'فشل'}")
print(f"    - سبب الرفض: {res3.reason}")