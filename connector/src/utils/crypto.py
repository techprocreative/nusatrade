from cryptography.fernet import Fernet


def generate_key() -> bytes:
    return Fernet.generate_key()


def encrypt(token: bytes, message: str) -> bytes:
    cipher = Fernet(token)
    return cipher.encrypt(message.encode())


def decrypt(token: bytes, token_message: bytes) -> str:
    cipher = Fernet(token)
    return cipher.decrypt(token_message).decode()
