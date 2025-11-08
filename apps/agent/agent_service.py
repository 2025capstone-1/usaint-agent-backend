from typing import Annotated, AsyncGenerator, Dict, Optional

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from playwright.async_api import Playwright, async_playwright
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


# 상태 정의
class State(TypedDict):
    messages: Annotated[list, add_messages]
    session_id: str


# 툴 이름을 한글 메시지로 변환하는 매핑
TOOL_NAME_TO_MESSAGE = {
    "search_ssu_notice": "숭실대 공지사항 검색 중...",
    "search_menu": "유세인트 메뉴 검색 중...",
    "select_navigation_menu": "메뉴 선택 중...",
    "get_iframe_text_content": "페이지 내용 읽는 중...",
    "get_iframe_interactive_element": "페이지 요소 찾는 중...",
    "click_in_iframe": "클릭 실행 중...",
    "insert_text": "텍스트 입력 중...",
}


class AgentService:
    """FastAPI에서 호출 가능한 에이전트 서비스 (LangGraph 기반)"""

    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
        self.playwright: Optional[Playwright] = None
        self.memory = MemorySaver()

        # 도구 정의
        self.tools = [
            click_in_iframe,
            insert_text,
            get_iframe_interactive_element,
            get_iframe_text_content,
            select_navigation_menu,
            search_menu,
            search_ssu_notice,
        ]

        # LLM에 도구 바인딩
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        # 그래프 초기화
        self.graph = self._build_graph()

    def _build_graph(self):
        """LangGraph 그래프 생성"""
        # 상태 그래프 초기화
        graph_builder = StateGraph(State)

        # chatbot 노드 정의
        async def chatbot(state: State):
            response = await self.llm_with_tools.ainvoke(state["messages"])
            return {"messages": [response]}

        # 노드 추가
        graph_builder.add_node("chatbot", chatbot)

        # 도구 노드 추가
        tool_node = ToolNode(tools=self.tools)
        graph_builder.add_node("tools", tool_node)

        # 엣지 추가
        graph_builder.add_edge(START, "chatbot")
        graph_builder.add_conditional_edges("chatbot", tools_condition)
        graph_builder.add_edge("tools", "chatbot")

        # 그래프 컴파일 (메모리 저장소 포함)
        return graph_builder.compile(checkpointer=self.memory)

    async def initialize(self):
        """Playwright 초기화"""
        if not self.playwright:
            self.playwright = await async_playwright().start()
            print("[AgentService] Playwright 초기화 완료")

    async def shutdown(self):
        """모든 세션 종료 및 Playwright 정리"""
        # 모든 세션 종료
        for session_id in list(session_manager.session_map.keys()):
            await self.close_session_by_id(session_id)

        # Playwright 종료
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
            print("[AgentService] Playwright 종료 완료")

    def _get_session_id(self, chat_room_id: int) -> str:
        """chat_room_id를 session_id로 변환"""
        return f"chatroom_{chat_room_id}"

    def _generate_tool_message(self, tool_name: str, tool_args: dict) -> str:
        """툴 이름과 인자를 기반으로 사용자 친화적인 메시지 생성"""
        if tool_name == "select_navigation_menu":
            # 실제 파라미터 이름은 menu_title
            menu_title = tool_args.get("menu_title", "")
            if menu_title:
                return f"'{menu_title}' 메뉴 선택 중..."
            return "메뉴 선택 중..."

        elif tool_name == "search_menu":
            # search_menu는 파라미터가 없음
            return "메뉴 구조 조회 중..."

        elif tool_name == "search_ssu_notice":
            query = tool_args.get("query", "")
            if query:
                return f"'{query}' 공지사항 검색 중..."
            return "숭실대 공지사항 검색 중..."

        elif tool_name == "insert_text":
            # 실제 파라미터 이름은 content
            content = tool_args.get("content", "")
            # 텍스트가 너무 길면 일부만 표시
            if content and len(content) <= 20:
                return f"'{content}' 입력 중..."
            elif content:
                return f"'{content[:20]}...' 입력 중..."
            return "텍스트 입력 중..."

        elif tool_name == "click_in_iframe":
            return "버튼 클릭 중..."

        elif tool_name == "get_iframe_text_content":
            return "페이지 내용 읽는 중..."

        elif tool_name == "get_iframe_interactive_element":
            return "페이지 요소 찾는 중..."

        else:
            # 기본 메시지
            return TOOL_NAME_TO_MESSAGE.get(tool_name, f"{tool_name} 실행 중...")

    async def process_message_stream(
        self,
        chat_room_id: int,
        message: str,
        usaint_id: str = None,
        usaint_password: str = None
    ) -> AsyncGenerator[Dict, None]:
        """
        사용자 메시지를 처리하고 스트리밍 방식으로 응답을 반환합니다.

        Args:
            chat_room_id: 채팅방 ID
            message: 사용자 메시지
            usaint_id: 유세인트 ID (선택)
            usaint_password: 유세인트 비밀번호 (선택)

        Yields:
            Dict: 이벤트 타입과 데이터를 포함한 딕셔너리
            - {"type": "tool_start", "tool_name": "...", "message": "..."}
            - {"type": "agent_message", "content": "..."}
            - {"type": "error", "message": "..."}
        """
        try:
            # Playwright가 초기화되지 않았다면 초기화
            if not self.playwright:
                await self.initialize()

            # chat_room_id를 session_id로 변환
            session_id = self._get_session_id(chat_room_id)

            # 채팅방별 세션 조회/생성
            session = session_manager.get_session(session_id)

            # 세션이 시작되지 않았다면 시작
            if session.page is None:
                await session.start(self.playwright)
                print(f"[AgentService] 채팅방 {chat_room_id}의 세션 시작: {session_id}")

                # 유세인트 로그인이 필요한 경우
                if usaint_id and usaint_password:
                    yield {
                        "type": "tool_start",
                        "tool_name": "usaint_login",
                        "message": "유세인트 로그인 중..."
                    }
                    await usaint_login(session, usaint_id, usaint_password)
                    print(f"[AgentService] 유세인트 로그인 완료: {session_id}")

            # LangGraph 설정
            config = {
                "recursion_limit": 25,
                "configurable": {"thread_id": session_id}
            }

            # 스트리밍 실행
            async for event in self.graph.astream(
                {
                    "session_id": session_id,
                    "messages": [
                        ("system", get_prompt(session_id)),
                        ("user", message)
                    ],
                },
                config=config,
            ):
                for value in event.values():
                    if "messages" in value and value["messages"]:
                        last_message = value["messages"][-1]

                        # AIMessage이면서 tool_calls가 있는 경우 (툴 호출)
                        if isinstance(last_message, AIMessage) and hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                            for tool_call in last_message.tool_calls:
                                # tool_call은 딕셔너리 또는 객체일 수 있음
                                if isinstance(tool_call, dict):
                                    tool_name = tool_call.get("name", "알 수 없는 도구")
                                    tool_args = tool_call.get("args", {})
                                else:
                                    # 객체인 경우 속성으로 접근
                                    tool_name = getattr(tool_call, "name", "알 수 없는 도구")
                                    tool_args = getattr(tool_call, "args", {})

                                # 툴 인자를 기반으로 구체적인 메시지 생성
                                tool_message = self._generate_tool_message(tool_name, tool_args)

                                # 디버깅용 로그
                                print(f"[AgentService] 툴 호출: {tool_name}, 인자: {tool_args}")

                                yield {
                                    "type": "tool_start",
                                    "tool_name": tool_name,
                                    "message": tool_message
                                }

                        # AIMessage이면서 content가 있는 경우 (최종 응답)
                        elif isinstance(last_message, AIMessage) and last_message.content:
                            yield {
                                "type": "agent_message",
                                "content": last_message.content
                            }

                        # ToolMessage는 무시 (내부 처리용)

        except Exception as e:
            print(f"[AgentService] 메시지 처리 중 오류: {e}")
            import traceback
            traceback.print_exc()
            yield {
                "type": "error",
                "message": f"오류가 발생했습니다: {str(e)}"
            }

    async def close_chat_room_session(self, chat_room_id: int):
        """특정 채팅방의 세션을 종료합니다."""
        session_id = self._get_session_id(chat_room_id)
        await self.close_session_by_id(session_id)

    async def close_session_by_id(self, session_id: str):
        """session_id로 세션을 종료합니다."""
        if session_id in session_manager.session_map:
            session = session_manager.session_map[session_id]
            await session.close()
            del session_manager.session_map[session_id]
            print(f"[AgentService] 세션 종료: {session_id}")


# 전역 싱글톤 인스턴스
agent_service = AgentService()
