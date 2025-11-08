"""
CLI 기반 에이전트 실행 스크립트

FastAPI 통합 버전은 apps.agent.agent_service를 사용하세요.
"""

import asyncio

import lib.env
from apps.agent.agent_service import agent_service
from apps.agent.session_manager import session_manager


async def main():
    """CLI 모드로 에이전트 실행"""
    print("=" * 50)
    print("에이전트 CLI 모드")
    print("종료하려면 'exit' 또는 'quit'를 입력하세요.")
    print("=" * 50)

    # SessionManager 초기화
    await session_manager.initialize()

    # 테스트용 사용자 ID (CLI 모드에서는 고정값 사용)
    test_user_id = 0

    try:
        while True:
            user_input = input("\n입력: ").strip()

            if user_input.lower() in ["exit", "quit"]:
                print("에이전트를 종료합니다.")
                break

            if not user_input:
                continue

            # AgentService를 통해 메시지 처리
            response = await agent_service.process_message(test_user_id, user_input)
            print(f"\n응답: {response}")

    finally:
        # 세션 정리
        await session_manager.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
