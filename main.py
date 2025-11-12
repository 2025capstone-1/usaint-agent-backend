from contextlib import asynccontextmanager
import asyncio

import socketio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import apps.user_api.domain.auth.controller as AuthRouter
import apps.user_api.domain.chat.controller as ChatRouter
import apps.user_api.domain.chat_room.controller as ChatRoomRouter
import apps.user_api.domain.schedule.controller as ScheduleRouter
import apps.user_api.domain.usaint_account.controller as UsaintAccountRouter
import apps.user_api.domain.user.controller as UserRouter
from apps.agent.agent_service import agent_service
from apps.agent.session import session_manager
from apps.user_api.domain.chat.socket_handler import register_socket_handlers
from apps.user_api.domain.schedule.service import check_and_run_due_schedules
from lib.database import Base, engine

scheduler = AsyncIOScheduler(timezone="Asia/Seoul")


async def cleanup_inactive_sessions_job():
    """비활성 세션을 정리하는 스케줄러 작업 (비동기 래퍼)"""
    try:
        print(f"clean up inactive session job!")
        await session_manager.cleanup_inactive_sessions(timeout_seconds=60)
    except Exception as e:
        print(f"[Scheduler] 세션 정리 작업 중 오류: {e}")

async def check_and_run_due_schedules_job():
    """스케줄러 작업을 위한 비동기 래퍼"""
    try:
        print(f"Running scheduled job: check_and_run_due_schedules...")
        await check_and_run_due_schedules()
    except Exception as e:
        print(f"[Scheduler] 스케줄 작업 중 오류: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 시작 시 실행할 코드
    # 1. 스케줄러 시작
    scheduler.add_job(
        check_and_run_due_schedules_job, "interval", minutes=1, id="main_scheduler_job",coalesce=True, max_instances=1,
    )
    scheduler.add_job(
        cleanup_inactive_sessions_job,
        "interval",
        minutes=1,  # 2분마다 실행 (충분한 실행 시간 확보)
        id="session_cleanup_job",
        coalesce=True,  # 밀린 작업은 한 번만 실행
        max_instances=1,  # 동시 실행 인스턴스 1개로 제한
    )
    scheduler.start()
    print("스케줄러가 시작되었습니다.")

    # 2. AgentService 초기화
    await agent_service.initialize()
    print("AgentService가 초기화되었습니다.")

    yield  # yield 이후의 코드는 앱 종료 시 실행됨

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
