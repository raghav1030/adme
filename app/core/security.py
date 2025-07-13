import hmac
import hashlib
from cryptography.fernet import Fernet
from app.core.config import settings

# Encryption for tokens
ENCRYPTION_KEY = settings.APP_SECRET_KEY.encode()
fernet = Fernet(ENCRYPTION_KEY)


def encrypt_token(token: str) -> str:
    return fernet.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    return fernet.decrypt(encrypted_token.encode()).decode()

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected_signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected_signature}", signature)
