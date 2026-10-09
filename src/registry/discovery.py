import time
import re
from typing import Dict, List, Optional
from urllib.parse import urlparse
from pydantic import BaseModel, Field, HttpUrl
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class ServiceCapability(BaseModel):
    name: str = Field(..., max_length=100)
    category: str = Field(..., max_length=50)
    description: str = Field(..., max_length=500)
    price_usdc: float = Field(..., gt=0.0)
    sla_seconds: int = Field(..., gt=0, le=86400)


class AgentRegistrationRequest(BaseModel):
    agent_id: str = Field(..., max_length=64)
    public_key_hex: str = Field(..., max_length=64)
    endpoint_url: HttpUrl
    capabilities: List[ServiceCapability]
    nonce: int
    signature: str


class SecureAgentRegistry:
    """
    Cryptographically verified directory for autonomous agents.
    Prevents SSRF, impersonation, and stale entry exploitation.
    """

    def __init__(self, entry_ttl_seconds: int = 86400):
        self.entry_ttl_seconds = entry_ttl_seconds
        self._agents: Dict[str, dict] = {}

    @staticmethod
    def _validate_safe_url(url: str) -> bool:
        """
        Hardened validation preventing Server-Side Request Forgery (SSRF).
        Rejects internal addresses, localhost, and non-HTTP(S) protocols.
        """
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False

        hostname = (parsed.hostname or "").lower()
        if not hostname:
            return False

        forbidden_patterns = [
            r"^localhost$",
            r"^127\.",
            r"^10\.",
            r"^192\.168\.",
            r"^172\.(1[6-9]|2[0-9]|3[0-1])\.",
            r"^169\.254\.",
            r"^0\.0\.0\.0$",
            r"^\[?::1\]?$"
        ]

        for pattern in forbidden_patterns:
            if re.match(pattern, hostname):
                return False

        return True

    @staticmethod
    def verify_ed25519_signature(public_key_hex: str, message: bytes, signature_hex: str) -> bool:
        try:
            public_key_bytes = bytes.fromhex(public_key_hex)
            signature_bytes = bytes.fromhex(signature_hex)
            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
            public_key.verify(signature_bytes, message)
            return True
        except Exception:
            return False

    def register_agent(self, payload: AgentRegistrationRequest) -> Dict[str, str]:
        """
        Validates cryptographic identity and registers an agent capability profile.
        """
        if not self._validate_safe_url(str(payload.endpoint_url)):
            raise ValueError("Endpoint URL violates network security policy (SSRF prevention).")

        canonical_data = (
            f"REGISTER:{payload.agent_id}:{payload.public_key_hex}:"
            f"{payload.endpoint_url}:{payload.nonce}"
        ).encode("utf-8")

        is_valid = self.verify_ed25519_signature(
            public_key_hex=payload.public_key_hex,
            message=canonical_data,
            signature_hex=payload.signature
        )

        if not is_valid:
            raise PermissionError("Registration failed: Invalid Ed25519 signature.")

        now = time.time()
        self._agents[payload.agent_id] = {
            "agent_id": payload.agent_id,
            "public_key_hex": payload.public_key_hex,
            "endpoint_url": str(payload.endpoint_url),
            "capabilities": [c.model_dump() for c in payload.capabilities],
            "registered_at": now,
            "last_heartbeat": now
        }

        return {
            "status": "REGISTERED",
            "agent_id": payload.agent_id,
            "capabilities_indexed": str(len(payload.capabilities))
        }

    def search_services(
        self,
        category: Optional[str] = None,
        max_price: Optional[float] = None
    ) -> List[dict]:
        results = []
        now = time.time()

        for agent in self._agents.values():
            if now - agent["last_heartbeat"] > self.entry_ttl_seconds:
                continue

            for cap in agent["capabilities"]:
                if category and cap["category"].lower() != category.lower():
                    continue
                if max_price is not None and cap["price_usdc"] > max_price:
                    continue

                results.append({
                    "agent_id": agent["agent_id"],
                    "public_key_hex": agent["public_key_hex"],
                    "endpoint_url": agent["endpoint_url"],
                    "service_name": cap["name"],
                    "category": cap["category"],
                    "price_usdc": cap["price_usdc"],
                    "sla_seconds": cap["sla_seconds"]
                })

        return results
