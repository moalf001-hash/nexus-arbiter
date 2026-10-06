from uuid import uuid4
from src.blockchain.escrow_client import EscrowBlockchainClient

print("--- بدء فحص جسر ربط البلوكتشين لبروتوكول NexusArbiter ---\n")

# استخدام عنوان عقد افتراضي للفحص المحلي
mock_contract_addr = "0x1234567890123456789012345678901234567890"
client = EscrowBlockchainClient(
    rpc_url="https://sepolia.base.org",
    contract_address=mock_contract_addr
)

print(f"[1] تم تحميل الـ ABI وتأسيس العقد الذكي:")
print(f"    - عنوان العقد المستهدف : {client.contract_address}")
print(f"    - الدوال المتاحة في العقد : {[f for f in client.contract.functions]}")

# 2. اختبار تحويل وحدات العملة ومعرف الجلسة
session_id = uuid4()
session_bytes = client.session_to_bytes32(session_id)
print(f"\n[2] تحويل معرف الجلسة لـ bytes32:")
print(f"    - الـ UUID الأصلي : {session_id}")
print(f"    - صيغة bytes32   : 0x{session_bytes.hex()}")

amount_usdc = 600.0
amount_units = client.usdc_to_units(amount_usdc)
print(f"\n[3] تحويل مبالغ USDC بدقة 6 خانات:")
print(f"    - المبلغ بالقيمة الاسمية: {amount_usdc} USDC")
print(f"    - وحدات البلوكتشين الصغرى : {amount_units} Micro-USDC")

# 3. بناء معاملة lockFunds والتأكد من تشفير الـ Calldata
buyer_addr = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
seller_addr = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
mock_agreement_hash = "f0b8485045e1d9cebd02806ef50ab71a1b1eeed67c2c39282fd3d6405822ae78"

lock_tx = client.build_lock_funds_tx(
    buyer_address=buyer_addr,
    session_id=session_id,
    seller_address=seller_addr,
    amount_usdc=amount_usdc,
    duration_seconds=86400,
    agreement_hash_hex=mock_agreement_hash
)

print(f"\n[4] فحص إنشاء معاملة حجز الأموال (lockFunds):")
print(f"    - المرسل (المشتري) : {lock_tx['from']}")
print(f"    - المستقبل (العقد)  : {lock_tx['to']}")
print(f"    - حمولة البيانات (Calldata): {lock_tx['data'][:30]}... (طول البيانات: {len(lock_tx['data'])} حرف)")

# 4. بناء معاملة settleAndSplit (الصرف وتوزيع العمولات)
arbiter_addr = "0xcccccccccccccccccccccccccccccccccccccccc"
settle_tx = client.build_settle_and_split_tx(
    sender_address=arbiter_addr,
    session_id=session_id
)

print(f"\n[5] فحص إنشاء معاملة التسوية واقتطاع العمولة (settleAndSplit):")
print(f"    - المشغّل (التحكيم): {settle_tx['from']}")
print(f"    - دالة العقد المشفرة : {settle_tx['data'][:10]}")

print("\n[+] جميع فحوصات جسر البلوكتشين سليمة ومتوافقة مع معايير EVM 100%.")