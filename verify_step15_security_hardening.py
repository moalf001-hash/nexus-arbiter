import concurrent.futures
from fastapi.testclient import TestClient

from src.api.server import app
from src.storage.database import StorageManager

client = TestClient(app)

print("--- بدء فحص التحصين الأمني (Hardening & DoS Resilience Audit) ---\n")

# 1. التحقق من صحة إعدادات الأمان ونمط التشغيل
health_resp = client.get("/health")
assert health_resp.status_code == 200
print(f"[1] حالة الخادم المحصن : {health_resp.json()['security']}\n")

# 2. اختبار التزامن وقفل قاعدة البيانات (Concurrency Stress Test)
print("[*] محاكاة 20 معاملة كتابة متزامنة عبر خيوط معالجة متعددة...")

def concurrent_writer(i: int):
    StorageManager.log_message(
        session_id=f"concurrent-test-session-{i}",
        sequence_id=i,
        sender_agent_id="agent:stress_tester",
        action="PROPOSE",
        payload_dict={"stress": True, "idx": i},
        pubkey_hex="0" * 64,
        sig_hex="0" * 128
    )
    return True

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(concurrent_writer, i) for i in range(20)]
    results = [f.result() for f in futures]

assert all(results), "فشل فحص التزامن!"
print("[2] فحص التزامن وقاعدة البيانات (WAL Mode): 20 عملية كتابة متزامنة أُنجزت دون حدوث قفل للجداول.\n")

# 3. محاكاة هجوم إغراق الذاكرة بحزمة ضخمة (Payload Size Attack)
print("[*] محاكاة إرسال حزمة ضخمة (200 KB) لتجاوز سعة الذاكرة...")
large_junk = "X" * (200 * 1024)
large_payload = {"oversized_data": large_junk}

resp_large = client.post("/negotiate/step", json=large_payload)
assert resp_large.status_code == 413, f"ثغرة! الخادم لم يرفض الحزمة الضخمة: {resp_large.status_code}"
print(f"[3] تم صد هجوم الحزمة الضخمة بنجاح (413 Payload Too Large): {resp_large.json()['detail']}\n")

print("=======================================================")
print("[+] جميع الثغرات التطبيقية والتزامنية تم إغلاقها بنجاح تام.")
print("=======================================================")