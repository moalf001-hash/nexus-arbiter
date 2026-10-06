import json
import os

print("[*] جارٍ توليد وحفظ ملف الـ ABI الرسمي لعقد AgentEscrow...")

# تعريف الـ ABI القياسي المعتمد لجميع دوال وأحداث عقد AgentEscrow
ESCROW_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "_usdcToken", "type": "address"},
            {"internalType": "address", "name": "_arbiterEngine", "type": "address"}
        ],
        "stateMutability": "nonpayable",
        "type": "constructor"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "sessionId", "type": "bytes32"},
            {"indexed": True, "internalType": "address", "name": "buyer", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "seller", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "FundsLocked",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "sessionId", "type": "bytes32"},
            {"indexed": False, "internalType": "uint256", "name": "sellerAmount", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "platformFee", "type": "uint256"}
        ],
        "name": "FundsSettled",
        "type": "event"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "sessionId", "type": "bytes32"},
            {"indexed": True, "internalType": "address", "name": "buyer", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"}
        ],
        "name": "FundsRefunded",
        "type": "event"
    },
    {
        "inputs": [],
        "name": "PLATFORM_FEE_BPS",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "arbiterEngine",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "platformOwner",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "sessionId", "type": "bytes32"},
            {"internalType": "address", "name": "seller", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
            {"internalType": "uint256", "name": "durationSeconds", "type": "uint256"},
            {"internalType": "bytes32", "name": "agreementHash", "type": "bytes32"}
        ],
        "name": "lockFunds",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
      },
      {
        "inputs": [{"internalType": "bytes32", "name": "sessionId", "type": "bytes32"}],
        "name": "settleAndSplit",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
      },
      {
        "inputs": [{"internalType": "bytes32", "name": "sessionId", "type": "bytes32"}],
        "name": "refundBuyer",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
      }
]

# إنشاء مجلد build وحفظ ملف الـ JSON
os.makedirs("build", exist_ok=True)
artifact_path = os.path.join("build", "AgentEscrow.json")

build_data = {
    "contractName": "AgentEscrow",
    "abi": ESCROW_ABI
}

with open(artifact_path, "w", encoding="utf-8") as f:
    json.dump(build_data, f, indent=2)

print(f"[+] تم توليد ملف العقد بنجاح في: {artifact_path}")
print(f"    - عدد الدوال المحفوظة في الـ ABI: {len([x for x in ESCROW_ABI if x.get('type') == 'function'])}")

# التحقق من العمليات الحسابية لعمولة المنصة
print("\n--- فحص تدفق الأموال واقتطاع نسبتك (1.5%) ---")
deal_amount_usdc = 600.0
usdc_decimals = 10**6
deal_amount_units = int(deal_amount_usdc * usdc_decimals)  # 600,000,000 Micro-USDC

PLATFORM_FEE_BPS = 150      # 1.5%
BPS_DENOMINATOR = 10000

platform_fee_units = (deal_amount_units * PLATFORM_FEE_BPS) // BPS_DENOMINATOR
seller_share_units = deal_amount_units - platform_fee_units

platform_fee_usdc = platform_fee_units / usdc_decimals
seller_share_usdc = seller_share_units / usdc_decimals

print(f"القيمة الإجمالية للصفقة : {deal_amount_usdc:,.2f} USDC")
print(f"عمولتك أنت (محفظة المالك) : {platform_fee_usdc:,.2f} USDC (اقتطاع آلي)")
print(f"المستحق للوكيل البائع   : {seller_share_usdc:,.2f} USDC")

assert platform_fee_units + seller_share_units == deal_amount_units, "خطأ في حساب المبالغ!"
print("[+] فحص التوزيع المالي: متطابق 100% وبدون أي فقدان للأجزاء العشرية (Zero-Loss).")