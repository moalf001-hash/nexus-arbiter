import json
import os
from uuid import UUID
from web3 import Web3

class EscrowBlockchainClient:
    def __init__(self, rpc_url: str = "https://sepolia.base.org", contract_address: str = None):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.contract_address = (
            Web3.to_checksum_address(contract_address)
            if contract_address
            else "0x0000000000000000000000000000000000000000"
        )
        
        artifact_path = os.path.join("build", "AgentEscrow.json")
        if not os.path.exists(artifact_path):
            raise FileNotFoundError(f"ABI artifact file not found at path: {artifact_path}")
            
        with open(artifact_path, "r", encoding="utf-8") as f:
            artifact = json.load(f)
            
        self.abi = artifact["abi"]
        self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.abi)

    @staticmethod
    def session_to_bytes32(session_id: UUID | str) -> bytes:
        """Convert a 16-byte UUID session identifier into a 32-byte Solidity-compatible bytes32 representation."""
        if isinstance(session_id, str):
            session_id = UUID(session_id)
        # Right-pad the remaining 16 bytes with zeros to strictly match bytes32
        return session_id.bytes.ljust(32, b"\x00")

    @staticmethod
    def usdc_to_units(amount_usdc: float) -> int:
        """Convert standard USDC amount to micro-USDC integer units (6 decimal places)."""
        return int(round(amount_usdc * 1_000_000))

    def build_lock_funds_tx(
        self,
        buyer_address: str,
        session_id: UUID | str,
        seller_address: str,
        amount_usdc: float,
        duration_seconds: int,
        agreement_hash_hex: str
    ) -> dict:
        """
        Build unsigned transaction data to lock escrow funds in the smart contract.
        """
        buyer = Web3.to_checksum_address(buyer_address)
        seller = Web3.to_checksum_address(seller_address)
        session_bytes = self.session_to_bytes32(session_id)
        amount_units = self.usdc_to_units(amount_usdc)
        agreement_bytes = bytes.fromhex(agreement_hash_hex)

        tx_data = self.contract.functions.lockFunds(
            session_bytes,
            seller,
            amount_units,
            duration_seconds,
            agreement_bytes
        ).build_transaction({
            "from": buyer,
            "nonce": 0,
            "gas": 150000,
            "gasPrice": self.w3.to_wei("0.1", "gwei")
        })
        return tx_data

    def build_settle_and_split_tx(self, sender_address: str, session_id: UUID | str) -> dict:
        """
        Build unsigned transaction data to release funds, deduct the 1.5% platform fee, and disburse remainder to seller.
        """
        sender = Web3.to_checksum_address(sender_address)
        session_bytes = self.session_to_bytes32(session_id)

        try:
            gas_price = self.w3.eth.gas_price
        except Exception:
            gas_price = 100_000_000  # 0.1 Gwei default fallback

        tx_data = self.contract.functions.settleAndSplit(
            session_bytes
        ).build_transaction({
            "from": sender,
            "nonce": 0,
            "gas": 120000,
            "gasPrice": gas_price
        })
        return tx_data