import os
import sys
import json
import time
import threading
from fastapi.testclient import TestClient
from src.api.server import app
from src.storage.database import StorageManager, init_db
from src.auth.keys import generate_api_key

client = TestClient(app)

passed_tests = 0
total_tests = 0

def assert_test(name: str, condition: bool, details: str = ""):
    global passed_tests, total_tests
    total_tests += 1
    if condition:
        passed_tests += 1
        print(f"  [PASS] {name}")
    else:
        print(f"  [FAIL] {name} -> {details}")

print("================================================================")
print("🛡️ بدء التدقيق الأمني والاختراق الشامل لبروتوكول NexusArbiter")
print("================================================================")

init_db()

# 1. اختبار حجب الحزم الضخمة (DoS Protection)
print("\n[+] 1. فحص حماية حجب الخدمة واستهلاك الموارد (DoS & Oversized Payloads)")
giant_payload = "A" * (130 * 1024)  # 130 KB (الحد الأقصى 128 KB)
res = client.post("/negotiate/step", content=giant_payload, headers={"Content-Type": "application/json"})
assert_test("حظر الحزم التي تتجاوز 128KB برمز 413", res.status_code == 413, f"Got status {res.status_code}")

# 2. اختبار هجمات حقن قواعد البيانات (SQL Injection) في المفتاح
print("\n[+] 2. فحص صمود طبقة المصادقة أمام حقن SQL (SQL Injection)")
sqli_keys = [
    "nx_live_' OR '1'='1",
    "nx_live_admin' --",
    "nx_live_' UNION SELECT 1,2,3,4,5,6 --"
]
for key in sqli_keys:
    res = client.post("/negotiate/step", json={}, headers={"X-Nexus-API-Key": key})
    assert_test(f"فشل الحقن بالمفتاح: {key[:20]}...", res.status_code == 401, f"Got status {res.status_code}")

# 3. اختبار تجاوز الحصص بالتزامن (Concurrency / Quota Bypass)
print("\n[+] 3. فحص هجمات السباق لتجاوز الحصص الشهرية (Concurrency / Quota Bypass)")
t_key, t_hash, t_pref = generate_api_key()
test_tenant_id = f"tenant_race_{int(time.time())}"
StorageManager.create_tenant(test_tenant_id, "Race Condition Corp", "free", monthly_limit=3)
StorageManager.save_api_key(t_hash, t_pref, test_tenant_id)

results = []
def fire_request():
    r = client.post("/negotiate/step", json={}, headers={"X-Nexus-API-Key": t_key})
    results.append(r.status_code)

threads = [threading.Thread(target=fire_request) for _ in range(10)]
for th in threads: th.start()
for th in threads: th.join()

blocked_429_count = results.count(429)
assert_test("الحظر التلقائي للطلبات الزائدة برمز 429 لمنع التجاوز المتزامن", blocked_429_count >= 7, f"Allowed more than quota! 429s: {blocked_429_count}")

# 4. فحص كشف التلاعب بالحزم الموقعة تشفيرياً (Cryptographic Tampering)
print("\n[+] 4. فحص كشف التلاعب بالحزم الموقعة تشفيرياً (Cryptographic Tampering)")
fake_step_data = {
    "session_id": "12345678-1234-5678-1234-567812345678",
    "sequence_id": 1,
    "sender_agent_id": "agent:attacker",
    "action": "PROPOSE",
    "payload": {
        "price_unit": 100.0,
        "quantity": 1,
        "currency": "USDC",
        "item_type": "COMPUTE_RESOURCE",
        "sla_hours": 24
    },
    "public_key_hex": "a" * 64,
    "signature_hex": "b" * 128
}
fresh_key, fresh_hash, fresh_pref = generate_api_key()
StorageManager.create_tenant("tenant_sec_01", "Sec Corp", "pro", monthly_limit=100)
StorageManager.save_api_key(fresh_hash, fresh_pref, "tenant_sec_01")
res = client.post("/negotiate/step", json=fake_step_data, headers={"X-Nexus-API-Key": fresh_key})
assert_test("كشف ورفض التوقيع المزور برمز 401", res.status_code == 401 and "Ed25519" in res.text, f"Got status {res.status_code}: {res.text}")


# 5. فحص حماية مسار التحكيم من Price Spoofing
print("\n[+] 5. فحص منع تزوير الأسعار في التحكيم (Anti-Price Spoofing Guard)")
settle_fake = {
    "session_id": "00000000-0000-0000-0000-000000000001",
    "raw_deliverable_json": "{}",
    "seller_pub_key_hex": "11" * 32,
    "delivery_signature_hex": "22" * 64,
    "deadline_timestamp": time.time() + 3600,
    "deal_amount_usdc": 5000.0
}
res = client.post("/arbiter/settle", json=settle_fake, headers={"X-Nexus-API-Key": fresh_key})
assert_test("رفض تسوية جلسة غير مسجلة أو لم تكتمل برمز 404 أو 400", res.status_code in (400, 404), f"Got status {res.status_code}")

print("\n================================================================")
print(f"📊 نتيجة التدقيق الأمني: نجاح {passed_tests} من أصل {total_tests} اختبارات.")
if passed_tests == total_tests:
    print("🎉 الكود محصن بالكامل ضد الثغرات البرمجية والتلاعب التشفيري!")
print("================================================================")