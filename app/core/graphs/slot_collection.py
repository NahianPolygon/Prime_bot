from langgraph.graph import StateGraph, END
from typing import Any
from app.models.conversation_state import ConversationState
from app.core.graph_visualizer import save_graph_visualization


class SlotCollectionGraph:
    def __init__(self):
        self._graph = None

    def identify_missing_slot_node(self, state: ConversationState) -> dict:
        if not state.missing_slots:
            return {
                "response": "Perfect! I have all the information I need. Let me find the best products for you.",
                "missing_slots": []
            }
        
        slot = state.missing_slots[0]
        last_message = state.conversation_history[-1]["content"] if state.conversation_history else ""
        
        # Dynamic prompts based on context
        prompts = {
            "age": f"I see you're interested in banking products. To help me find the best options, could you share your age?",
            "income": f"Thanks! Now, what's your approximate monthly income in BDT? This helps me suggest products suited to your financial profile.",
            "deposit": f"Great! How much would you like to deposit initially? This helps me recommend products with suitable denomination requirements.",
            "product_category": f"I'd love to help! Are you looking for savings products (like accounts or deposit schemes) or credit products (like credit cards)?",
            "employment_type": f"What's your employment type? Are you salaried, self-employed, or in business? This affects which products suit you best.",
            "banking_type": f"Would you prefer conventional banking products or Islamic (Shariah-compliant) banking products?"
        }
        
        response = prompts.get(slot, f"Could you help me understand your {slot}?")
        
        return {
            "response": response
        }

    def ask_question_node(self, state: ConversationState) -> dict:
        return {"response": state.response}

    def parse_user_answer_node(self, state: ConversationState) -> dict:
        if not state.conversation_history:
            return {}
        
        last_message = state.conversation_history[-1]["content"]
        missing_slots = state.missing_slots.copy() if state.missing_slots else []
        profile = state.user_profile.model_copy() if state.user_profile else None
        
        if missing_slots:
            current_slot = missing_slots[0]
            
            try:
                if current_slot == "age":
                    # Extract age from message
                    import re
                    age_match = re.search(r'\b(\d{1,3})\b', last_message)
                    if age_match:
                        profile.age = int(age_match.group(1))
                        missing_slots.pop(0)
                
                elif current_slot == "income":
                    # Extract income from message
                    import re
                    income_match = re.search(r'(\d+(?:[.,]\d{3})*)', last_message.replace(',', ''))
                    if income_match:
                        profile.income_monthly = float(income_match.group(1))
                        missing_slots.pop(0)
                
                elif current_slot == "deposit":
                    # Extract deposit amount
                    import re
                    deposit_match = re.search(r'(\d+(?:[.,]\d{3})*)', last_message.replace(',', ''))
                    if deposit_match:
                        profile.deposit = float(deposit_match.group(1))
                        missing_slots.pop(0)
                
                elif current_slot == "employment_type":
                    message_lower = last_message.lower()
                    if 'salaried' in message_lower or 'employee' in message_lower:
                        profile.employment_type = "salaried"
                    elif 'self' in message_lower or 'freelancer' in message_lower:
                        profile.employment_type = "self-employed"
                    elif 'business' in message_lower or 'entrepreneur' in message_lower:
                        profile.employment_type = "business"
                    missing_slots.pop(0)
                
                elif current_slot == "banking_type":
                    message_lower = last_message.lower()
                    if 'islamic' in message_lower or 'shariah' in message_lower or 'islami' in message_lower:
                        
                        return {
                            "user_profile": profile,
                            "missing_slots": missing_slots,
                            "banking_type": "islami"
                        }
                    missing_slots.pop(0)
                
            except Exception as e:
                print(f"Error parsing answer: {e}")
        
        return {
            "user_profile": profile,
            "missing_slots": missing_slots
        }

    def update_state_node(self, state: ConversationState) -> dict:
        return {
            "user_profile": state.user_profile,
            "missing_slots": state.missing_slots
        }

    def build_graph(self) -> Any:
        graph = StateGraph(ConversationState)
        
        graph.add_node("identify_missing_slot", self.identify_missing_slot_node)
        graph.add_node("ask_question", self.ask_question_node)
        graph.add_node("parse_user_answer", self.parse_user_answer_node)
        graph.add_node("update_state", self.update_state_node)
        
        graph.set_entry_point("identify_missing_slot")
        
        graph.add_conditional_edges(
            "identify_missing_slot",
            lambda state: "ask_question" if state.missing_slots else END
        )
        
        graph.add_edge("ask_question", "parse_user_answer")
        graph.add_edge("parse_user_answer", "update_state")
        graph.add_edge("update_state", "identify_missing_slot")
        
        self._graph = graph.compile()
        save_graph_visualization(graph, "graph_1_slot_collection")
        return self._graph
    
    def invoke(self, state: ConversationState) -> ConversationState:
        graph = self.build_graph()
        if isinstance(state, dict):
            state_obj = ConversationState(**state)
            state_dict = state
        else:
            state_obj = state
            state_dict = state.model_dump()
        
        result = graph.invoke(state_dict)
        
        updated_fields = {
            "user_profile": result.get("user_profile", state_obj.user_profile),
            "missing_slots": result.get("missing_slots", state_obj.missing_slots),
            "response": result.get("response", state_obj.response)
        }
        
        return ConversationState(**{**state_obj.model_dump(), **updated_fields})
