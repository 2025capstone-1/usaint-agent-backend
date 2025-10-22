from cryptography.fernet import Fernet
from lib.env import get_env

# get_env 함수를 사용하여 ENCRYPTION_KEY를 가져옵니다.
encryption_key = get_env("ENCRYPTION_KEY")

# 키가 .env 파일에 설정되어 있는지 확인합니다.
if not encryption_key:
    raise ValueError("ENCRYPTION_KEY is not set in the environment variables.")

# Fernet 인스턴스를 생성합니다.
cipher_suite = Fernet(encryption_key.encode())

def encrypt_password(password: str) -> str:
    """비밀번호를 암호화하여 문자열로 반환합니다."""
    if not password:
        return ""
    encrypted_password = cipher_suite.encrypt(password.encode())
    return encrypted_password.decode()

def decrypt_password(encrypted_password: str) -> str:
    """암호화된 비밀번호를 복호화하여 원본 문자열로 반환합니다."""
    if not encrypted_password:
        return ""
    decrypted_password = cipher_suite.decrypt(encrypted_password.encode())
    return decrypted_password.decode()