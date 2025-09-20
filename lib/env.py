import os
from typing import Callable, Literal, Optional, TypeVar
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

type EnvKey = Literal[
    "OPENAI_API_KEY",
    "LANGSMITH_TRACING",
    "LANGSMITH_ENDPOINT",
    "LANGSMITH_API_KEY",
    "LANGSMITH_PROJECT",
]

T = TypeVar("T")


def get_env(env_key: EnvKey, cast: Callable[[str], T] = str) -> Optional[T]:
    result = os.getenv(env_key)
    if result is None:
        return result
    return cast(result)
