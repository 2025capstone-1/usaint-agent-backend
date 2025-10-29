from sqlalchemy.orm import Session
from apps.user_api.domain.chat_room.entity import ChatRoom
from apps.user_api.domain.chat_room.exception import ChatRoomNotFound
from lib.database import transactional

@transactional
def create_chat_room(db: Session, user_id: int, summary: str = None) -> ChatRoom:
    """새로운 채팅방을 생성합니다."""
    new_chat_room = ChatRoom.create(user_id=user_id, summary=summary)
    db.add(new_chat_room)
    return new_chat_room

def get_chat_rooms_by_user_id(db: Session, user_id: int):
    """사용자의 모든 채팅방 목록을 조회합니다."""
    return db.query(ChatRoom).filter(ChatRoom.user_id == user_id).all()

def get_chat_room_by_id(db: Session, user_id: int, chat_room_id: int) -> ChatRoom:
    """특정 채팅방 정보를 조회합니다."""
    chat_room = db.query(ChatRoom).filter(
        ChatRoom.chat_room_id == chat_room_id,
        ChatRoom.user_id == user_id
    ).first()
    if not chat_room:
        raise ChatRoomNotFound()
    return chat_room

@transactional
def delete_chat_room(db: Session, user_id: int, chat_room_id: int):
    """채팅방을 삭제합니다."""
    chat_room = get_chat_room_by_id(db, user_id, chat_room_id)
    db.delete(chat_room)