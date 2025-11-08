from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from apps.agent import browser
from apps.agent.session_manager import session_manager


class AgentService:
    """FastAPI에서 호출 가능한 에이전트 서비스"""

    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    async def process_message(self, user_id: int, message: str) -> str:
        """
        사용자 메시지를 처리하고 에이전트 응답을 반환합니다.

        Args:
            user_id: 사용자 ID (세션 식별에 사용)
            message: 사용자 메시지

        Returns:
            에이전트의 응답 텍스트
        """
        try:
            # 사용자별 세션 조회/생성
            session = await session_manager.get_or_create_session(user_id)

            # 브라우저 도구 생성 (세션별로)
            tools = browser.get_browser_tools(session)

            # langchain 1.0의 create_agent 사용
            agent_executor = create_agent(
                model=self.llm,
                tools=tools,
            )

            # 에이전트 실행
            result = await agent_executor.ainvoke({"messages": [("user", message)]})

            # 결과 추출 (langgraph는 messages 리스트 반환)
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
        await session_manager.close_session(user_id)


# 전역 싱글톤 인스턴스
agent_service = AgentService()
