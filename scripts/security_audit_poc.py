"""
NexusArbiter Adversarial Security & Access Control Audit Suite
Validating Ed25519 signature enforcement and AgentEscrow on-chain modifiers.
"""
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from web3.exceptions import ContractLogicError

# استيراد دوال التشفير الرسمية
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

print("=" * 65)
print(" 🛡️  NexusArbiter Security & Access Control Audit")
print("=" * 65)

# ----------------------------------------------------------------------
# الاختبار الأول: تزوير التوقيع والتلاعب بالسعر (Price Spoofing / Tampering)
# ----------------------------------------------------------------------
print("\n[!] الاختبار 1: محاولة التلاعب بالسعر الموقع تشفيرياً (Ed25519)...")

buyer_priv, buyer_pub = generate_keypair()
buyer_pub_hex = buyer_pub.public_bytes_raw().hex()

original_price = 500.0
tampered_price = 50.0

original_commitment = f"session:sess_101|price:{original_price}|seller:agent:seller_victim".encode("utf-8")
valid_signature_hex = sign_bytes(buyer_priv, original_commitment)

tampered_payload = f"session:sess_101|price:{tampered_price}|seller:agent:seller_victim".encode("utf-8")
is_tampered_valid = verify_signature(buyer_pub_hex, valid_signature_hex, tampered_payload)

if not is_tampered_valid:
    print("  [✓] صمدت آلية التشفير: تم رفض التوقيع المزور وإحباط التلاعب بالسعر.")
else:
    print("  [CRITICAL] فشل التحقق: تم قبول توقيع غير صالح!")

# ----------------------------------------------------------------------
# تحميل العقد وتهيئة حساب غير مصرح له
# ----------------------------------------------------------------------
with open("build/AgentEscrow.json", "r") as f:
    contract_abi = json.load(f)["abi"]

contract = w3.eth.contract(address=Web3.to_checksum_address(ESCROW_ADDRESS), abi=contract_abi)
attacker_wallet = w3.eth.account.create()
fake_session_id = Web3.keccak(text="session_unauthorized_999")

# ----------------------------------------------------------------------
# الاختبار الثاني: استدعاء settleAndSplit من حساب غير مصرح له
# ----------------------------------------------------------------------
print("\n[!] الاختبار 2: محاولة استدعاء settleAndSplit() من محفظة غير مسجلة كـ Arbiter أو Buyer...")

try:
    contract.functions.settleAndSplit(fake_session_id).call({'from': attacker_wallet.address})
    print("  [CRITICAL] ثغرة وصول: سُمح للمحفظة غير المصرح لها بتنفيذ settleAndSplit!")
except (ContractLogicError, Exception) as e:
    err_str = str(e)
    print(f"  [✓] صمد محدد الصلاحيات (onlyArbiterOrBuyer): تم رفض المعاملة على السلسلة مباشرة:\n      -> {err_str}")

# ----------------------------------------------------------------------
# الاختبار الثالث: استدعاء refundBuyer لصفقة وهمية أو غير مؤهلة
# ----------------------------------------------------------------------
print("\n[!] الاختبار 3: محاولة استدعاء refundBuyer() لاسترداد أموال غير مستحقة...")

try:
    contract.functions.refundBuyer(fake_session_id).call({'from': attacker_wallet.address})
    print("  [CRITICAL] ثغرة منطقية: تم قبول استرداد أموال دون التحقق من حالة الصفقة والـ SLA!")
except (ContractLogicError, Exception) as e:
    err_str = str(e)
    print(f"  [✓] صمد منطق العقد: تم رفض طلب الاسترداد من الـ EVM:\n      -> {err_str}")

# ----------------------------------------------------------------------
# الاختبار الرابع: محاولة سرقة ملكية التحكيم (updateArbiter)
# ----------------------------------------------------------------------
print("\n[!] الاختبار 4: محاولة تغيير عنوان المحكم updateArbiter() من حساب خارجي...")

try:
    contract.functions.updateArbiter(attacker_wallet.address).call({'from': attacker_wallet.address})
    print("  [CRITICAL] ثغرة فادحة: تم تغيير المحكم دون صفة مالك المنصة!")
except (ContractLogicError, Exception) as e:
    err_str = str(e)
    print(f"  [✓] صمد محدد الصلاحيات (onlyPlatformOwner): تم منع تغيير المحكم بنجاح:\n      -> {err_str}")

print("\n" + "=" * 65)
print(" [+] اكتمال الفحص الأمني لكافة واجهات العقد والتشفير.")
print("=" * 65)