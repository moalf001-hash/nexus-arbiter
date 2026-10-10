import os
import sys
import json
import uuid
import getpass
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.blockchain.escrow_client import EscrowBlockchainClient


def load_private_key_from_keystore() -> str:
    keystore_path = os.getenv("DEPLOYER_KEYSTORE_PATH", "secrets/deployer_keystore.json")
    
    if not os.path.exists(keystore_path):
        # Fallback to plain private key if present
        plain_key = os.getenv("ARBITER_PRIVATE_KEY")
        if plain_key:
            return plain_key
        print(f"[!] Error: Keystore file not found at: {keystore_path}")
        sys.exit(1)

    with open(keystore_path, "r", encoding="utf-8") as f:
        keystore_data = json.load(f)

    # Get password from env or prompt user securely
    password = os.getenv("KEYSTORE_PASSWORD")
    if not password:
        password = getpass.getpass(prompt="Enter Keystore password: ")

    w3 = Web3()
    try:
        private_key_bytes = w3.eth.account.decrypt(keystore_data, password)
        return private_key_bytes.hex()
    except Exception as e:
        print(f"[!] Failed to decrypt keystore: {e}")
        sys.exit(1)


def main():
    print("=" * 60)
    print("NexusArbiter: Live Settlement Broadcast Test (Base Sepolia)")
    print("=" * 60)

    # Decrypt and retrieve private key safely
    private_key = load_private_key_from_keystore()

    client = EscrowBlockchainClient()
    account = client.w3.eth.account.from_key(private_key)
    signer_address = account.address

    print(f"[*] Connected RPC: {client.rpc_url}")
    print(f"[*] Chain ID: {client.chain_id}")
    print(f"[*] Escrow Contract: {client.contract_address}")
    print(f"[*] Signer Address: {signer_address}")

    # Check ETH balance
    balance_wei = client.w3.eth.get_balance(signer_address)
    balance_eth = client.w3.from_wei(balance_wei, "ether")
    print(f"[*] Wallet ETH Balance: {balance_eth:.6f} ETH")

    if balance_wei == 0:
        print("\n[!] Insufficient balance: Signer wallet has 0 ETH on Base Sepolia.")
        print(f"    Please fund address {signer_address} with testnet ETH.")
        sys.exit(1)

    # Generate a unique test session ID
    test_session_id = uuid.uuid4()
    print(f"\n[*] Generated Test Session ID: {test_session_id}")
    print("[*] Signing and broadcasting settleAndSplit transaction...")

    try:
        receipt_data = client.broadcast_settlement_tx(
            private_key=private_key,
            session_id=test_session_id,
            timeout=120
        )

        print("\n" + "=" * 60)
        print("TRANSACTION BROADCAST COMPLETED")
        print("=" * 60)
        print(f"Status:       {receipt_data['status']}")
        print(f"TX Hash:      {receipt_data['tx_hash']}")
        print(f"Block:        {receipt_data['block_number']}")
        print(f"Gas Used:     {receipt_data['gas_used']}")
        print(f"Explorer URL: {receipt_data['basescan_url']}")
        print("=" * 60)

    except Exception as e:
        print(f"\n[!] Broadcast failed with exception: {str(e)}")


if __name__ == "__main__":
    main()