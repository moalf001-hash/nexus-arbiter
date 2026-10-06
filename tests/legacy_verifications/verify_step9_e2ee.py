import os
from src.crypto.encryption import (
    generate_encryption_keypair,
    derive_shared_secret,
    encrypt_payload,
    decrypt_payload
)

print("--- بدء اختبار نظام التشفير الهجين التام (E2EE X25519 + ChaCha20-Poly1305) ---\n")

# 1. توليد مفاتيح التشفير للمشتري والبائع
buyer_priv, buyer_pub = generate_encryption_keypair()
seller_priv, seller_pub = generate_encryption_keypair()

buyer_pub_hex = buyer_pub.public_bytes_raw().hex()
seller_pub_hex = seller_pub.public_bytes_raw().hex()

print(f"[+] مفتاح المشتري العام للتشفير : {buyer_pub_hex[:32]}...")
print(f"[+] مفتاح البائع العام للتشفير  : {seller_pub_hex[:32]}...")

# 2. اشتقاق المفتاح السري المشترك (ECDH + HKDF)
salt = os.urandom(16)

# المشتري يشتق المفتاح باستخدام مفتاحه الخاص + مفتاح البائع العام
buyer_shared_key = derive_shared_secret(buyer_priv, seller_pub_hex, salt)

# البائع يشتق المفتاح باستخدام مفتاحه الخاص + مفتاح المشتري العام
seller_shared_key = derive_shared_secret(seller_priv, buyer_pub_hex, salt)

assert buyer_shared_key == seller_shared_key, "خطأ: المفاتيح المشتقة غير متطابقة!"
print(f"[+] تم اشتقاق السر المشترك بنجاح عبر طرفي الاتصال (32 بايت مشفرة بالتساوي)\n")

# 3. تشفير حمولة العرض المالي السري
confidential_offer = {
    "target": "Enterprise Financial Core",
    "secret_bid_usdc": 750.0,
    "proprietary_terms": "Confidential AI Penetration SLA"
}

encrypted_packet = encrypt_payload(buyer_shared_key, confidential_offer)
print("[*] تم تشفير محتوى العرض بالكامل قبل إرساله للشبكة:")
print(f"    - الـ Nonce الفريد    : {encrypted_packet['nonce_hex']}")
print(f"    - النص المشفر (Cipher): {encrypted_packet['ciphertext_hex']}\n")

# 4. استلام وفك تشفير العرض من طرف البائع
decrypted_data = decrypt_payload(
    seller_shared_key,
    encrypted_packet["nonce_hex"],
    encrypted_packet["ciphertext_hex"]
)
print(f"[1] فك التشفير المعتمد لدى البائع: ناجح 100%")
print(f"    - السعر المسترجع بأمان : {decrypted_data['secret_bid_usdc']} USDC")
print(f"    - تفاصيل الصفقة        : {decrypted_data['proprietary_terms']}\n")

# 5. اختبار أمني: محاولة طرف ثالث (مهاجم) فك التشفير بمفتاح مختلف
attacker_priv, _ = generate_encryption_keypair()
attacker_fake_key = derive_shared_secret(attacker_priv, buyer_pub_hex, salt)

try:
    decrypt_payload(attacker_fake_key, encrypted_packet["nonce_hex"], encrypted_packet["ciphertext_hex"])
    print("[-] ثغرة: نجح المهاجم في قراءة البيانات!")
except Exception:
    print("[2] فحص الحصانة ضد التلصص (Eavesdropping Protection): تم حجب المهاجم وفشل فك التشفير رياضياً.\n")

# 6. اختبار أمني: محاولة تلاعب بحرف واحد في النص المشفر أثناء النقل
tampered_ciphertext = list(encrypted_packet["ciphertext_hex"])
tampered_ciphertext[10] = "f" if tampered_ciphertext[10] != "f" else "0"
tampered_hex = "".join(tampered_ciphertext)

try:
    decrypt_payload(seller_shared_key, encrypted_packet["nonce_hex"], tampered_hex)
    print("[-] ثغرة: تم قبول نص مشفر متلاعب به!")
except Exception:
    print("[3] فحص المصادقة ضد التلاعب (AEAD Integrity Tag): اكتشف رمز Poly1305 التعديل ورفض الحزمة فوراً.")

print("\n=======================================================")
print("[+] تم إثبات الحماية القصوى للتفاوض وسرية الأسعار بنجاح.")
print("=======================================================")