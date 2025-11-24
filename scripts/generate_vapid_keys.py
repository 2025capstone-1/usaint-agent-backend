#!/usr/bin/env python3
"""
VAPID 키 생성 스크립트

Web Push 알림을 위한 VAPID 키 쌍을 생성합니다.
생성된 키는 .env 파일에 추가해야 합니다.
"""

from py_vapid import Vapid01
from cryptography.hazmat.primitives import serialization
import base64

def generate_vapid_keys():
    """VAPID 키 쌍을 생성하고 출력합니다."""

    print("=" * 80)
    print("VAPID Keys Generation")
    print("=" * 80)
    print()

    try:
        # Generate new VAPID keys
        vapid = Vapid01()
        vapid.generate_keys()

        # Get private key in PEM format
        private_key_pem = vapid.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8').strip()

        # Get public key as uncompressed point
        public_key_bytes = vapid.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )

        # Convert public key to URL-safe base64
        public_key_base64 = base64.urlsafe_b64encode(public_key_bytes).decode('utf-8').rstrip('=')

        print("VAPID keys generated successfully!")
        print()
        print("=" * 80)
        print("Add the following lines to your .env file:")
        print("=" * 80)
        print()
        print(f"VAPID_PRIVATE_KEY=\"{private_key_pem}\"")
        print(f"VAPID_PUBLIC_KEY={public_key_base64}")
        print("VAPID_CLAIM_EMAIL=mailto:your-email@example.com  # 반드시 실제 이메일로 변경하세요!")
        print()
        print("=" * 80)
        print()
        print("Public key for frontend (프론트엔드에서 사용할 공개키):")
        print(f"{public_key_base64}")
        print()
        print("=" * 80)

    except Exception as e:
        print(f"Error generating VAPID keys: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    generate_vapid_keys()
