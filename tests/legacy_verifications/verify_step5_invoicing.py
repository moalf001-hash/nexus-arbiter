from src.invoicing.invoice_generator import InvoiceGenerator

print("--- بدء فحص محرك الفوترة والامتثال الضريبي المشفر ---\n")

# البيانات المستخرجة من جلسة العمل السابقة
session_id = "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"
buyer_id = "agent:buyer_corp"
seller_id = "agent:seller_audit"
item_desc = "Security Audit - Vulnerability Assessment"
deal_amount = 600.0
# البصمة الناتجة عن محرك التحكيم في الخطوة السابقة
deliverable_hash = "f0b8485045e1d9cebd02806ef50ab71a1b1eeed67c2c39282fd3d6405822ae78"

# 1. توليد الفاتورة
invoice = InvoiceGenerator.create_invoice(
    session_id=session_id,
    buyer_id=buyer_id,
    seller_id=seller_id,
    item_description=item_desc,
    amount_usdc=deal_amount,
    deliverable_hash=deliverable_hash
)

inv_hash = invoice.invoice_hash()

print(f"[+] تم إنشاء الفاتورة الضريبية بنجاح:")
print(f"    - رقم الفاتورة        : {invoice.invoice_id}")
print(f"    - المشتري              : {invoice.buyer_id}")
print(f"    - البائع               : {invoice.seller_id}")
print(f"    - القيمة الإجمالية    : {invoice.financials.subtotal_usdc} USDC")
print(f"    - عمولة المنصة (أرباحك): {invoice.financials.platform_fee_amount} USDC ({invoice.financials.platform_fee_percent}%)")
print(f"    - صافي مستحق البائع   : {invoice.financials.seller_net_amount} USDC")
print(f"    - هاش إثبات الإنجاز    : {invoice.deliverable_hash}")
print(f"    - هاش الفاتورة المشفر  : {inv_hash}\n")

# 2. فحص الحصانة ضد التلاعب (Immutability Test)
# محاكاة محاولة تلاعب بقيمة الفاتورة أو تخفيض العمولة بعد إنشائها
tampered_invoice = invoice.model_copy(deep=True)
tampered_invoice.financials.platform_fee_amount = 0.0  # محاولة شطب عمولتك

tampered_hash = tampered_invoice.invoice_hash()

print("[*] فحص كشف التلاعب بالفاتورة:")
if inv_hash != tampered_hash:
    print("    [+] نجاح الحماية: أي تعديل في أي رقم يغير هاش الفاتورة فوراً ويجعلها باطلة محاسبياً.")
    print(f"    - الهاش الأصلي : {inv_hash}")
    print(f"    - الهاش المزور : {tampered_hash}")
else:
    print("    [-] فشل: لم يتم كشف التلاعب!")