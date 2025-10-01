import asyncio
from typing import List

from apps.agent import browser
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.output_parsers.openai_tools import JsonOutputToolsParser
from langchain_openai import ChatOpenAI
from playwright.async_api import async_playwright

import lib.env
from apps.agent import prompt
from apps.agent.session import Session
from apps.agent.type import ToolCallResult


async def main():

    session = Session()
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    async with async_playwright() as playwright:
        await session.start(playwright)

        tools = browser.get_browser_tools(session)
        agent = create_tool_calling_agent(llm, tools, prompt.prompt)
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True,
        )

        try:
            while True:
                user_input = input("입력: ")
                result = await agent_executor.ainvoke({"input": user_input})
                print(f"result: {result}")
                # await browser.execute_tool_calls(tools, result)

                # result: List[ToolCallResult] = chain.invoke("현재 페이지 HTML 가져와줘.")
                # print(f"result: {result}")
                # await browser.execute_tool_calls(tools, result)

        finally:
            await session.close()


if __name__ == "__main__":
    asyncio.run(main())
