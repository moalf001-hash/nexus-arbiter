import json
import os
from pathlib import Path
from web3 import Web3

def load_env():
    env_vars = {}
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip()
    return env_vars

def verify_onchain_escrow():
    env = load_env()
    rpc_url = env.get("RPC_URL", "https://ethereum-sepolia-rpc.publicnode.com")
    contract_address = env.get("ESCROW_CONTRACT_ADDRESS")

    if not contract_address:
        print("[-] Error: ESCROW_CONTRACT_ADDRESS not found in .env")
        return

    # 1. الاتصال بمزود البلوكتشين
    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 15}))
    if not w3.is_connected():
        print(f"[-] Error: Could not connect to RPC: {rpc_url}")
        return

    # 2. تحميل الـ ABI الخاص بالعقد
    artifact_path = Path("build/AgentEscrow.json")
    if not artifact_path.exists():
        print(f"[-] Error: Artifact not found at {artifact_path}")
        return

    with open(artifact_path, "r", encoding="utf-8") as f:
        artifact = json.load(f)

    contract = w3.eth.contract(
        address=Web3.to_checksum_address(contract_address),
        abi=artifact["abi"]
    )

    # 3. قراءة المتغيرات العامة من العقد الحي
    owner = contract.functions.platformOwner().call()
    arbiter = contract.functions.arbiterEngine().call()
    usdc = contract.functions.usdcToken().call()
    fee_bps = contract.functions.PLATFORM_FEE_BPS().call()
    bps_denominator = contract.functions.BPS_DENOMINATOR().call()

    fee_percentage = (fee_bps / bps_denominator) * 100

    print("=========================================================")
    print("      NexusArbiter On-Chain Contract Verification        ")
    print("=========================================================")
    print(f"[*] Network          : Ethereum Sepolia (Chain ID: {w3.eth.chain_id})")
    print(f"[*] Contract Address : {contract.address}")
    print(f"[*] Platform Owner   : {owner}")
    print(f"[*] Arbiter Engine   : {arbiter}")
    print(f"[*] USDC Token       : {usdc}")
    print(f"[*] Platform Fee     : {fee_bps} BPS ({fee_percentage:.2f}%)")
    print("=========================================================")
    print("[+] SUCCESS: The smart contract is live and fully responsive!")

if __name__ == "__main__":
    verify_onchain_escrow()