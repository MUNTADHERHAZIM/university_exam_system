import base64
import hashlib
from cryptography.fernet import Fernet
from django.conf import settings

def get_cipher():
    # Derive a 32-byte key from the Django SECRET_KEY
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key)
    return Fernet(fernet_key)

def encrypt_data(plain_text):
    if not plain_text:
        return ""
    cipher = get_cipher()
    return cipher.encrypt(plain_text.encode()).decode()

def decrypt_data(cipher_text):
    if not cipher_text:
        return ""
    try:
        cipher = get_cipher()
        return cipher.decrypt(cipher_text.encode()).decode()
    except Exception:
        # If decryption fails (e.g. data wasn't encrypted), return as is
        return cipher_text
