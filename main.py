import asyncio
from typing import List

from langchain_core.output_parsers.openai_tools import JsonOutputToolsParser
from langchain_openai import ChatOpenAI
from playwright.async_api import async_playwright

import lib.env
from lib import browser
from lib.session import Session
from lib.type import ToolCallResult


async def main():
    session = Session()
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    async with async_playwright() as playwright:
        await session.run(playwright)

        # 도구 바인딩
        tools = browser.get_browser_tools(session)
        llm_with_tools = llm.bind_tools(tools)

        chain = llm_with_tools | JsonOutputToolsParser(tools=tools)
        result: List[ToolCallResult] = chain.invoke("네이버 홈페이지로 이동해줘")
        print(f"result: {result}")
        await browser.execute_tool_calls(tools, result)

        result: List[ToolCallResult] = chain.invoke("현재 페이지 HTML 가져와줘.")
        print(f"result: {result}")
        await browser.execute_tool_calls(tools, result)

        await asyncio.sleep(2)
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
