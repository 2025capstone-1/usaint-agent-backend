from fastapi import FastAPI

import apps.user_api.domain.auth.controller as AuthRouter
import apps.user_api.domain.chat.controller as ChatRouter
import apps.user_api.domain.chat_room.controller as ChatRoomRouter
import apps.user_api.domain.schedule.controller as ScheduleRouter
import apps.user_api.domain.usaint_account.controller as UsaintAccountRouter
import apps.user_api.domain.user.controller as UserRouter
from lib.database import Base, engine

app = FastAPI()

app.include_router(AuthRouter.router, prefix="/auth")
app.include_router(ChatRouter.router, prefix="/chat")
app.include_router(ChatRoomRouter.router, prefix="/chat-room")
app.include_router(ScheduleRouter.router, prefix="/schedule")
app.include_router(UsaintAccountRouter.router, prefix="/usaint-account")
app.include_router(UserRouter.router, prefix="/user")

# initial table creation
Base.metadata.create_all(bind=engine)
