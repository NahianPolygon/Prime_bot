from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import json

from app.core.redis import get_redis
from app.core.graphs.conversation_manager import ConversationManagerGraph
from app.models.conversation_state import ConversationState, UserProfile

router = APIRouter()
conversation_graph = ConversationManagerGraph()
compiled_graph = conversation_graph.build_graph()


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    response: str
    session_id: str
    intent: Optional[str] = None
    domain: Optional[str] = None


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    redis = get_redis()
    
    try:
        state = await _load_state(redis, request.session_id)
        
        state.conversation_history.append({
            "role": "user",
            "content": request.message
        })
        
        
        state_dict = state.model_dump()
        result_dict = await compiled_graph.ainvoke(state_dict)
        result_state = ConversationState(**result_dict)
        
        response_text = result_state.response or "I can help with banking. What do you need?"
        result_state.conversation_history.append({
            "role": "assistant",
            "content": response_text
        })
        
        await _save_state(redis, request.session_id, result_state)
        
        return ChatResponse(
            response=response_text,
            session_id=request.session_id,
            intent=result_state.intent,
            domain=result_state.banking_type
        )
        
    except Exception as e:
        raise


async def _load_state(redis, session_id: str) -> ConversationState:
    state_dict = None
    
    if redis:
        try:
            state_data = await redis.get(f"state:{session_id}")
            if state_data:
                state_dict = json.loads(state_data)
        except Exception:
            pass
    
    if state_dict:
        return ConversationState(**state_dict)
    
    return ConversationState(
        session_id=session_id,
        user_profile=UserProfile()
    )


async def _save_state(redis, session_id: str, state: ConversationState) -> None:
    if redis:
        try:
            state_data = {
                "session_id": state.session_id,
                "intent": state.intent,
                "banking_type": state.banking_type,
                "product_category": state.product_category,
                "product_type": state.product_type,
                "product_name": state.product_name,
                "user_profile": state.user_profile.model_dump(),
                "conversation_history": state.conversation_history,
                "response": state.response
            }
            await redis.set(
                f"state:{session_id}",
                json.dumps(state_data),
                ex=86400
            )
        except Exception:
            pass
