import os
from typing import Literal

from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

type EnvKey = Literal[
    "OPENAI_API_KEY",
    "LANGSMITH_TRACING",
    "LANGSMITH_ENDPOINT",
    "LANGSMITH_API_KEY",
    "LANGSMITH_PROJECT",
    "USAINT_ID",
    "USAINT_PASSWORD"
    # 위는 무시.
    "ENV",
    "DB_USER",
    "DB_PASSWORD",
    "DB_HOST",
    "DB_PORT",
    "DB_NAME",
    "JWT_TYPE",
    "JWT_SECRET",
    "JWT_ALGORITHM",
    "ACCESS_TOKEN_TTL_MINUTES",
    "ENCRYPTION_KEY"
]


def get_env(env_key: EnvKey):
    result = os.getenv(env_key)
    return result
