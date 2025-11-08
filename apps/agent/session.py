from os import getcwd
from pathlib import Path
from time import time
from typing import Dict, Optional
import threading
import asyncio

from playwright.async_api import BrowserContext, Page, Playwright


class Session:

    def __init__(self, session_id: str):
        self.id = session_id
        self.user_data_dir = Path(f"{getcwd()}/sessions/{self.id}")  # 세션별 디렉토리
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self.save_path = Path.joinpath(self.user_data_dir, "state.json")

        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.last_activity_time: float = time()  # 마지막 활동 시간

    async def start(self, playwright: Playwright):
        self.context = await playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=False,
            args=[
                "--disable-web-security",
                "--disable-features=IsolateOrigins,SitePerProcess",
            ],
        )

        self.page = (
            self.context.pages[0]
            if self.context.pages
            else await self.context.new_page()
        )

    def update_activity(self):
        """마지막 활동 시간 업데이트"""
        self.last_activity_time = time()

    def is_inactive(self, timeout_seconds: int) -> bool:
        """세션이 비활성 상태인지 확인"""
        return (time() - self.last_activity_time) > timeout_seconds

    async def close(self):
        if self.context:
            await self.context.close()

        self.page = None


_thread_local = threading.local()


def get_session_for_current_thread(session_id: str):
    """Get or create session for current thread"""
    if not hasattr(_thread_local, "sessions"):
        _thread_local.sessions = {}

    if session_id not in _thread_local.sessions:
        _thread_local.sessions[session_id] = session_manager.get_session(session_id)

    return _thread_local.sessions[session_id]


class SessionManager:
    session_map: Dict[str, Session] = {}

    def __init__(self):
        pass

    def get_session(self, session_id: str):
        if self.session_map.get(session_id) is None:
            new_session = Session(session_id)
            self.session_map[session_id] = new_session

        return self.session_map.get(session_id)

    async def cleanup_inactive_sessions(self, timeout_seconds: int = 300):
        """비활성 세션을 정리합니다. 기본값: 300초(5분)"""
        # 세션이 없으면 빠르게 리턴
        if not self.session_map:
            return

        # 비활성 세션 찾기
        inactive_sessions = [
            (session_id, session)
            for session_id, session in self.session_map.items()
            if session.is_inactive(timeout_seconds)
        ]

        if not inactive_sessions:
            return

        print(f"[SessionManager] {len(inactive_sessions)}개의 비활성 세션 정리 시작")

        # 병렬로 세션 종료 (각 세션마다 5초 타임아웃)
        async def close_session_safe(session_id: str, session):
            try:
                await asyncio.wait_for(session.close(), timeout=5.0)
                del self.session_map[session_id]
                print(f"[SessionManager] 비활성 세션 정리 완료: {session_id}")
            except asyncio.TimeoutError:
                # 타임아웃 발생 시에도 맵에서 제거
                if session_id in self.session_map:
                    del self.session_map[session_id]
                print(f"[SessionManager] 세션 정리 타임아웃 (강제 제거): {session_id}")
            except Exception as e:
                # 에러 발생 시에도 맵에서 제거
                if session_id in self.session_map:
                    del self.session_map[session_id]
                print(f"[SessionManager] 세션 정리 중 오류 (강제 제거): {session_id} - {e}")

        # 모든 세션을 병렬로 종료
        await asyncio.gather(
            *[close_session_safe(sid, sess) for sid, sess in inactive_sessions],
            return_exceptions=True
        )

        print(f"[SessionManager] 세션 정리 완료")


session_manager = SessionManager()
