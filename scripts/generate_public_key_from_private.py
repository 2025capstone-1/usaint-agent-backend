#!/usr/bin/env python3
"""
기존 private_key.pem 파일에서 public key를 생성하는 스크립트
"""

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import base64
import os

def generate_public_key():
    """private_key.pem에서 public key를 추출합니다."""

    # private_key.pem 파일 경로
    private_key_path = os.path.join(os.getcwd(), "private_key.pem")

    if not os.path.exists(private_key_path):
        print(f"❌ Error: {private_key_path} 파일을 찾을 수 없습니다.")
        return

    # Private key 로드
    with open(private_key_path, "rb") as f:
        private_key_pem = f.read()

    private_key = serialization.load_pem_private_key(
        private_key_pem,
        password=None,
        backend=default_backend()
    )

    # Public key 추출
    public_key = private_key.public_key()

    # Public key를 uncompressed point 형식으로 변환
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )

    # URL-safe base64로 인코딩
    public_key_base64 = base64.urlsafe_b64encode(public_key_bytes).decode('utf-8').rstrip('=')

    # Private key를 PEM 형식으로 변환 (문자열)
    private_key_str = private_key_pem.decode('utf-8').strip()

    print("=" * 80)
    print("VAPID Keys from private_key.pem")
    print("=" * 80)
    print()
    print(".env 파일의 다음 부분을 업데이트하세요:")
    print()
    print(f'VAPID_PRIVATE_KEY="{private_key_str.replace(chr(10), "\\n")}"')
    print(f"VAPID_PUBLIC_KEY={public_key_base64}")
    print()
    print("=" * 80)
    print()
    print("프론트엔드에서 사용할 공개키:")
    print(public_key_base64)
    print()
    print("=" * 80)

if __name__ == "__main__":
    generate_public_key()
