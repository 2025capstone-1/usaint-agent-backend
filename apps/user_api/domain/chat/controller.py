from typing import Annotated, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from apps.user_api.domain.auth.dto.token import TokenPayload
from apps.user_api.domain.auth.service import get_current_user
from apps.user_api.domain.chat.dto.request import CreateChatRequest
from apps.user_api.domain.chat.dto.response import ChatResponse
from apps.user_api.domain.chat import service
from lib.database import get_db

router = APIRouter()
router_tag = ["Chat API"]

@router.post("/{chat_room_id}", tags=router_tag, status_code=status.HTTP_201_CREATED, response_model=ChatResponse)
async def create_chat_message(
    chat_room_id: int,
    request: CreateChatRequest,
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """새로운 채팅 메시지를 생성합니다 (사용자 -> 에이전트)."""
    # 사용자 메시지 저장
    user_chat = service.create_chat(
        db, user_id=current_user.id, chat_room_id=chat_room_id, content=request.content, sender="user"
    )

    # TODO: 여기서 LangGraph/LLM을 호출하여 에이전트의 답변을 생성하는 로직이 필요합니다.
    # agent_response_content = call_langchain_agent(request.content)
    agent_response_content = "에이전트의 답변입니다." # 임시 답변

    # 에이전트 답변 저장
    agent_chat = service.create_chat(
        db, user_id=current_user.id, chat_room_id=chat_room_id, content=agent_response_content, sender="agent"
    )

    # 에이전트의 답변을 응답으로 반환
    return ChatResponse.from_entity(agent_chat)

@router.get("/{chat_room_id}", tags=router_tag, response_model=List[ChatResponse])
async def get_chat_history(
    chat_room_id: int,
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    """특정 채팅방의 모든 대화 기록을 조회합니다."""
    chats = service.get_chats_by_room_id(db, current_user.id, chat_room_id)
    return [ChatResponse.from_entity(chat) for chat in chats]