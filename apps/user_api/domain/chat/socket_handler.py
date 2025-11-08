"""
Socket.io 이벤트 핸들러
"""

import jwt
from jwt.exceptions import InvalidTokenError
from socketio import AsyncServer
from sqlalchemy.orm import Session

from apps.agent.agent_service import agent_service
from apps.user_api.domain.auth.exception import NotAuthenticated
from apps.user_api.domain.auth.service import JWT_ALGORITHM, JWT_SECRET
from apps.user_api.domain.chat.dto.response import ChatResponse
from apps.user_api.domain.chat.service import create_chat, get_chats_by_room_id
from apps.user_api.domain.chat_room.service import get_chat_room_by_id
from lib.database import get_db


def verify_token(token: str) -> int:
    """JWT 토큰을 검증하고 user_id를 반환합니다."""
    try:
        payload: dict = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("id")
        authority = payload.get("authority")

        if user_id is None or authority != "ROLE_USER":
            raise NotAuthenticated()

        return user_id
    except InvalidTokenError:
        raise NotAuthenticated()


def register_socket_handlers(sio: AsyncServer):
    """Socket.io 이벤트 핸들러 등록"""

    @sio.event
    async def connect(sid, environ, auth):
        """클라이언트 연결 이벤트"""
        try:
            # 토큰 검증 (auth 딕셔너리에서 token 추출)
            token = auth.get("token") if auth else None
            if not token:
                print(f"[Socket.io] 연결 거부: 토큰 없음 (sid={sid})")
                return False

            # JWT 검증
            user_id = verify_token(token)

            # 세션에 user_id 저장
            async with sio.session(sid) as session:
                session["user_id"] = user_id

            print(f"[Socket.io] 사용자 연결: user_id={user_id}, sid={sid}")
            return True

        except NotAuthenticated:
            print(f"[Socket.io] 연결 거부: 인증 실패 (sid={sid})")
            return False
        except Exception as e:
            print(f"[Socket.io] 연결 오류: {e} (sid={sid})")
            return False

    @sio.event
    async def disconnect(sid):
        """클라이언트 연결 해제 이벤트"""
        try:
            async with sio.session(sid) as session:
                user_id = session.get("user_id")
            print(f"[Socket.io] 사용자 연결 해제: user_id={user_id}, sid={sid}")
        except Exception as e:
            print(f"[Socket.io] 연결 해제 오류: {e} (sid={sid})")

    @sio.event
    async def join_room(sid, data):
        """채팅방 입장 이벤트"""
        try:
            chat_room_id = data.get("chat_room_id")
            if not chat_room_id:
                await sio.emit("error", {"message": "chat_room_id가 필요합니다."}, room=sid)
                return

            # 세션에서 user_id 가져오기
            async with sio.session(sid) as session:
                user_id = session.get("user_id")

            if not user_id:
                await sio.emit("error", {"message": "인증되지 않은 사용자입니다."}, room=sid)
                return

            # 채팅방 존재 여부 및 소유권 확인
            db: Session = next(get_db())
            try:
                chat_room = get_chat_room_by_id(db, user_id, chat_room_id)

                # Socket.io room에 입장
                await sio.enter_room(sid, f"chat_room_{chat_room_id}")

                await sio.emit(
                    "joined_room",
                    {"chat_room_id": chat_room_id, "message": "채팅방에 입장했습니다."},
                    room=sid,
                )
                print(f"[Socket.io] 사용자 {user_id}가 채팅방 {chat_room_id}에 입장")
            finally:
                db.close()

        except Exception as e:
            await sio.emit("error", {"message": str(e)}, room=sid)
            print(f"[Socket.io] join_room 오류: {e} (sid={sid})")

    @sio.event
    async def leave_room(sid, data):
        """채팅방 퇴장 이벤트"""
        try:
            chat_room_id = data.get("chat_room_id")
            if not chat_room_id:
                await sio.emit("error", {"message": "chat_room_id가 필요합니다."}, room=sid)
                return

            # Socket.io room에서 퇴장
            await sio.leave_room(sid, f"chat_room_{chat_room_id}")

            await sio.emit(
                "left_room",
                {"chat_room_id": chat_room_id, "message": "채팅방에서 퇴장했습니다."},
                room=sid,
            )

            async with sio.session(sid) as session:
                user_id = session.get("user_id")
            print(f"[Socket.io] 사용자 {user_id}가 채팅방 {chat_room_id}에서 퇴장")

        except Exception as e:
            await sio.emit("error", {"message": str(e)}, room=sid)
            print(f"[Socket.io] leave_room 오류: {e} (sid={sid})")

    @sio.event
    async def send_message(sid, data):
        """메시지 전송 이벤트"""
        try:
            chat_room_id = data.get("chat_room_id")
            content = data.get("content")

            if not chat_room_id or not content:
                await sio.emit(
                    "error",
                    {"message": "chat_room_id와 content가 필요합니다."},
                    room=sid,
                )
                return

            # 세션에서 user_id 가져오기
            async with sio.session(sid) as session:
                user_id = session.get("user_id")

            if not user_id:
                await sio.emit("error", {"message": "인증되지 않은 사용자입니다."}, room=sid)
                return

            db: Session = next(get_db())
            try:
                # 1. 사용자 메시지 저장
                user_chat = create_chat(
                    db=db,
                    user_id=user_id,
                    chat_room_id=chat_room_id,
                    content=content,
                    sender="user",
                )
                db.commit()
                db.refresh(user_chat)

                # 사용자 메시지 전송
                user_chat_response = ChatResponse.from_entity(user_chat)
                await sio.emit(
                    "receive_message",
                    user_chat_response.model_dump(mode="json"),
                    room=sid,
                )

                # 2. 에이전트 호출
                agent_response_content = await agent_service.process_message(
                    user_id=user_id, message=content
                )

                # 3. 에이전트 응답 저장
                agent_chat = create_chat(
                    db=db,
                    user_id=user_id,
                    chat_room_id=chat_room_id,
                    content=agent_response_content,
                    sender="agent",
                )
                db.commit()
                db.refresh(agent_chat)

                # 에이전트 응답 전송
                agent_chat_response = ChatResponse.from_entity(agent_chat)
                await sio.emit(
                    "receive_message",
                    agent_chat_response.model_dump(mode="json"),
                    room=sid,
                )

                print(
                    f"[Socket.io] 메시지 처리 완료: user_id={user_id}, chat_room_id={chat_room_id}"
                )

            finally:
                db.close()

        except Exception as e:
            await sio.emit("error", {"message": f"메시지 처리 중 오류: {str(e)}"}, room=sid)
            print(f"[Socket.io] send_message 오류: {e} (sid={sid})")
