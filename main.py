from contextlib import asynccontextmanager

import socketio
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import apps.user_api.domain.auth.controller as AuthRouter
import apps.user_api.domain.chat.controller as ChatRouter
import apps.user_api.domain.chat_room.controller as ChatRoomRouter
import apps.user_api.domain.schedule.controller as ScheduleRouter
import apps.user_api.domain.usaint_account.controller as UsaintAccountRouter
import apps.user_api.domain.user.controller as UserRouter
from apps.agent.agent_service import agent_service
from apps.user_api.domain.chat.socket_handler import register_socket_handlers
from apps.user_api.domain.schedule.service import check_and_run_due_schedules
from lib.database import Base, engine

scheduler = BackgroundScheduler(timezone='Asia/Seoul')

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 시작 시 실행할 코드
    # 1. 스케줄러 시작
    scheduler.add_job(check_and_run_due_schedules, 'interval', minutes=1, id="main_scheduler_job")
    scheduler.start()
    print("스케줄러가 시작되었습니다.")

    # 2. AgentService 초기화
    await agent_service.initialize()
    print("AgentService가 초기화되었습니다.")

    yield # yield 이후의 코드는 앱 종료 시 실행됨

    # 앱 종료 시 실행할 코드
    # 1. 스케줄러 종료
    scheduler.shutdown()
    print("스케줄러가 종료되었습니다.")

    # 2. AgentService 종료
    await agent_service.shutdown()
    print("AgentService가 종료되었습니다.")

# FastAPI 앱을 생성할 때 lifespan을 등록.
app = FastAPI(lifespan=lifespan)

# CORS 설정 - 모든 출처 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 출처 허용
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

app.include_router(AuthRouter.router, prefix="/auth")
app.include_router(ChatRouter.router, prefix="/chat")
app.include_router(ChatRoomRouter.router, prefix="/chat-room")
app.include_router(ScheduleRouter.router, prefix="/schedule")
app.include_router(UsaintAccountRouter.router, prefix="/usaint-account")
app.include_router(UserRouter.router, prefix="/user")

# Socket.io 서버 생성
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",  # CORS 허용 (프로덕션에서는 특정 도메인만 허용)
    logger=True,
    engineio_logger=True,
)

# Socket.io 이벤트 핸들러 등록
register_socket_handlers(sio)

# Socket.io를 FastAPI와 통합
# IMPORTANT: uvicorn 실행 시 "uvicorn main:app" 명령 사용
# Socket.io가 통합된 최종 앱을 app 변수에 할당
app = socketio.ASGIApp(sio, other_asgi_app=app)

# initial table creation
Base.metadata.create_all(bind=engine)