import os
import sys
import json
from pathlib import Path
from web3 import Web3
from eth_account import Account

def load_env_file():
    """Load key-value pairs from .env into environment variables."""
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()

def deploy():
    load_env_file()

    rpc_url = os.getenv("RPC_URL", "https://ethereum-sepolia-rpc.publicnode.com")
    private_key = os.getenv("DEPLOYER_PRIVATE_KEY")
    usdc_address = os.getenv("USDC_ADDRESS", "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238")
    arbiter_address = os.getenv("ARBITER_ADDRESS")

    if not private_key or "المفتاح_الخاص" in private_key:
        print("[-] Error: DEPLOYER_PRIVATE_KEY is missing or invalid in .env")
        sys.exit(1)

    # 1. Connect to RPC
    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 20}))
    if not w3.is_connected():
        print(f"[-] Error: Unable to connect to RPC endpoint: {rpc_url}")
        sys.exit(1)

    # قراءة معرّف الشبكة الفعلي مباشرة من مزود الاتصال
    actual_chain_id = w3.eth.chain_id

    account = Account.from_key(private_key)
    deployer_address = account.address
    arbiter = arbiter_address if arbiter_address and "0x" in arbiter_address else deployer_address

    print("=========================================================")
    print("      NexusArbiter On-Chain Deployment Protocol          ")
    print("=========================================================")
    print(f"[*] Detected Chain ID : {actual_chain_id}")
    print(f"[*] Deployer Wallet   : {deployer_address}")
    print(f"[*] Arbiter Engine    : {arbiter}")
    print(f"[*] USDC Token        : {usdc_address}")

    # 2. Check Gas Balance
    balance_wei = w3.eth.get_balance(deployer_address)
    balance_eth = w3.from_wei(balance_wei, "ether")
    print(f"[*] ETH Balance       : {balance_eth:.6f} ETH")

    if balance_wei == 0:
        print(f"\n[-] Error: Account {deployer_address} has 0 ETH on this network.")
        sys.exit(1)

    # 3. Load Compiled Artifact
    artifact_path = Path("build/AgentEscrow.json")
    if not artifact_path.exists():
        print(f"[-] Error: Artifact not found at {artifact_path}. Run scripts.compile_contract first.")
        sys.exit(1)

    with open(artifact_path, "r", encoding="utf-8") as f:
        artifact = json.load(f)

    abi = artifact["abi"]
    bytecode = artifact["bytecode"]

    contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    # 4. Build Constructor Transaction
    nonce = w3.eth.get_transaction_count(deployer_address)
    gas_price = w3.eth.gas_price

    print("[*] Building deployment transaction...")
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
        print(f"[*] Estimated Gas     : {tx_data['gas']}")
    except Exception as e:
        print(f"[!] Warning: Gas estimation fallback ({e}). Setting 3,500,000 gas limit.")
        tx_data["gas"] = 3500000

    # 5. Sign & Broadcast Transaction
    print("[*] Signing transaction with deployer key...")
    signed_tx = w3.eth.account.sign_transaction(tx_data, private_key=private_key)

    raw_tx = getattr(signed_tx, "raw_transaction", None) or getattr(signed_tx, "rawTransaction", None)
    print("[*] Broadcasting transaction to mempool...")
    tx_hash = w3.eth.send_raw_transaction(raw_tx)
    tx_hash_hex = tx_hash.hex()
    
    explorer_base = "https://sepolia.etherscan.io" if actual_chain_id == 11155111 else "https://sepolia.basescan.org"
    print(f"[+] Broadcasted! TX Hash: {tx_hash_hex}")
    print(f"    Explorer: {explorer_base}/tx/{tx_hash_hex}")

    print("[*] Awaiting on-chain block confirmation (receipt)...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

    if receipt.status == 1:
        deployed_address = receipt.contractAddress
        print("\n=========================================================")
        print("[+] DEPLOYMENT SUCCESSFUL!")
        print(f"    Contract Address : {deployed_address}")
        print(f"    Block Number     : {receipt.blockNumber}")
        print(f"    Gas Used         : {receipt.gasUsed}")
        print(f"    Explorer Link    : {explorer_base}/address/{deployed_address}")
        print("=========================================================")

        with open(".env", "a", encoding="utf-8") as f:
            f.write(f"\nESCROW_CONTRACT_ADDRESS={deployed_address}\n")
        print("[+] Saved ESCROW_CONTRACT_ADDRESS to .env")
    else:
        print("[-] Deployment transaction reverted on-chain.")
        sys.exit(1)

if __name__ == "__main__":
    deploy()