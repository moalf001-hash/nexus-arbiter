import os
import sys
import json
import getpass
from pathlib import Path
from web3 import Web3
from eth_account import Account

def load_env_file():
    """تحميل متغيرات البيئة من ملف .env."""
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip("\"'")

def get_deployer_account() -> Account:
    """فك تشفير المحفظة من الـ Keystore المشفر حصراً وفق معايير الأمان القصوى."""
    keystore_path = os.getenv("DEPLOYER_KEYSTORE_PATH", "secrets/deployer_keystore.json")
    
    if not os.path.exists(keystore_path):
        print(f"[-] خطأ أمني: لم يتم العثور على ملف Keystore في '{keystore_path}'")
        print("    يُمنع استخدام المفاتيح غير المشفرة في بيئة الإنتاج.")
        sys.exit(1)

    print(f"[*] تحميل المحفظة المشفرة: {keystore_path}")
    try:
        with open(keystore_path, "r", encoding="utf-8") as f:
            keystore_data = json.load(f)
        passphrase = getpass.getpass("أدخل كلمة مرور الـ Keystore لفك تشفير المحفظة: ")
        private_key = Account.decrypt(keystore_data, passphrase)
        return Account.from_key(private_key)
    except Exception as e:
        print(f"[-] خطأ: فشل فك تشفير الـ Keystore ({e})")
        sys.exit(1)

def deploy():
    load_env_file()

    rpc_url = os.getenv("RPC_URL", "https://ethereum-sepolia-rpc.publicnode.com")
    usdc_address = os.getenv("USDC_ADDRESS", "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238")
    arbiter_address = os.getenv("ARBITER_ADDRESS")

    # 1. الاتصال بمزود الـ RPC
    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 20}))
    if not w3.is_connected():
        print(f"[-] خطأ: تعذر الاتصال بمزود الـ RPC: {rpc_url}")
        sys.exit(1)

    actual_chain_id = w3.eth.chain_id

    # فك تشفير المحفظة بأمان
    account = get_deployer_account()
    deployer_address = account.address
    arbiter = arbiter_address if arbiter_address and "0x" in arbiter_address else deployer_address

    print("\n=========================================================")
    print("      NexusArbiter On-Chain Deployment Protocol          ")
    print("=========================================================")
    print(f"[*] معرف الشبكة (Chain ID) : {actual_chain_id}")
    print(f"[*] محفظة النشر (Deployer) : {deployer_address}")
    print(f"[*] محرك التحكيم (Arbiter) : {arbiter}")
    print(f"[*] رمز USDC المستهدف       : {usdc_address}")

    # 2. فحص رصيد الغاز
    balance_wei = w3.eth.get_balance(deployer_address)
    balance_eth = w3.from_wei(balance_wei, "ether")
    print(f"[*] رصيد الغاز (ETH)       : {balance_eth:.6f} ETH")

    if balance_wei == 0:
        print(f"\n[-] خطأ: المحفظة {deployer_address} لا تملك رصيد غاز (0 ETH) على هذه الشبكة.")
        sys.exit(1)

    # 3. تحميل ملف البناء المترجم
    artifact_path = Path("build/AgentEscrow.json")
    if not artifact_path.exists():
        print(f"[-] خطأ: ملف البناء غير موجود في {artifact_path}. نفذ scripts.compile_contract أولاً.")
        sys.exit(1)

    with open(artifact_path, "r", encoding="utf-8") as f:
        artifact = json.load(f)

    abi = artifact["abi"]
    bytecode = artifact["bytecode"]

    contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    # 4. بناء معاملة النشر
    nonce = w3.eth.get_transaction_count(deployer_address)
    gas_price = w3.eth.gas_price

    print("[*] جاري بناء معاملة العقد...")
    tx_data = contract.constructor(
        Web3.to_checksum_address(usdc_address),
        Web3.to_checksum_address(arbiter)
    ).build_transaction({
        "from": deployer_address,
        "nonce": nonce,
        "gasPrice": int(gas_price * 1.25),
        "chainId": actual_chain_id
    })

    try:
        estimated_gas = w3.eth.estimate_gas(tx_data)
        tx_data["gas"] = int(estimated_gas * 1.2)
        print(f"[*] تقدير الغاز           : {tx_data['gas']}")
    except Exception as e:
        print(f"[!] تحذير: فشل تقدير الغاز تلقائياً ({e}). استخدام 3,500,000 كحد أقصى.")
        tx_data["gas"] = 3500000

    # 5. التوقيع وبث المعاملة
    print("[*] توقيع المعاملة عبر المفتاح المشفر...")
    signed_tx = w3.eth.account.sign_transaction(tx_data, private_key=account.key)

    raw_tx = getattr(signed_tx, "raw_transaction", None) or getattr(signed_tx, "rawTransaction", None)
    print("[*] بث المعاملة إلى الشبكة...")
    tx_hash = w3.eth.send_raw_transaction(raw_tx)
    tx_hash_hex = tx_hash.hex()

    explorer_base = "https://sepolia.etherscan.io" if actual_chain_id == 11155111 else "https://sepolia.basescan.org"
    print(f"[+] تم البث! هاش المعاملة : {tx_hash_hex}")
    print(f"    رابط المستكشف          : {explorer_base}/tx/{tx_hash_hex}")

    print("[*] بانتظار تأكيد التعدين على البلوكتشين...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

    if receipt.status == 1:
        deployed_address = receipt.contractAddress
        print("\n=========================================================")
        print("[+] تم نشر العقد بنجاح!")
        print(f"    عنوان العقد المنشور: {deployed_address}")
        print(f"    رقم الكتلة (Block) : {receipt.blockNumber}")
        print(f"    الغاز المستهلك     : {receipt.gasUsed}")
        print(f"    رابط المستكشف      : {explorer_base}/address/{deployed_address}")
        print("=========================================================")

        with open(".env", "a", encoding="utf-8") as f:
            f.write(f"\nESCROW_CONTRACT_ADDRESS={deployed_address}\n")
        print("[+] تم حفظ ESCROW_CONTRACT_ADDRESS داخل .env")
    else:
        print("[-] فشلت المعاملة وتم ارتدادها على البلوكتشين (Reverted).")
        sys.exit(1)

if __name__ == "__main__":
    deploy()