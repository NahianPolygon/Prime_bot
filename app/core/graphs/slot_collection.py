from langgraph.graph import StateGraph, START, END
from app.core.config import llm
from app.models.conversation_state import ConversationState
from app.models.graphs import SlotExtractionResult, SlotPromptResponse
from app.prompts.slot_collection import SELECT_SLOT_PROMPT, EXTRACT_SLOT_PROMPT, GENERATE_PROMPT
import re
import logging

logger = logging.getLogger(__name__)


class SlotCollectionGraph:
    def __init__(self):
        self.llm = llm

    def select_next_slot_node(self, state: ConversationState) -> dict:
        logger.info(f"🎯 [SLOT_SELECT] Selecting next slot from missing: {state.missing_slots}")
        if not state.missing_slots:
            logger.info(f"✅ [SLOT_SELECT] No missing slots - collection complete")
            return {
                "response": "Perfect! I have all information needed. Let me proceed.",
                "missing_slots": []
            }
        
        try:
            history = "\n".join([
                f"{msg['role']}: {msg['content']}" 
                for msg in state.conversation_history[-3:]
            ])
            profile = state.user_profile.model_dump(exclude_none=True)

            prompt = SELECT_SLOT_PROMPT.format(
                missing_slots=state.missing_slots,
                profile=profile,
                intent=state.intent or "explore",
                history=history
            )
            logger.info(f"📝 [SLOT_SELECT] Calling LLM to select next slot...")

            structured_llm = self.llm.with_structured_output(SlotPromptResponse)
            result = structured_llm.invoke(prompt)
            logger.info(f"✅ [SLOT_SELECT] Selected slot: {result.slot_name}")

            return {
                "response": result.prompt,
                "current_slot": result.slot_name
            }
        except Exception as e:
            logger.error(f"❌ [SLOT_SELECT] Error selecting slot: {str(e)}", exc_info=True)
            current_slot = state.missing_slots[0] if state.missing_slots else "information"
            return {
                "response": f"Could you please provide your {current_slot}?",
                "current_slot": current_slot
            }

    def generate_slot_prompt_node(self, state: ConversationState) -> dict:
        # Response already set in select_next_slot_node, just pass it through
        logger.info(f"📝 [GENERATE_PROMPT] Passing prompt response: {state.response[:50]}...")
        return {"response": state.response}

    def build_graph(self):
        graph = StateGraph(ConversationState)
        
        graph.add_node("select_next_slot", self.select_next_slot_node)
        graph.add_node("generate_prompt", self.generate_slot_prompt_node)
        
        graph.add_edge(START, "select_next_slot")
        graph.add_edge("select_next_slot", "generate_prompt")
        graph.add_edge("generate_prompt", END)
        
        return graph.compile()

    def visualize(self):
        graph = self.build_graph()
        return graph.get_graph().to_dict()

    def invoke(self, state):
        graph = self.build_graph()
        return graph.invoke(state)
