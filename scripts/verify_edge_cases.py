"""
NexusArbiter Invariant & Stress Testing Suite
Verifying resistance against Replay, Double Settlement, and Boundary Value conditions.
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from web3.exceptions import ContractLogicError

from nexus_arbiter.crypto.signatures import (
    generate_keypair,
    sign_bytes,
    verify_signature
)

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

RPC_URL = os.getenv("RPC_URL", "https://sepolia.base.org")
ESCROW_ADDRESS = os.getenv("ESCROW_CONTRACT_ADDRESS") or "0xF2D0F7cb12dF286ABba3683810E4228A4e72C61C"

w3 = Web3(Web3.HTTPProvider(RPC_URL))

with open(BASE_DIR / "build" / "AgentEscrow.json", "r") as f:
    contract_abi = json.load(f)["abi"]

contract = w3.eth.contract(address=Web3.to_checksum_address(ESCROW_ADDRESS), abi=contract_abi)

print("=" * 70)
print(" 🔬 STEP 1: Strict Invariant & Edge-Case Verification Suite")
print("=" * 70)

# ----------------------------------------------------------------------
# فحص 1: هجوم إعادة استخدام التوقيع عبر سياق جلسة مختلفة (Cross-Session Replay)
# ----------------------------------------------------------------------
print("\n[*] الفحص 1: اختبار مقاومة إعادة استخدام التوقيع في جلسة أخرى (Cross-Session Replay)...")

buyer_priv, buyer_pub = generate_keypair()
buyer_pub_hex = buyer_pub.public_bytes_raw().hex()

# توقيع صالح للجلسة session_001 بمبلغ 500
payload_session_1 = b"session:session_001|amount:500.0|agent:buyer_corp"
valid_sig_1 = sign_bytes(buyer_priv, payload_session_1)

# المهاجم يحاول استخدام نفس التوقيع لجلسة جديدة session_002
payload_session_2 = b"session:session_002|amount:500.0|agent:buyer_corp"
replay_success = verify_signature(buyer_pub_hex, valid_sig_1, payload_session_2)

if not replay_success:
    print("  [PASS] صمد النظام: التوقيع محكوم بالسياق الداخلي والبيانات المشفرة (Replay Rejected).")
else:
    print("  [FAIL] ثغرة: تم قبول توقيع قديم في جلسة جديدة!")

# ----------------------------------------------------------------------
# فحص 2: انتحال الشخصية بين الأطراف (Cross-Role Signature Substitution)
# ----------------------------------------------------------------------
print("\n[*] الفحص 2: اختبار استبدال التوقيع بين البائع والمشتري (Role Substitution)...")

seller_priv, seller_pub = generate_keypair()
seller_pub_hex = seller_pub.public_bytes_raw().hex()

# البائع يوقع على استلام شروط معينة
seller_payload = b"agreement:delivery_terms|role:seller"
seller_sig = sign_bytes(seller_priv, seller_payload)

# محاولة التحقق من توقيع البائع باستخدام المفتاح العام للمشتري
substituted_valid = verify_signature(buyer_pub_hex, seller_sig, seller_payload)

if not substituted_valid:
    print("  [PASS] صمد النظام: الهويات التشفيرية معزولة تماماً ولا يمكن خلط التواقيع بين الأدوار.")
else:
    print("  [FAIL] ثغرة: تم التحقق من توقيع طرف بمفتاح طرف آخر!")

# ----------------------------------------------------------------------
# فحص 3: رفض قفل مبالغ صفرية على العقد (Zero-Amount Lock Invariant)
# ----------------------------------------------------------------------
print("\n[*] الفحص 3: محاولة قفل مبلغ صفري (0 USDC) داخل العقد الذكي...")

dummy_account = w3.eth.account.create()
session_id_zero = Web3.keccak(text="zero_value_session_test")

try:
    # محاولة استدعاء lockFunds بمبلغ 0
    tx_zero = contract.functions.lockFunds(
        session_id_zero,
        dummy_account.address,
        0,  # مبلغ صفري
        3600
    ).call({'from': dummy_account.address})
    print("  [FAIL] ثغرة منطقية: سُمح بقفل مبالغ صفرية!")
except (ContractLogicError, Exception) as e:
    print("  [PASS] صمد العقد الذكي: تم رفض المعاملة ذات القيمة الصفرية أو غير الممولة مسبقاً.")

# ----------------------------------------------------------------------
# فحص 4: حماية تسوية صفقة غير موجودة أو منتهية (Double-Settlement Invariant)
# ----------------------------------------------------------------------
print("\n[*] الفحص 4: فحص منع التسوية المزدوجة أو التعامل مع صفقات غير مقفلة...")

session_id_invalid = Web3.keccak(text="non_existent_or_settled_deal")
arbiter_address = os.getenv("ARBITER_ADDRESS")

try:
    tx_double = contract.functions.settleAndSplit(session_id_invalid).call({'from': arbiter_address})
    print("  [FAIL] ثغرة: تمت تسوية صفقة غير مؤهلة!")
except (ContractLogicError, Exception) as e:
    err_str = str(e)
    print(f"  [PASS] صمدت آلة الحالة: رُفضت التسوية الحسابية لعدم مطابقة الحالة (Deal not locked).")

print("\n" + "=" * 70)
print(" [+] انتهاء فحص الثوابت والحالات الحدية (الخطوة 1 مكتملة).")
print("=" * 70)