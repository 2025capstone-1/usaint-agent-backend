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
from apps.agent.cafeteria import fetch_cafeteria_menu
from apps.agent.grade_fetcher import fetch_grade_summary, fetch_full_grades
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

from apps.user_api.domain.usaint_account.service import get_usaint_account_by_user_id
from lib.database import get_db
from lib.security import decrypt_password
from apps.agent.rag import search_notices

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
    "fetch_cafeteria_menu": "식당 메뉴 조회 중...",
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
            fetch_cafeteria_menu,
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
            from langchain_core.messages import SystemMessage

            # 시스템 프롬프트가 없으면 추가
            messages = list(state["messages"])
            has_system = any(isinstance(msg, SystemMessage) for msg in messages)

            if not has_system:
                # 첫 메시지면 시스템 프롬프트 추가
                session_id = state.get("session_id", "")
                messages = [SystemMessage(content=get_prompt(session_id))] + messages

            response = await self.llm_with_tools.ainvoke(messages)
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

    def clear_memory(self, chat_room_id: int):
        """특정 채팅방의 대화 메모리를 초기화"""
        session_id = self._get_session_id(chat_room_id)
        try:
            if hasattr(self.memory, "storage"):
                thread_key = (session_id,)
                if thread_key in self.memory.storage:
                    del self.memory.storage[thread_key]
                    print(f"[AgentService] 채팅방 {chat_room_id}의 메모리 초기화 완료")
                    return True
            return False
        except Exception as e:
            print(f"[AgentService] 메모리 초기화 실패: {e}")
            return False

    def _validate_and_fix_memory(self, session_id: str) -> bool:
        """
        메모리에서 불완전한 tool_calls를 감지하고 수정합니다.

        Returns:
            bool: 메모리가 수정되었으면 True, 그렇지 않으면 False
        """
        try:
            if not hasattr(self.memory, "storage"):
                return False

            thread_key = (session_id,)
            if thread_key not in self.memory.storage:
                return False

            # 메모리에서 상태 가져오기
            checkpoint = self.memory.storage[thread_key]
            if not checkpoint or "channel_values" not in checkpoint:
                return False

            channel_values = checkpoint["channel_values"]
            if "messages" not in channel_values:
                return False

            messages = channel_values["messages"]
            if not messages:
                return False

            # 마지막 메시지 확인
            last_message = messages[-1]

            # AIMessage이면서 tool_calls가 있는지 확인
            from langchain_core.messages import AIMessage, ToolMessage

            if (
                isinstance(last_message, AIMessage)
                and hasattr(last_message, "tool_calls")
                and last_message.tool_calls
            ):
                # tool_calls가 있는데 다음 메시지가 ToolMessage인지 확인
                # 마지막이 AIMessage(with tool_calls)면 ToolMessage가 없는 것
                print(
                    f"[AgentService] 불완전한 tool_calls 감지: {len(last_message.tool_calls)}개"
                )

                # 불완전한 AIMessage 제거
                messages.pop()
                checkpoint["channel_values"]["messages"] = messages
                self.memory.storage[thread_key] = checkpoint

                print(
                    f"[AgentService] 불완전한 메시지 제거 완료 (session: {session_id})"
                )
                return True

            return False

        except Exception as e:
            print(f"[AgentService] 메모리 검증 중 오류: {e}")
            import traceback

            traceback.print_exc()
            return False

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

        elif tool_name == "fetch_cafeteria_menu":
            restaurant_code = tool_args.get("restaurant_code", "")
            restaurant_names = {
                1: "학생식당",
                2: "숭실도담식당",
                4: "스넥코너",
                5: "푸드코트",
                6: "THE KITCHEN",
                7: "FACULTY LOUNGE",
            }
            restaurant_name = restaurant_names.get(restaurant_code, "식당")
            return f"{restaurant_name} 메뉴 조회 중..."

        else:
            # 기본 메시지
            return TOOL_NAME_TO_MESSAGE.get(tool_name, f"{tool_name} 실행 중...")

    async def process_message_stream(
        self,
        chat_room_id: int,
        message: str,
        usaint_id: str = None,
        usaint_password: str = None,
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

            # 세션 활동 시간 업데이트
            session.update_activity()

            # 메모리 검증 및 수정 (불완전한 tool_calls 제거)
            was_fixed = self._validate_and_fix_memory(session_id)
            if was_fixed:
                print(f"[AgentService] 메모리 상태 복구 완료")

            # 세션이 시작되지 않았다면 시작
            if session.page is None:
                await session.start(self.playwright)
                print(f"[AgentService] 채팅방 {chat_room_id}의 세션 시작: {session_id}")

                # 유세인트 로그인이 필요한 경우
                if usaint_id and usaint_password:
                    yield {
                        "type": "tool_start",
                        "tool_name": "usaint_login",
                        "message": "유세인트 로그인 중...",
                    }
                    await usaint_login(session, usaint_id, usaint_password)
                    print(f"[AgentService] 유세인트 로그인 완료: {session_id}")

            # LangGraph 설정
            config = {"recursion_limit": 25, "configurable": {"thread_id": session_id}}

            # 스트리밍 실행
            try:
                async for event in self.graph.astream(
                    {
                        "session_id": session_id,
                        "messages": [
                            ("user", message)
                        ],  # 시스템 메시지는 그래프 내부에서 관리
                    },
                    config=config,
                ):
                    for value in event.values():
                        if "messages" in value and value["messages"]:
                            last_message = value["messages"][-1]

                            # AIMessage이면서 tool_calls가 있는 경우 (툴 호출)
                            if (
                                isinstance(last_message, AIMessage)
                                and hasattr(last_message, "tool_calls")
                                and last_message.tool_calls
                            ):
                                for tool_call in last_message.tool_calls:
                                    # tool_call은 딕셔너리 또는 객체일 수 있음
                                    if isinstance(tool_call, dict):
                                        tool_name = tool_call.get(
                                            "name", "알 수 없는 도구"
                                        )
                                        tool_args = tool_call.get("args", {})
                                    else:
                                        # 객체인 경우 속성으로 접근
                                        tool_name = getattr(
                                            tool_call, "name", "알 수 없는 도구"
                                        )
                                        tool_args = getattr(tool_call, "args", {})

                                    # 툴 인자를 기반으로 구체적인 메시지 생성
                                    tool_message = self._generate_tool_message(
                                        tool_name, tool_args
                                    )

                                    # 디버깅용 로그
                                    print(
                                        f"[AgentService] 툴 호출: {tool_name}, 인자: {tool_args}"
                                    )

                                    yield {
                                        "type": "tool_start",
                                        "tool_name": tool_name,
                                        "message": tool_message,
                                    }

                            # AIMessage이면서 content가 있는 경우 (최종 응답)
                            elif (
                                isinstance(last_message, AIMessage)
                                and last_message.content
                            ):
                                yield {
                                    "type": "agent_message",
                                    "content": last_message.content,
                                }

                            # ToolMessage는 무시 (내부 처리용)

            except Exception as stream_error:
                # 스트리밍 중 에러 발생 시 메모리 상태 정리
                error_msg = str(stream_error)
                print(f"[AgentService] 스트리밍 오류 발생: {error_msg}")

                # OpenAI API 400 에러 (tool_calls 관련 에러)인 경우 메모리 초기화
                if "400" in error_msg or "tool_call" in error_msg.lower():
                    print(f"[AgentService] tool_calls 에러 감지, 메모리 초기화 시도")
                    self.clear_memory(chat_room_id)

                    # 사용자에게 알림
                    yield {
                        "type": "error",
                        "message": "대화 기록에 문제가 발생하여 초기화했습니다. 다시 시도해주세요.",
                    }
                else:
                    # 다른 에러는 그대로 전달
                    yield {
                        "type": "error",
                        "message": f"오류가 발생했습니다: {error_msg}",
                    }

                # 에러를 yield로 전달했으므로 raise하지 않음
                return

        except Exception as e:
            print(f"[AgentService] 메시지 처리 중 오류: {e}")
            import traceback

            traceback.print_exc()
            yield {"type": "error", "message": f"오류가 발생했습니다: {str(e)}"}

    # 스케줄러가 호출할 성적 데이터 가져오기
    async def get_grades_data(
        self, chat_room_id: int, user_id: int
    ) -> Optional[str]:
        """
        [스케줄러 전용] 유세인트 성적 데이터를 가져옵니다.
        """
        print(f"[AgentService] 스케줄러 작업: 성적 데이터 조회 (User: {user_id})")
        db = next(get_db())
        try:
            # DB에서 유세인트 ID/PW 가져오기
            usaint_account = get_usaint_account_by_user_id(db, user_id)
            usaint_id = usaint_account.id
            usaint_pw = decrypt_password(usaint_account.password)

            # 세션 가져오기
            session = await self._get_or_create_session(chat_room_id, usaint_id, usaint_pw)
            if not session:
                raise Exception("세션 생성 또는 로그인에 실패했습니다.")

            # 세션 id 문자열 가져오기
            session_id_str = self._get_session_id(chat_room_id)

            # 전체 성적 데이터 추출
            key_data = await fetch_full_grades(session, session_id_str)
            return key_data

        except Exception as e:
            print(f"[AgentService] 성적 조회 작업 중 오류: {e}")
            return None
        finally:
             db.close()

    # 스케줄러가 호출할 학식 메뉴 데이터 가져오기
    async def get_cafeteria_data(
        self, chat_room_id: int, user_id: int, restaurant_code: int
    ) -> Optional[str]:
        """
        [스케줄러 전용] 학식 메뉴 데이터를 가져옵니다.
        restaurant_code는 스케줄 DB에 저장된 값을 사용합니다.
        """
        from apps.agent.cafeteria import fetch_cafeteria_menu_data
        from datetime import datetime

        print(f"[AgentService] 스케줄러 작업: 학식 메뉴 조회 (User: {user_id}, Restaurant: {restaurant_code})")

        try:
            # 오늘 날짜 YYYYMMDD 형식으로
            today = datetime.now().strftime("%Y%m%d")

            # 학식 메뉴 데이터 가져오기
            menu_data = fetch_cafeteria_menu_data(restaurant_code, today)

            if not menu_data or not menu_data.get("menus"):
                print(f"[AgentService] 학식 메뉴를 찾지 못했습니다.")
                return None

            # 메뉴 정보를 문자열로 변환
            menu_str = f"{menu_data['restaurant_name']} ({menu_data['date']})\n"
            for menu in menu_data["menus"]:
                menu_str += f"- {menu['category']}: {menu['main_dish']}\n"

            return menu_str.strip()

        except Exception as e:
            print(f"[AgentService] 학식 메뉴 조회 중 오류: {e}")
            return None

    # 스케줄러가 호출할 장학금 공지사항 데이터 가져오기
    async def get_scholarship_notice_data(
        self, chat_room_id: int, user_id: int
    ) -> Optional[str]:
        """
        [스케줄러 전용] 장학금 공지사항 데이터를 가져옵니다.
        """
        import requests
        from bs4 import BeautifulSoup

        print(f"[AgentService] 스케줄러 작업: 장학금 공지사항 조회 (User: {user_id})")

        try:
            # 스캐치 공지사항 페이지에서 최신 장학금 공지 찾기
            url = "https://scatch.ssu.ac.kr/공지사항/page/1"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            # HTML 파싱
            soup = BeautifulSoup(response.text, "html.parser")

            # notice-lists 클래스를 가진 ul 요소 찾기
            notice_lists = soup.find("ul", class_="notice-lists")

            if not notice_lists:
                print(f"[AgentService] 공지사항 목록을 찾을 수 없습니다.")
                return None

            # 모든 li 요소 찾기
            list_items = notice_lists.find_all("li")

            scholarship_notices = []
            for li in list_items:
                # 헤더 행은 건너뛰기
                if "notice_head" in li.get("class", []):
                    continue

                # 제목과 카테고리 추출
                title_col = li.find("div", class_="notice_col3")
                if not title_col:
                    continue

                title_link = title_col.find("a")
                if not title_link:
                    continue

                title_text = title_link.get_text(strip=True)

                # 장학 관련 공지만 필터링
                if "장학" in title_text:
                    date_col = li.find("div", class_="notice_col1")
                    date = date_col.get_text(strip=True) if date_col else ""

                    scholarship_notices.append({
                        "title": title_text,
                        "date": date,
                        "url": title_link.get("href", "")
                    })

            if not scholarship_notices:
                print(f"[AgentService] 장학금 공지를 찾지 못했습니다.")
                return None

            # 최신 장학금 공지의 제목 반환 (변경 감지용)
            latest_notice = scholarship_notices[0]
            notice_summary = f"{latest_notice['title']} ({latest_notice['date']})"

            print(f"[AgentService] 최신 장학금 공지: {notice_summary}")
            return notice_summary

        except Exception as e:
            print(f"[AgentService] 장학금 공지 조회 중 오류: {e}")
            return None

    async def _get_or_create_session(
        self, chat_room_id: int, usaint_id: str, usaint_pw: str
    ):
        """[스케줄러 전용] 세션을 가져오거나, 없으면 생성하고 로그인합니다."""
        if not self.playwright:
            await self.initialize()

        session_id = self._get_session_id(chat_room_id)
        session = session_manager.get_session(session_id)
        session.update_activity() # 세션 자동 종료 방지

        # 세션이 없거나, 페이지가 닫혔으면 새로 시작
        if session.page is None or session.page.is_closed():
            print(f"[AgentService] 스케줄러용 세션이 없어 새로 시작합니다: {session_id}")
            await session.start(self.playwright)
            await usaint_login(session, usaint_id, usaint_pw)
            print(f"[AgentService] 스케줄러용 로그인 완료: {session_id}")
        
        return session

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


def get_agent_data_function(task_type: str):
    """
    [스케줄러 전용] task_type 문자열을 실제 agent_service 함수 객체로 매핑합니다.
    """
    if task_type == "GRADE_CHECK":
        return agent_service.get_grades_data
    elif task_type == "CAFETERIA_CHECK":
        return agent_service.get_cafeteria_data
    elif task_type == "SCHOLARSHIP_CHECK":
        return agent_service.get_scholarship_notice_data

    return None # 매핑되는 함수가 없으면 None 반환

# 전역 싱글톤 인스턴스
agent_service = AgentService()
