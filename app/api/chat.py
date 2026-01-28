from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import json
import logging

logger = logging.getLogger(__name__)

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
    logger.info(f"🔵 [CHAT] Received message: {request.message[:50]}... from session: {request.session_id}")
    redis = get_redis()
    
    try:
        logger.info(f"📥 [STATE] Loading state for session: {request.session_id}")
        state = await _load_state(redis, request.session_id)
        logger.info(f"✅ [STATE] State loaded - Intent: {state.intent}, Banking Type: {state.banking_type}")
        
        state.conversation_history.append({
            "role": "user",
            "content": request.message
        })
        logger.info(f"📝 [HISTORY] Added user message to conversation history")
        
        state_dict = state.model_dump()
        
        try:
            logger.info(f"🚀 [GRAPH] Invoking ConversationManagerGraph...")
            result_dict = compiled_graph.invoke(state_dict)
            logger.info(f"✅ [GRAPH] Graph execution completed")
            
            if isinstance(result_dict, ConversationState):
                result_state = result_dict
            else:
                result_state = ConversationState(**result_dict)
            
            logger.info(f"📊 [RESULT] Response: {result_state.response[:50] if result_state.response else 'Empty'}")
        except Exception as graph_error:
            logger.error(f"❌ [GRAPH] Graph execution error: {type(graph_error).__name__}: {str(graph_error)}", exc_info=True)
            return ChatResponse(
                response=f"Error processing your request: {str(graph_error)}",
                session_id=request.session_id,
                intent=state.intent,
                domain=state.banking_type
            )
        
        response_text = result_state.response or "I can help with banking. What do you need?"
        
        result_state.conversation_history.append({
            "role": "assistant",
            "content": response_text
        })
        logger.info(f"📝 [HISTORY] Added assistant response to conversation history")
        
        logger.info(f"💾 [SAVE] Saving state to Redis for session: {request.session_id}")
        await _save_state(redis, request.session_id, result_state)
        logger.info(f"✅ [SAVE] State saved successfully")
        
        logger.info(f"🟢 [CHAT] Sending response to client")
        return ChatResponse(
            response=response_text,
            session_id=request.session_id,
            intent=result_state.intent,
            domain=result_state.banking_type
        )
        
    except Exception as e:
        logger.error(f"❌ [CHAT] Chat endpoint error: {type(e).__name__}: {str(e)}", exc_info=True)
        return ChatResponse(
            response=f"An error occurred: {str(e)}",
            session_id=request.session_id,
            intent=None,
            domain=None
        )


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
