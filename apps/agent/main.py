import asyncio
from typing import Annotated

import mermaid
from langchain_core.runnables.config import RunnableConfig
from langchain_openai import ChatOpenAI
from langchain_teddynote import logging
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from playwright.async_api import async_playwright
from typing_extensions import TypedDict

from apps.agent.prompt import get_prompt
from apps.agent.rag import search_ssu_notice
from apps.agent.session import session_manager
from apps.agent.usaint import (
    click_in_iframe,
    get_iframe_interactive_element,
    get_iframe_text_content,
    insert_text,
    search_menu,
    select_navigation_menu,
    usaint_login,
)
from lib.env import get_env

# 메모리 저장소 생성
memory = MemorySaver()


# LLM 초기화
tools = [
    click_in_iframe,
    insert_text,
    get_iframe_interactive_element,
    get_iframe_text_content,
    select_navigation_menu,
    search_menu,
    search_ssu_notice,
]
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
llm_with_tools = llm.bind_tools(tools)


# 상태 정의
class State(TypedDict):
    # 메시지 목록 주석 추가
    messages: Annotated[list, add_messages]
    session_id: str


async def chatbot(state: State):
    # 메시지 호출 및 반환
    response = await llm_with_tools.ainvoke(state["messages"])
    print(f"\n[DEBUG] Response type: {type(response)}")
    print(f"[DEBUG] Response content: {response.content}")
    print(
        f"[DEBUG] Tool calls: {response.tool_calls if hasattr(response, 'tool_calls') else 'No tool_calls attribute'}"
    )
    state["messages"] = [response]
    return state


session_id = "test1234"


async def main():

    logging.langsmith("UsaintBot")

    # 상태 그래프 초기화
    graph_builder = StateGraph(State)

    # 노드 추가
    graph_builder.add_node("chatbot", chatbot)

    # 도구 노드 생성
    tool_node = ToolNode(tools=tools)

    # 그래프에 도구 노드 추가
    graph_builder.add_node("tools", tool_node)

    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_conditional_edges("chatbot", tools_condition)
    graph_builder.add_edge("tools", "chatbot")

    # 그래프 컴파일
    graph = graph_builder.compile(checkpointer=memory)

    # 그래프 시각화
    try:
        mermaid_str = graph.get_graph().draw_mermaid()
        mermaid.Mermaid(mermaid_str).to_png("output.png")
        print("Graph visualization saved to output.png")
    except Exception as e:
        print(f"Could not generate graph visualization: {e}")

    config = RunnableConfig(
        recursion_limit=25,  # 최대 25개의 노드까지 방문. 그 이상은 RecursionError 발생
        configurable={"thread_id": session_id},  # 스레드 ID 설정
    )

    async with async_playwright() as playwright:
        session = session_manager.get_session(session_id)
        await session.start(playwright)

        print("Logging in to USAINT...")
        await usaint_login(session, get_env("USAINT_ID"), get_env("USAINT_PASSWORD"))

        question = "내 학적 정보 조회해줘."

        # 시스템 메시지와 사용자 질문을 함께 전달
        print(f"\n{'='*50}")
        print(f"User: {question}")
        print(f"{'='*50}\n")

        async for event in graph.astream(
            {
                "session_id": session_id,
                "messages": [
                    (
                        "system",
                        get_prompt(session_id),
                    ),
                    ("user", question),
                ],
            },
            config=config,
        ):
            for value in event.values():
                if "messages" in value and value["messages"]:
                    value["messages"][-1].pretty_print()

        print(f"\n{'='*50}")
        print("Conversation completed")
        print(f"{'='*50}\n")

    # # 이어지는 질문
    # print("\nAsking follow-up question...")
    # question = "내 이름이 뭐라고 했지?"
    #
    # async for event in graph.astream(
    #     {
    #         "session_id": session_id,
    #         "messages": [("user", question)]
    #     },
    #     config=config
    # ):
    #     for value in event.values():
    #         if "messages" in value and value["messages"]:
    #             value["messages"][-1].pretty_print()


if __name__ == "__main__":
    asyncio.run(main())
