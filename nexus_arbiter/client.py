from datetime import datetime, timezone
import json
import os
from typing import Any, Optional, Union
from uuid import UUID, uuid4
import httpx

from .schemas import (
    ActionType,
    CurrencyType,
    ItemType,
    NegotiationPayload,
    EncryptedPayloadEnvelope,
    PriceCommitment,
    SignedNegotiationMessage
)
from .crypto.signatures import generate_keypair, sign_bytes
from .crypto.encryption import (
    generate_encryption_keypair,
    derive_shared_secret,
    encrypt_payload,
    decrypt_payload
)

class NexusAgentClient:
    def __init__(self, agent_id: str, gateway_url: str = "http://127.0.0.1:8000"):
        self.agent_id = agent_id
        self.gateway_url = gateway_url.rstrip("/")
        
        self.private_key, self.public_key = generate_keypair()
        self.public_key_hex = self.public_key.public_bytes_raw().hex()

        self.enc_private_key, self.enc_public_key = generate_encryption_keypair()
        self.enc_public_key_hex = self.enc_public_key.public_bytes_raw().hex()

        self.session_sequences: dict[UUID, int] = {}

    def sync_sequence(self, session_id: UUID, next_sequence: int):
        self.session_sequences[session_id] = next_sequence

    def _sign_and_post_step(
        self,
        session_id: UUID,
        action: ActionType,
        payload: Union[NegotiationPayload, EncryptedPayloadEnvelope],
        sequence_id: Optional[int] = None,
        client: Optional[httpx.Client] = None
    ) -> dict[str, Any]:
        current_seq = sequence_id if sequence_id is not None else self.session_sequences.get(session_id, 1)

        msg_stub = SignedNegotiationMessage(
            session_id=session_id,
            sequence_id=current_seq,
            sender_agent_id=self.agent_id,
            action=action,
            payload=payload,
            public_key_hex=self.public_key_hex,
            signature_hex="0" * 128
        )

        sig_hex = sign_bytes(self.private_key, msg_stub.message_digest_bytes())
        signed_msg = msg_stub.model_copy(update={"signature_hex": sig_hex})
        msg_payload = signed_msg.model_dump(mode="json")

        url = f"{self.gateway_url}/negotiate/step"
        if client:
            resp = client.post(url, json=msg_payload)
        else:
            resp = httpx.post(url, json=msg_payload)

        resp.raise_for_status()
        self.session_sequences[session_id] = current_seq + 1
        return resp.json()

    # --- End-to-End Encryption (E2EE) ---

    def create_encrypted_payload(
        self,
        peer_enc_pubkey_hex: str,
        session_id: UUID,
        item_type: ItemType,
        price_unit: float,
        quantity: int = 1,
        sla_hours: int = 24
    ) -> EncryptedPayloadEnvelope:
        salt = session_id.bytes
        shared_key = derive_shared_secret(self.enc_private_key, peer_enc_pubkey_hex, salt=salt)
        
        raw_data = {
            "item_type": item_type.value,
            "price_unit": price_unit,
            "quantity": quantity,
            "currency": "USDC",
            "sla_hours": sla_hours
        }
        enc_result = encrypt_payload(shared_key, raw_data)
        
        return EncryptedPayloadEnvelope(
            nonce_hex=enc_result["nonce_hex"],
            ciphertext_hex=enc_result["ciphertext_hex"],
            sender_enc_pubkey_hex=self.enc_public_key_hex
        )

    def decrypt_received_payload(
        self,
        session_id: UUID,
        envelope: EncryptedPayloadEnvelope
    ) -> dict[str, Any]:
        salt = session_id.bytes
        shared_key = derive_shared_secret(
            self.enc_private_key,
            envelope.sender_enc_pubkey_hex,
            salt=salt
        )
        return decrypt_payload(shared_key, envelope.nonce_hex, envelope.ciphertext_hex)

    def propose_encrypted(
        self,
        peer_enc_pubkey_hex: str,
        item_type: ItemType,
        price_unit: float,
        quantity: int = 1,
        sla_hours: int = 24,
        client: Optional[httpx.Client] = None
    ) -> tuple[UUID, EncryptedPayloadEnvelope, dict[str, Any]]:
        session_id = uuid4()
        enc_envelope = self.create_encrypted_payload(
            peer_enc_pubkey_hex=peer_enc_pubkey_hex,
            session_id=session_id,
            item_type=item_type,
            price_unit=price_unit,
            quantity=quantity,
            sla_hours=sla_hours
        )
        res = self._sign_and_post_step(session_id, ActionType.PROPOSE, enc_envelope, client=client)
        return session_id, enc_envelope, res

    def counter_encrypted(
        self,
        peer_enc_pubkey_hex: str,
        session_id: UUID,
        item_type: ItemType,
        price_unit: float,
        quantity: int = 1,
        sla_hours: int = 24,
        sequence_id: Optional[int] = None,
        client: Optional[httpx.Client] = None
    ) -> tuple[EncryptedPayloadEnvelope, dict[str, Any]]:
        enc_envelope = self.create_encrypted_payload(
            peer_enc_pubkey_hex=peer_enc_pubkey_hex,
            session_id=session_id,
            item_type=item_type,
            price_unit=price_unit,
            quantity=quantity,
            sla_hours=sla_hours
        )
        res = self._sign_and_post_step(
            session_id, ActionType.COUNTER, enc_envelope, sequence_id=sequence_id, client=client
        )
        return enc_envelope, res

    # --- Cryptographic Buyer Price Commitment ---

    def create_price_commitment(
        self,
        session_id: UUID,
        agreed_amount_usdc: float,
        seller_agent_id: str
    ) -> PriceCommitment:
        """Cryptographically sign the agreed price to prevent seller spoofing during settlement."""
        commitment = PriceCommitment(
            session_id=session_id,
            agreed_amount_usdc=agreed_amount_usdc,
            buyer_agent_id=self.agent_id,
            seller_agent_id=seller_agent_id,
            buyer_pubkey_hex=self.public_key_hex,
            buyer_signature_hex="0" * 128
        )
        sig = sign_bytes(self.private_key, commitment.digest_bytes())
        return commitment.model_copy(update={"buyer_signature_hex": sig})

    # --- Acceptance, Arbitration, and Settlement ---

    def accept(
        self,
        session_id: UUID,
        agreed_payload: Union[NegotiationPayload, EncryptedPayloadEnvelope],
        sequence_id: Optional[int] = None,
        client: Optional[httpx.Client] = None
    ) -> dict[str, Any]:
        return self._sign_and_post_step(
            session_id, ActionType.ACCEPT, agreed_payload, sequence_id=sequence_id, client=client
        )

    def submit_and_settle(
        self,
        session_id: UUID,
        deliverable_dict: dict[str, Any],
        deadline_timestamp: float,
        deal_amount_usdc: float,
        price_commitment: Optional[PriceCommitment] = None,
        item_description: str = "AI Service Execution",
        client: Optional[httpx.Client] = None
    ) -> dict[str, Any]:
        raw_deliverable_json = json.dumps(deliverable_dict, sort_keys=True, separators=(",", ":"))
        delivery_sig_hex = sign_bytes(self.private_key, raw_deliverable_json.encode("utf-8"))

        settle_payload = {
            "session_id": str(session_id),
            "raw_deliverable_json": raw_deliverable_json,
            "seller_pub_key_hex": self.public_key_hex,
            "delivery_signature_hex": delivery_sig_hex,
            "deadline_timestamp": deadline_timestamp,
            "deal_amount_usdc": deal_amount_usdc,
            "price_commitment": price_commitment.model_dump(mode="json") if price_commitment else None,
            "item_description": item_description
        }

        url = f"{self.gateway_url}/arbiter/settle"
        if client:
            resp = client.post(url, json=settle_payload)
        else:
            resp = httpx.post(url, json=settle_payload)

        resp.raise_for_status()
        return resp.json()