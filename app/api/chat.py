from fastapi import APIRouter
from typing import Optional
import json
import logging

logger = logging.getLogger(__name__)

from app.core.redis import get_redis
from app.core.graphs.conversation_manager import ConversationManagerGraph
from app.models.conversation_state import ConversationState, UserProfile
from app.models.api.schemas import ChatRequest, ChatResponse

router = APIRouter()
conversation_graph = ConversationManagerGraph()
compiled_graph = conversation_graph.build_graph()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    logger.info(f"🔵 [CHAT] Received message: {request.message[:50]}... from session: {request.session_id}")
    redis = get_redis()
    
    try:
        logger.info(f"📥 [STATE] Loading state for session: {request.session_id}")
        state = await _load_state(redis, request.session_id)
        logger.info(f"✅ [STATE] State loaded - Intent: {state.intent}, Banking Type: {state.banking_type}, Product Type In Progress: {state.product_type_in_progress}")
        
        state.conversation_history.append({
            "role": "user",
            "content": request.message
        })
        logger.info(f"📝 [HISTORY] Added user message to conversation history")
        
        state_dict = state.model_dump()
        
        try:
            logger.info(f"🚀 [GRAPH] Invoking ConversationManagerGraph...")
            
            result_obj = compiled_graph.invoke(state)
            logger.info(f"✅ [GRAPH] Graph execution completed")
            logger.info(f"🔍 [GRAPH] Result type: {type(result_obj).__name__}")
            
            
            if isinstance(result_obj, ConversationState):
                result_state = result_obj
            elif isinstance(result_obj, dict):
                logger.info(f"🔍 [GRAPH] Result dict banking_type: {result_obj.get('banking_type')}")
                
                logger.info(f"🔍 [MERGE] Before merge: state has banking_type={state_dict.get('banking_type')}, result has={result_obj.get('banking_type')}")
                merged_dict = {**state_dict, **result_obj}
                logger.info(f"🔍 [MERGE] After merge: merged has banking_type={merged_dict.get('banking_type')}")
                result_state = ConversationState(**merged_dict)
                logger.info(f"🔍 [MERGE] After ConversationState creation: banking_type={result_state.banking_type}")
            else:
                
                if hasattr(result_obj, 'model_dump'):
                    merged_dict = {**state_dict, **result_obj.model_dump()}
                else:
                    merged_dict = {**state_dict, **dict(result_obj)}
                result_state = ConversationState(**merged_dict)
            
            logger.info(f"📊 [RESULT] Response: {result_state.response if result_state.response else 'Empty'}")
            logger.info(f"🔹 [RESULT] Product Type In Progress: {result_state.product_type_in_progress}, Current Slot: {result_state.current_slot}")
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
        logger.info(f"🔍 [SAVE] State.banking_type={result_state.banking_type}, State.gender={result_state.gender}, State.age={result_state.age}, State.remittance_status={result_state.remittance_status}, State.occupation={result_state.occupation}, State.product_type_in_progress={result_state.product_type_in_progress}")
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
                logger.info(f"🔍 [LOAD] comparison_status={state_dict.get('comparison_status')}, comparison_banking_type={state_dict.get('comparison_banking_type')}, remittance_status={state_dict.get('remittance_status')}, product_type_in_progress={state_dict.get('product_type_in_progress')}")
        except Exception as e:
            logger.error(f"❌ [LOAD] Error loading state: {e}")
            pass
    
    if state_dict:
        state = ConversationState(**state_dict)
        logger.info(f"🔍 [LOAD] Loaded state: comparison_status={state.comparison_status}")
        return state
    
    return ConversationState(
        session_id=session_id,
        user_profile=UserProfile()
    )


async def _save_state(redis, session_id: str, state: ConversationState) -> None:
    if redis:
        try:
            state_data = {
                "session_id": state.session_id,
                "inquiry_type": state.inquiry_type,
                "inquiry_confidence": state.inquiry_confidence,
                "extracted_context": state.extracted_context,
                "matched_products": state.matched_products,
                "suggested_products": state.suggested_products,
                "comparison_products": state.comparison_products,
                "intent": state.intent,
                "banking_type": state.banking_type,
                "product_category": state.product_category,
                "product_type": state.product_type,
                "product_name": state.product_name,
                "account_goal": state.account_goal,
                "account_purpose": state.account_purpose,
                "account_type_preference": state.account_type_preference,
                "age": state.age,
                "gender": state.gender,
                "remittance_status": state.remittance_status,
                "occupation": state.occupation,
                "health_benefits_interest": state.health_benefits_interest,
                "locker_interest": state.locker_interest,
                "spending_pattern": state.spending_pattern,
                "card_tier_preference": state.card_tier_preference,
                "annual_income": state.annual_income,
                "loan_purpose": state.loan_purpose,
                "amount_needed": state.amount_needed,
                "repayment_period": state.repayment_period,
                "monthly_savings": state.monthly_savings,
                "primary_use": state.primary_use,
                "travel_frequency": state.travel_frequency,
                "credit_tier": state.credit_tier,
                "loan_amount": state.loan_amount,
                "repayment_tenure": state.repayment_tenure,
                "user_profile": state.user_profile.model_dump(),
                "conversation_history": state.conversation_history,
                "response": state.response,
                "missing_slots": state.missing_slots,
                "eligible_products": state.eligible_products,
                "comparison_mode": state.comparison_mode,
                "comparison_status": state.comparison_status,
                "comparison_banking_type": state.comparison_banking_type,
                "comparison_deposit_frequency": state.comparison_deposit_frequency,
                "comparison_tenure_range": state.comparison_tenure_range,
                "comparison_purpose": state.comparison_purpose,
                "comparison_interest_priority": state.comparison_interest_priority,
                "comparison_flexibility_priority": state.comparison_flexibility_priority,
                "comparison_feature_priorities": state.comparison_feature_priorities,
                "comparison_initial_budget": state.comparison_initial_budget,
                "comparison_monthly_budget": state.comparison_monthly_budget,
                "comparison_collected_slots": state.comparison_collected_slots,
                "comparison_slot_to_collect": state.comparison_slot_to_collect,
                "product_type_in_progress": state.product_type_in_progress,
                "current_slot": state.current_slot,
                "next_action": state.next_action,
                "last_agent": state.last_agent
            }
            logger.info(f"🔍 [SAVE] comparison_status={state.comparison_status}, comparison_banking_type={state.comparison_banking_type}, comparison_deposit_frequency={state.comparison_deposit_frequency}")
            await redis.set(
                f"state:{session_id}",
                json.dumps(state_data),
                ex=86400
            )
        except Exception as e:
            logger.error(f"❌ [SAVE] Error saving state: {e}")
            pass
