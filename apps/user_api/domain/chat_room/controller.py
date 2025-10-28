from typing import Annotated, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from apps.user_api.domain.auth.dto.token import TokenPayload
from apps.user_api.domain.auth.service import get_current_user
from apps.user_api.domain.chat_room.dto.response import ChatRoomResponse
from apps.user_api.domain.chat_room import service
from lib.database import get_db

router = APIRouter()
router_tag = ["ChatRoom API"]

@router.post("/", tags=router_tag, status_code=status.HTTP_201_CREATED, response_model=ChatRoomResponse)
async def create_chat_room(
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """새로운 채팅방을 생성합니다."""
    new_chat_room = service.create_chat_room(db, current_user.id, summary="New Chat")
    return ChatRoomResponse.from_entity(new_chat_room)

@router.get("/", tags=router_tag, response_model=List[ChatRoomResponse])
async def get_my_chat_rooms(
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """현재 로그인된 사용자의 모든 채팅방 목록을 조회합니다."""
    chat_rooms = service.get_chat_rooms_by_user_id(db, current_user.id)
    return [ChatRoomResponse.from_entity(room) for room in chat_rooms]

@router.get("/{chat_room_id}", tags=router_tag, response_model=ChatRoomResponse)
async def get_chat_room_details(
    chat_room_id: int,
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """특정 채팅방의 상세 정보를 조회합니다."""
    chat_room = service.get_chat_room_by_id(db, current_user.id, chat_room_id)
    return ChatRoomResponse.from_entity(chat_room)

@router.delete("/{chat_room_id}", tags=router_tag, status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_room(
    chat_room_id: int,
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """특정 채팅방을 삭제합니다."""
    service.delete_chat_room(db, current_user.id, chat_room_id)
    return