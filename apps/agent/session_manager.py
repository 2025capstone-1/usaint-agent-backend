import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional

from playwright.async_api import Playwright, async_playwright

from apps.agent.session import Session


class SessionManager:
    """사용자별 브라우저 세션을 관리하는 매니저"""

    def __init__(self, session_timeout_minutes: int = 30):
        self.sessions: Dict[int, Session] = {}  # user_id -> Session
        self.last_activity: Dict[int, datetime] = {}  # user_id -> last_activity_time
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.playwright: Optional[Playwright] = None
        self._cleanup_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Playwright 초기화 및 세션 정리 태스크 시작"""
        if not self.playwright:
            self.playwright = await async_playwright().start()
            # 주기적으로 타임아웃된 세션 정리 (5분마다)
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def shutdown(self):
        """모든 세션 종료 및 Playwright 정리"""
        # 정리 태스크 종료
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # 모든 세션 종료
        for user_id in list(self.sessions.keys()):
            await self.close_session(user_id)

        # Playwright 종료
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

    async def get_or_create_session(self, user_id: int) -> Session:
        """사용자 세션 조회 또는 생성"""
        # Playwright가 초기화되지 않았다면 초기화
        if not self.playwright:
            await self.initialize()

        # 기존 세션이 있으면 활동 시간 업데이트 후 반환
        if user_id in self.sessions:
            self.last_activity[user_id] = datetime.now()
            return self.sessions[user_id]

        # 새 세션 생성
        session = Session()
        await session.start(self.playwright)
        self.sessions[user_id] = session
        self.last_activity[user_id] = datetime.now()

        print(f"[SessionManager] 사용자 {user_id}의 새 세션 생성: {session.id}")
        return session

    async def close_session(self, user_id: int):
        """특정 사용자의 세션 종료"""
        if user_id in self.sessions:
            session = self.sessions[user_id]
            await session.close()
            del self.sessions[user_id]
            del self.last_activity[user_id]
            print(f"[SessionManager] 사용자 {user_id}의 세션 종료: {session.id}")

    async def _cleanup_loop(self):
        """타임아웃된 세션을 주기적으로 정리"""
        while True:
            try:
                await asyncio.sleep(300)  # 5분마다 실행
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[SessionManager] 세션 정리 중 오류: {e}")

    async def _cleanup_expired_sessions(self):
        """타임아웃된 세션 정리"""
        now = datetime.now()
        expired_users = []

        for user_id, last_activity in self.last_activity.items():
            if now - last_activity > self.session_timeout:
                expired_users.append(user_id)

        for user_id in expired_users:
            print(f"[SessionManager] 타임아웃으로 인한 세션 종료: 사용자 {user_id}")
            await self.close_session(user_id)

    def get_active_session_count(self) -> int:
        """활성 세션 수 반환"""
        return len(self.sessions)


# 전역 싱글톤 인스턴스
session_manager = SessionManager(session_timeout_minutes=30)
