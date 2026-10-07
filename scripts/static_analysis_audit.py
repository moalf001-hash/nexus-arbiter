"""
NexusArbiter Static Analysis & Pattern Audit
Automated review of AgentEscrow.sol against industry security standards.
"""
from pathlib import Path
import re

BASE_DIR = Path(__file__).resolve().parent.parent
CONTRACT_PATH = BASE_DIR / "contracts" / "AgentEscrow.sol"

print("=" * 70)
print(" 🔍 STEP 2: Smart Contract Static Analysis & Security Review")
print("=" * 70)

if not CONTRACT_PATH.exists():
    print(f"[-] خطأ: لم يتم العثور على العقد في {CONTRACT_PATH}")
    exit(1)

code = CONTRACT_PATH.read_text(encoding="utf-8")

# 1. فحص إصدار المترجم
solc_match = re.search(r"pragma solidity\s+([^;]+);", code)
version = solc_match.group(1) if solc_match else "Unknown"
print(f"\n[*] 1. فحص إصدار Solidity: {version}")
if "^0.8" in version or ">=0.8" in version:
    print("  [PASS] الإصدار 0.8+ مفعّل (حماية مدمجة ضد Integer Overflow / Underflow).")
else:
    print("  [WARN] يجب استخدام الإصدار 0.8+ لتفادي أخطاء الحسابات.")

# 2. فحص نمط Checks-Effects-Interactions في settleAndSplit
print("\n[*] 2. فحص نمط Checks-Effects-Interactions (منع Reentrancy)...")
settle_func = re.search(r"function settleAndSplit\b.*?\n\s*}", code, re.DOTALL)
if settle_func:
    func_body = settle_func.group(0)
    # التحقق من أن تغيير الحالة يسبق التحويل المالي
    status_update_idx = func_body.find("DealStatus.Settled")
    transfer_idx = func_body.find("transfer(")
    if status_update_idx != -1 and transfer_idx != -1 and status_update_idx < transfer_idx:
        print("  [PASS] النمط سليم: يتم تحديث حالة الصفقة داخلياً قبل استدعاء التحويل الخارجي.")
    else:
        print("  [WARN] قد يكون هناك خرق لنمط CEI؛ تأكد من تحديث الحالة قبل استدعاء transfer.")
else:
    print("  [INFO] لم يتم استخراج الدالة بشكل كامل للتحليل.")

# 3. فحص محددات الوصول الصارمة
print("\n[*] 3. تدقيق محددات الوصول (Access Control Modifiers)...")
critical_funcs = {
    "updateArbiter": "onlyPlatformOwner",
    "settleAndSplit": "onlyArbiterOrBuyer"
}
for func_name, expected_mod in critical_funcs.items():
    if re.search(rf"function {func_name}\b.*?{expected_mod}", code):
        print(f"  [PASS] الدالة `{func_name}` محمية بشكل صحيح بالمحدد `{expected_mod}`.")
    else:
        print(f"  [FAIL] الدالة `{func_name}` غير مقيدة بالمحدد المتوقع `{expected_mod}`!")

# 4. فحص التحقق من العناوين الصفرية (Zero-Address Validation)
print("\n[*] 4. فحص التحقق من العناوين الصفرية (Zero-Address Checks)...")
if "address(0)" in code or "Invalid address" in code:
    print("  [PASS] العقد يحتوي على شروط صريحة لمنع تمرير العناوين الصفرية address(0).")
else:
    print("  [WARN] يُنصح بإضافة شروط require(account != address(0)) لمنع ضياع الأموال.")

print("\n" + "=" * 70)
print(" [+] اكتمال تقرير الفحص الساكن (الخطوة 2 جاهزة).")
print("=" * 70)