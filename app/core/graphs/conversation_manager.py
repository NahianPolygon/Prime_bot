from langgraph.graph import StateGraph, END
from typing import Any
from app.models.conversation_state import ConversationState
from app.core.intent_detector import IntentDetector
from app.core.graphs.slot_collection import SlotCollectionGraph
from app.core.graphs.eligibility import EligibilityGraph
from app.core.graphs.product_retrieval import ProductRetrievalGraph
from app.core.graphs.comparison import ComparisonGraph
from app.core.graphs.rag_explanation import RAGExplanationGraph
from app.core.graph_visualizer import save_graph_visualization


class ConversationManagerGraph:
    def __init__(self):
        self.intent_detector = IntentDetector()
        self._graph = None
        self.slot_collection_graph = SlotCollectionGraph()
        self.eligibility_graph = EligibilityGraph()
        self.product_retrieval_graph = ProductRetrievalGraph()
        self.comparison_graph = ComparisonGraph()
        self.rag_explanation_graph = RAGExplanationGraph()

    def parse_message_node(self, state: ConversationState) -> dict:
        message = state.conversation_history[-1]["content"] if state.conversation_history else ""
        return {
            "last_agent": "parse_message"
        }

    async def detect_intent_node(self, state: ConversationState) -> dict:
        message = state.conversation_history[-1]["content"] if state.conversation_history else ""
        
        try:
            intent_result = await self.intent_detector.detect(message)
            intent_type = intent_result.intent_type
            domain = intent_result.domain or state.banking_type
            vertical = intent_result.vertical or state.product_category
        except:
            intent_type = "explore"
            domain = "savings"
            vertical = "deposit"
        
        return {
            "intent": intent_type,
            "banking_type": domain,
            "product_category": vertical,
            "last_agent": "detect_intent"
        }

    def check_missing_slots_node(self, state: ConversationState) -> dict:
        required_slots = []
        
        # Always ask for banking type if not specified
        if not state.banking_type or state.banking_type == "savings":
            # Only ask if it seems ambiguous (e.g., user mentioned Islamic)
            message = state.conversation_history[-1]["content"].lower() if state.conversation_history else ""
            if "islamic" in message or "shariah" in message or "islami" in message or "halal" in message:
                # User specified Islamic, don't ask
                pass
            elif state.banking_type is None:
                required_slots.append("banking_type")
        
        # Always ask for product category if not specified
        if not state.product_category:
            message = state.conversation_history[-1]["content"].lower() if state.conversation_history else ""
            if "credit" in message or "card" in message or "loan" in message:
                # User wants credit products
                pass
            elif "save" in message or "deposit" in message or "account" in message or "dps" in message or "scheme" in message:
                # User wants savings products
                pass
            elif "investment" in message or "mutual" in message:
                # User wants investment products
                pass
            else:
                required_slots.append("product_category")
        
        if state.intent == "eligibility":
            if state.user_profile.age is None:
                required_slots.append("age")
            if state.user_profile.income_monthly is None and state.user_profile.income_yearly is None:
                required_slots.append("income")
            if state.user_profile.deposit is None:
                required_slots.append("deposit")
        
        elif state.intent == "compare":
            if state.product_category is None:
                if "product_category" not in required_slots:
                    required_slots.append("product_category")
        
        return {
            "missing_slots": required_slots,
            "last_agent": "check_missing_slots"
        }

    def route_and_invoke_node(self, state: ConversationState) -> dict:
        state_dict = state.model_dump() if isinstance(state, ConversationState) else state
        
        if state.missing_slots:
            result_dict = self.slot_collection_graph.invoke(state_dict)
        elif state.intent == "eligibility":
            result_dict = self.eligibility_graph.invoke(state_dict)
        elif state.intent == "compare":
            result_dict = self.comparison_graph.invoke(state_dict)
        elif state.intent == "explain":
            result_dict = self.rag_explanation_graph.invoke(state_dict)
        else:
            result_dict = self.product_retrieval_graph.invoke(state_dict)
        
        result_state = ConversationState(**result_dict) if isinstance(result_dict, dict) else result_dict
        
        return {
            "user_profile": result_state.user_profile,
            "missing_slots": result_state.missing_slots if result_state.missing_slots else [],
            "response": result_state.response,
            "eligible_products": result_state.eligible_products if result_state.eligible_products else [],
            "comparison_mode": result_state.comparison_mode,
            "banking_type": result_state.banking_type,  # Preserve banking_type updates
            "product_category": result_state.product_category,  # Preserve product_category updates
            "last_agent": "route_and_invoke"
        }

    def build_graph(self) -> Any:
        graph = StateGraph(ConversationState)
        
        graph.add_node("parse_message", self.parse_message_node)
        graph.add_node("detect_intent", self.detect_intent_node)
        graph.add_node("check_missing_slots", self.check_missing_slots_node)
        graph.add_node("route_and_invoke", self.route_and_invoke_node)
        
        graph.set_entry_point("parse_message")
        graph.add_edge("parse_message", "detect_intent")
        graph.add_edge("detect_intent", "check_missing_slots")
        graph.add_edge("check_missing_slots", "route_and_invoke")
        graph.add_edge("route_and_invoke", END)
        
        self._graph = graph.compile()
        save_graph_visualization(graph, "graph_0_conversation_manager")
        return self._graph
    
    def invoke(self, state: ConversationState) -> ConversationState:
        graph = self.build_graph()
        result = graph.invoke(state)
        
        updated_fields = {
            "intent": result.get("intent", state.intent),
            "banking_type": result.get("banking_type", state.banking_type),
            "product_category": result.get("product_category", state.product_category),
            "user_profile": result.get("user_profile", state.user_profile),
            "missing_slots": result.get("missing_slots", state.missing_slots),
            "response": result.get("response", state.response),
            "eligible_products": result.get("eligible_products", state.eligible_products),
            "comparison_mode": result.get("comparison_mode", state.comparison_mode),
            "last_agent": result.get("last_agent", state.last_agent)
        }
        
        return ConversationState(**{**state.model_dump(), **updated_fields})
