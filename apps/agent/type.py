from typing import Dict, TypedDict


class ToolCallResult(TypedDict):
    type: str
    args: Dict[str, str]
