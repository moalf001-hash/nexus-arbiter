import json
import os
from uuid import UUID
from typing import Optional, Dict, Any
from web3 import Web3

class EscrowBlockchainClient:
    DEFAULT_ABI = [
        {
            "inputs": [{"internalType": "bytes32", "name": "sessionId", "type": "bytes32"}],
            "name": "settleAndSplit",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function"
        },
        {
            "inputs": [
                {"internalType": "bytes32", "name": "sessionId", "type": "bytes32"},
                {"internalType": "address", "name": "seller", "type": "address"},
                {"internalType": "uint256", "name": "amountUnits", "type": "uint256"},
                {"internalType": "uint256", "name": "durationSeconds", "type": "uint256"},
                {"internalType": "bytes", "name": "agreementHash", "type": "bytes"}
            ],
            "name": "lockFunds",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function"
        }
    ]

    def __init__(self, rpc_url: Optional[str] = None, contract_address: Optional[str] = None):
        self.rpc_url = rpc_url or os.getenv("RPC_URL", "https://sepolia.base.org")
        self.chain_id = int(os.getenv("CHAIN_ID", "84532"))
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))

        default_addr = os.getenv("ESCROW_CONTRACT_ADDRESS", "0xF2D0F7cb12dF286ABba3683810E4228A4e72C61C")
        target_addr = contract_address or default_addr

        self.contract_address = (
            Web3.to_checksum_address(target_addr)
            if target_addr
            else "0x0000000000000000000000000000000000000000"
        )

        self.abi = self._load_abi()
        self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.abi)

    def _load_abi(self) -> list:
        artifact_path = os.path.join(os.getcwd(), "build", "AgentEscrow.json")
        if os.path.exists(artifact_path):
            try:
                with open(artifact_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("abi", data)
            except Exception:
                pass
        return self.DEFAULT_ABI

    @staticmethod
    def session_to_bytes32(session_id: UUID | str) -> bytes:
        if isinstance(session_id, str):
            session_id = UUID(session_id)
        return session_id.bytes.ljust(32, b"\x00")

    @staticmethod
    def usdc_to_units(amount_usdc: float) -> int:
        return int(round(amount_usdc * 1_000_000))

    def _get_safe_gas_price(self) -> int:
        try:
            return self.w3.eth.gas_price
        except Exception:
            return 100_000_000

    def build_lock_funds_tx(
        self,
        buyer_address: str,
        session_id: UUID | str,
        seller_address: str,
        amount_usdc: float,
        duration_seconds: int,
        agreement_hash_hex: str
    ) -> dict:
        buyer = Web3.to_checksum_address(buyer_address)
        seller = Web3.to_checksum_address(seller_address)
        session_bytes = self.session_to_bytes32(session_id)
        amount_units = self.usdc_to_units(amount_usdc)
        agreement_bytes = bytes.fromhex(agreement_hash_hex)

        try:
            nonce = self.w3.eth.get_transaction_count(buyer)
        except Exception:
            nonce = 0

        tx_data = self.contract.functions.lockFunds(
            session_bytes,
            seller,
            amount_units,
            duration_seconds,
            agreement_bytes
        ).build_transaction({
            "from": buyer,
            "nonce": nonce,
            "gas": 150000,
            "gasPrice": self._get_safe_gas_price(),
            "chainId": self.chain_id
        })
        return tx_data

    def build_settle_and_split_tx(self, sender_address: str, session_id: UUID | str) -> dict:
        sender = Web3.to_checksum_address(sender_address)
        session_bytes = self.session_to_bytes32(session_id)

        try:
            nonce = self.w3.eth.get_transaction_count(sender)
        except Exception:
            nonce = 0

        tx_data = self.contract.functions.settleAndSplit(
            session_bytes
        ).build_transaction({
            "from": sender,
            "nonce": nonce,
            "gas": 120000,
            "gasPrice": self._get_safe_gas_price(),
            "chainId": self.chain_id
        })
        return tx_data

    def broadcast_settlement_tx(self, private_key: str, session_id: UUID | str, timeout: int = 120) -> Dict[str, Any]:
        account = self.w3.eth.account.from_key(private_key)
        tx_data = self.build_settle_and_split_tx(account.address, session_id)
        signed_tx = self.w3.eth.account.sign_transaction(tx_data, private_key=private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)

        status_str = "SUCCESS" if receipt.status == 1 else "FAILED"
        tx_hash_hex = tx_hash.hex()

        return {
            "tx_hash": tx_hash_hex,
            "status": status_str,
            "block_number": receipt.blockNumber,
            "gas_used": receipt.gasUsed,
            "basescan_url": f"https://sepolia.basescan.org/tx/{tx_hash_hex}"
        }
