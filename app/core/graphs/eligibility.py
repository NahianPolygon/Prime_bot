from langgraph.graph import StateGraph, END
from typing import Any
from app.models.conversation_state import ConversationState
from app.core.graph_visualizer import save_graph_visualization
import json


class EligibilityGraph:
    def __init__(self):
        self._graph = None

    def validate_inputs_node(self, state: ConversationState) -> dict:
        required_fields = ["age", "income_monthly", "employment_type"]
        missing = [f for f in required_fields if not getattr(state.user_profile, f, None)]
        
        if missing:
            return {
                "missing_slots": missing,
                "response": f"I need {', '.join(missing)} to determine eligibility.",
                "eligible_products": []
            }
        
        return {
            "response": "Checking eligibility...",
            "eligible_products": []
        }

    def apply_rules_node(self, state: ConversationState) -> dict:
        profile = state.user_profile
        eligible = []
        
        if profile.employment_type == "salaried" and 18 <= profile.age <= 65 and profile.income_monthly >= 20000:
            eligible.extend(["savings_account", "dps", "monthly_sip"])
        
        if profile.age >= 21 and profile.income_monthly >= 30000:
            eligible.extend(["credit_card", "personal_loan"])
        
        if profile.income_monthly >= 50000:
            eligible.extend(["investment_account", "wealth_management"])
        
        if profile.deposit and profile.deposit >= 100000:
            eligible.append("fixed_deposit_premium")
        
        return {
            "eligible_products": list(set(eligible)),
            "response": f"Found {len(set(eligible))} eligible products for you."
        }

    def filter_products_node(self, state: ConversationState) -> dict:
        try:
            with open("app/data/banking_products.json", "r") as f:
                products = json.load(f)
        except:
            products = []
        
        filtered = []
        for product in products:
            if product.get("type") in state.eligible_products:
                if state.user_profile.religion and product.get("shariah_compliant") is False:
                    continue
                filtered.append(product)
        
        return {
            "eligible_products": [p.get("name") for p in filtered],
            "response": f"Filtered to {len(filtered)} products based on your profile."
        }

    def store_eligible_products_node(self, state: ConversationState) -> dict:
        return {
            "eligible_products": state.eligible_products,
            "response": f"Eligible products: {', '.join(state.eligible_products[:5])}"
        }

    def build_graph(self) -> Any:
        graph = StateGraph(ConversationState)
        
        graph.add_node("validate_inputs", self.validate_inputs_node)
        graph.add_node("apply_rules", self.apply_rules_node)
        graph.add_node("filter_products", self.filter_products_node)
        graph.add_node("store_eligible_products", self.store_eligible_products_node)
        
        graph.set_entry_point("validate_inputs")
        
        graph.add_conditional_edges(
            "validate_inputs",
            lambda state: "apply_rules" if not state.missing_slots else END
        )
        
        graph.add_edge("apply_rules", "filter_products")
        graph.add_edge("filter_products", "store_eligible_products")
        graph.add_edge("store_eligible_products", END)
        
        self._graph = graph.compile()
        save_graph_visualization(graph, "graph_2_eligibility")
        return self._graph
        self._graph = graph.compile()
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
            "eligible_products": result.get("eligible_products", state_obj.eligible_products),
            "missing_slots": result.get("missing_slots", state_obj.missing_slots),
            "response": result.get("response", state_obj.response)
        }
        
        return ConversationState(**{**state_obj.model_dump(), **updated_fields})
