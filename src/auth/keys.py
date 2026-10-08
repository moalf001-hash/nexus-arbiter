import hashlib
import hmac
import secrets
from typing import Tuple

KEY_PREFIX = "nx_live_"

def generate_api_key() -> Tuple[str, str, str]:
    """
    يولد مفتاح API جديد بصيغة آمنة تشفيرياً.
    
    العائد:
        - raw_key: المفتاح الكامل الصريح (يُعرض للعميل لمرة واحدة فقط).
        - key_hash: الهاش بصيغة SHA-256 (يُخزن في قاعدة البيانات).
        - prefix: أول 16 محرفاً لتسهيل استعراض المفتاح والتعرف عليه في الواجهة.
    """
    # توليد 32 بايت من العشوائية المشفرة
    random_bytes = secrets.token_urlsafe(32)
    raw_key = f"{KEY_PREFIX}{random_bytes}"
    
    # استخراج البادئة للتعريف
    prefix = raw_key[:16]
    
    # حساب التجزئة بصيغة SHA-256
    key_hash = hash_api_key(raw_key)
    
    return raw_key, key_hash, prefix

def hash_api_key(key: str) -> str:
    """
    تجزئة المفتاح باستخدام SHA-256.
    """
    return hashlib.sha256(key.encode("utf-8")).hexdigest()

def verify_api_key(provided_key: str, stored_hash: str) -> bool:
    """
    التحقق من صحة المفتاح المقدم بمقارنته مع الهاش المخزن.
    يستخدم compare_digest لمنع هجمات التوقيت (Timing Attacks).
    """
    if not provided_key.startswith(KEY_PREFIX):
        return False
    
    computed_hash = hash_api_key(provided_key)
    return hmac.compare_digest(computed_hash, stored_hash)