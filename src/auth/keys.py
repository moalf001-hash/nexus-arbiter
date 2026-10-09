import hashlib
import hmac
import secrets
from typing import Tuple

KEY_PREFIX = "nx_live_"

def generate_api_key() -> Tuple[str, str, str]:
    """
    Generates a new cryptographically secure API key.
    
    Returns:
        - raw_key: The full plaintext API key (displayed to the client only once).
        - key_hash: The SHA-256 hash (persisted in the database).
        - prefix: First 16 characters for visual identification and dashboard listing.
    """
    # Generate 32 bytes of cryptographically secure randomness
    random_bytes = secrets.token_urlsafe(32)
    raw_key = f"{KEY_PREFIX}{random_bytes}"
    
    # Extract identifier prefix
    prefix = raw_key[:16]
    
    # Compute SHA-256 hash
    key_hash = hash_api_key(raw_key)
    
    return raw_key, key_hash, prefix

def hash_api_key(key: str) -> str:
    """
    Hashes the API key using SHA-256.
    """
    return hashlib.sha256(key.encode("utf-8")).hexdigest()

def verify_api_key(provided_key: str, stored_hash: str) -> bool:
    """
    Verifies the provided API key against the stored hash.
    Utilizes compare_digest to mitigate timing attacks.
    """
    if not provided_key.startswith(KEY_PREFIX):
        return False
    
    computed_hash = hash_api_key(provided_key)
    return hmac.compare_digest(computed_hash, stored_hash)