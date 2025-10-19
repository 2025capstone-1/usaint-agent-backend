from os import getcwd
from pathlib import Path
from time import time
from typing import Dict, Optional
import threading

from playwright.async_api import BrowserContext, Page, Playwright, Request, Response


class Session:

    def __init__(self, session_id: str):
        self.id = session_id
        self.user_data_dir = Path(f"{getcwd()}/sessions/{self.id}")  # 세션별 디렉토리
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self.save_path = Path.joinpath(self.user_data_dir, "state.json")

        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

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

        # 모든 요청 로깅
        def log_request(request):
            print(">>", request.method, request.url, request.headers)

        # 모든 응답 로깅
        async def log_response(response):
            print("<<", response.status, response.url)

            # HTML/text일 경우
            try:
                text = await response.text()  # str
                print(text[:200])  # 앞 200자만 출력
            except Exception as e:
                print("response.text() error:", e)

            # JSON일 경우
            try:
                data = await response.json()  # dict
                print(data)
            except Exception:
                pass

        # self.page.on("request", log_request)
        # self.page.on("response", log_response)

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


session_manager = SessionManager()
