from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

def generate_keypair() -> tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key

def sign_bytes(private_key: ed25519.Ed25519PrivateKey, data: bytes) -> str:
    signature = private_key.sign(data)
    return signature.hex()

def verify_signature(public_key_hex: str, signature_hex: str, data: bytes) -> bool:
    try:
        public_bytes = bytes.fromhex(public_key_hex)
        sig_bytes = bytes.fromhex(signature_hex)
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_bytes)
        public_key.verify(sig_bytes, data)
        return True
    except (InvalidSignature, ValueError):
        return False