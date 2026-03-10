import secrets
import hashlib


def generate_api_key() -> str:
    # Generate a random 32-byte API key and return it as a hex string
    return f"sk_live_{secrets.token_urlsafe(32)}" 
    

def hash_api_key(api_key: str) -> str:
    # Hash the API key using SHA-256 and return the hex digest
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    