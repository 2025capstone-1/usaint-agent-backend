from typing import List

from langchain_core.tools import BaseTool, tool

from apps.agent.session import Session
from apps.agent.type import ToolCallResult


def get_browser_tools(session: Session):

    @tool
    async def open_url(url: str) -> None:
        """Open {url} in the browser."""
        await session.page.goto(url, wait_until="networkidle")

    @tool
    async def get_html(selector: str = "html") -> str:
        """Get html source in the current page."""
        return await session.page.inner_html(selector)

    @tool
    async def click_element(selector: str):
        """Do click {selector} html element."""
        return await session.page.click(selector, timeout=5000)

    return [open_url, get_html, click_element]


async def execute_tool_calls(
    tools: list[BaseTool], tool_call_results: list[ToolCallResult]
):
    for tool_call_result in tool_call_results:
        tool_name = tool_call_result["type"]
        tool_args = tool_call_result["args"]

        # 도구 이름과 일치하는 도구를 찾습니다.
        matching_tool = next((tool for tool in tools if tool.name == tool_name), None)

        if matching_tool:
            result = await matching_tool.ainvoke(tool_args)
            print(f"[실행도구] {tool_name}\n[실행결과] {result}")
        else:
            print(f"경고: {tool_name}에 해당하는 도구를 찾을 수 없습니다.")
