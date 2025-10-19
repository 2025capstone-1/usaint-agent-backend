from typing import Annotated, Dict, TypedDict
from langgraph.graph.message import add_messages


class ToolCallResult(TypedDict):
    type: str
    args: Dict[str, str]
