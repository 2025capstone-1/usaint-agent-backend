from typing import Optional

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from playwright.async_api import Playwright, async_playwright

from apps.agent import browser
from apps.agent.rag import search_ssu_notice
from apps.agent.session import session_manager
from apps.agent.usaint import (
    click_in_iframe,
    get_iframe_interactive_element,
    get_iframe_text_content,
    search_menu,
    select_navigation_menu,
    usaint_login,
)


class AgentService:
    """FastAPI에서 호출 가능한 에이전트 서비스"""

    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.playwright: Optional[Playwright] = None

    async def initialize(self):
        """Playwright 초기화"""
        if not self.playwright:
            self.playwright = await async_playwright().start()
            print("[AgentService] Playwright 초기화 완료")

    async def shutdown(self):
        """모든 세션 종료 및 Playwright 정리"""
        # 모든 세션 종료
        for session_id in list(session_manager.session_map.keys()):
            await self.close_user_session_by_id(session_id)

        # Playwright 종료
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
            print("[AgentService] Playwright 종료 완료")

    def _get_session_id(self, user_id: int) -> str:
        """user_id를 session_id로 변환"""
        return f"user_{user_id}"

    async def process_message(self, user_id: int, message: str, usaint_id: str = None, usaint_password: str = None) -> str:
        """
        사용자 메시지를 처리하고 에이전트 응답을 반환합니다.

        Args:
            user_id: 사용자 ID
            message: 사용자 메시지
            usaint_id: 유세인트 ID (선택)
            usaint_password: 유세인트 비밀번호 (선택)

        Returns:
            에이전트의 응답 텍스트
        """
        try:
            # Playwright가 초기화되지 않았다면 초기화
            if not self.playwright:
                await self.initialize()

            # user_id를 session_id로 변환
            session_id = self._get_session_id(user_id)

            # 사용자별 세션 조회/생성
            session = session_manager.get_session(session_id)

            # 세션이 시작되지 않았다면 시작
            if session.page is None:
                await session.start(self.playwright)
                print(f"[AgentService] 사용자 {user_id}의 세션 시작: {session_id}")

                # 유세인트 로그인이 필요한 경우
                if usaint_id and usaint_password:
                    await usaint_login(session, usaint_id, usaint_password)
                    print(f"[AgentService] 유세인트 로그인 완료: {session_id}")

            # 모든 도구 통합
            tools = [
                # RAG 도구
                search_ssu_notice,
                # 유세인트 도구
                search_menu,
                select_navigation_menu,
                get_iframe_text_content,
                get_iframe_interactive_element,
                click_in_iframe,
                # 브라우저 도구 (browser.py의 도구들은 session을 인자로 받으므로 제외)
                # TODO: browser.py의 도구들도 session_id를 받도록 수정하면 추가 가능
            ]

            # langchain 1.0의 create_agent 사용
            agent_executor = create_agent(
                model=self.llm,
                tools=tools,
            )

            # 에이전트 실행 (session_id를 메시지에 포함)
            # tools가 session_id를 필요로 하므로 함께 전달
            result = await agent_executor.ainvoke({
                "messages": [
                    ("system", f"현재 세션 ID는 '{session_id}' 입니다. 도구를 사용할 때 이 session_id를 전달하세요."),
                    ("user", message)
                ]
            })

            # 결과 추출
            messages = result.get("messages", [])
            if messages:
                # 마지막 메시지가 에이전트의 응답
                last_message = messages[-1]
                output = last_message.content if hasattr(last_message, 'content') else str(last_message)
                return output
            else:
                return "응답을 생성할 수 없습니다."

        except Exception as e:
            print(f"[AgentService] 메시지 처리 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return f"오류가 발생했습니다: {str(e)}"

    async def close_user_session(self, user_id: int):
        """특정 사용자의 세션을 종료합니다."""
        session_id = self._get_session_id(user_id)
        await self.close_user_session_by_id(session_id)

    async def close_user_session_by_id(self, session_id: str):
        """session_id로 세션을 종료합니다."""
        if session_id in session_manager.session_map:
            session = session_manager.session_map[session_id]
            await session.close()
            del session_manager.session_map[session_id]
            print(f"[AgentService] 세션 종료: {session_id}")


# 전역 싱글톤 인스턴스
agent_service = AgentService()
