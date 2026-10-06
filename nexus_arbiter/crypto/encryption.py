import os
import json
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

def generate_encryption_keypair() -> tuple[x25519.X25519PrivateKey, x25519.X25519PublicKey]:
    """Generate an X25519 keypair for cryptographic key exchange."""
    private_key = x25519.X25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key

def derive_shared_secret(
    private_key: x25519.X25519PrivateKey,
    peer_public_key_hex: str,
    salt: bytes,
    info: bytes = b"nexus-arbiter-v1-negotiation"
) -> bytes:
    """
    Derive a 32-byte shared symmetric key using ECDH followed by HKDF-SHA256.
    """
    peer_public_bytes = bytes.fromhex(peer_public_key_hex)
    peer_public_key = x25519.X25519PublicKey.from_public_bytes(peer_public_bytes)
    
    # 1. Diffie-Hellman Key Exchange over Curve25519 (ECDH)
    raw_shared_key = private_key.exchange(peer_public_key)

    # 2. Derive cryptographically secure symmetric key via HKDF
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=info
    )
    return hkdf.derive(raw_shared_key)

def encrypt_payload(
    shared_key: bytes,
    plaintext_data: dict,
    associated_data: bytes = b""
) -> dict:
    """
    Encrypt proposal or payload using ChaCha20-Poly1305 (AEAD).
    """
    # Generate unique random nonce per message (12 bytes)
    nonce = os.urandom(12)
    cipher = ChaCha20Poly1305(shared_key)
    
    plaintext_bytes = json.dumps(plaintext_data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ciphertext = cipher.encrypt(nonce, plaintext_bytes, associated_data)

    return {
        "nonce_hex": nonce.hex(),
        "ciphertext_hex": ciphertext.hex()
    }

def decrypt_payload(
    shared_key: bytes,
    nonce_hex: str,
    ciphertext_hex: str,
    associated_data: bytes = b""
) -> dict:
    """
    Decrypt payload envelope and verify Poly1305 authentication tag.
    """
    nonce = bytes.fromhex(nonce_hex)
    ciphertext = bytes.fromhex(ciphertext_hex)
    cipher = ChaCha20Poly1305(shared_key)

    decrypted_bytes = cipher.decrypt(nonce, ciphertext, associated_data)
    return json.loads(decrypted_bytes.decode("utf-8"))