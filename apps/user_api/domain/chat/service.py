from sqlalchemy.orm import Session
from apps.user_api.domain.chat.entity import Chat
from apps.user_api.domain.chat_room.service import get_chat_room_by_id
from lib.database import transactional

@transactional
def create_chat(db: Session, user_id: int, chat_room_id: int, content: str, sender: str) -> Chat:
    """새로운 채팅 메시지를 생성하고 채팅방의 마지막 메시지를 업데이트합니다."""
    # 채팅방 존재 여부 및 소유권 확인
    chat_room = get_chat_room_by_id(db, user_id, chat_room_id)
    
    new_chat = Chat.create(
        chat_room_id=chat_room_id,
        content=content,
        sender=sender,
    )
    db.add(new_chat)
    
    # 채팅방의 last_content 업데이트
    chat_room.last_content = content
    db.add(chat_room)
    
    return new_chat

def get_chats_by_room_id(db: Session, user_id: int, chat_room_id: int):
    """특정 채팅방의 모든 메시지 기록을 조회합니다."""
    # 채팅방 존재 여부 및 소유권 확인
    get_chat_room_by_id(db, user_id, chat_room_id)
    
    return db.query(Chat).filter(Chat.chat_room_id == chat_room_id).order_by(Chat.created_at).all()