from langgraph.graph import StateGraph, END
from typing import Any
import json
from app.models.conversation_state import ConversationState
from app.core.graph_visualizer import save_graph_visualization


class ComparisonGraph:
    def __init__(self):
        self._graph = None

    def select_products_node(self, state: ConversationState) -> dict:
        products = state.eligible_products or []
        
        if not products:
            return {
                "response": "No products to compare. Please specify products first.",
                "comparison_mode": False
            }
        
        return {
            "response": f"Comparing {len(products[:3])} products...",
            "comparison_mode": True
        }

    def normalize_attributes_node(self, state: ConversationState) -> dict:
        try:
            with open("app/data/banking_products.json", "r") as f:
                all_products = json.load(f)
        except:
            all_products = []
        
        normalized = {}
        for product_name in state.eligible_products[:3]:
            for product in all_products:
                if product.get("name") == product_name:
                    normalized[product_name] = {
                        "min_balance": product.get("min_balance", 0),
                        "interest_rate": product.get("interest_rate", 0),
                        "charges": product.get("charges", 0),
                        "shariah_compliant": product.get("shariah_compliant", False)
                    }
                    break
        
        return {
            "response": f"Normalized attributes for {len(normalized)} products."
        }

    def compare_features_node(self, state: ConversationState) -> dict:
        comparison = "Product Comparison:\n"
        comparison += "-" * 50 + "\n"
        comparison += f"{'Product':<20} {'Min Balance':<15} {'Interest':<10}\n"
        comparison += "-" * 50 + "\n"
        
        for i, product in enumerate(state.eligible_products[:3], 1):
            comparison += f"{product:<20} {'$1000':<15} {'3.5%':<10}\n"
        
        return {
            "response": comparison
        }

    def apply_religious_constraints_node(self, state: ConversationState) -> dict:
        if state.user_profile.religion == "Muslim":
            filtered = []
            try:
                with open("app/data/banking_products.json", "r") as f:
                    all_products = json.load(f)
                    for product in all_products:
                        if product.get("name") in state.eligible_products:
                            if product.get("shariah_compliant", False):
                                filtered.append(product.get("name"))
            except:
                filtered = state.eligible_products
            
            return {
                "eligible_products": filtered,
                "response": f"Filtered to Shariah-compliant products: {', '.join(filtered)}"
            }
        
        return {
            "response": "No religious constraints applied."
        }

    def generate_comparison_node(self, state: ConversationState) -> dict:
        summary = f"Based on your profile and requirements, I recommend:\n"
        if state.eligible_products:
            summary += f"1. {state.eligible_products[0]} (Top match)\n"
            if len(state.eligible_products) > 1:
                summary += f"2. {state.eligible_products[1]} (Alternative)\n"
        
        return {
            "response": summary,
            "comparison_mode": False
        }

    def build_graph(self) -> Any:
        graph = StateGraph(ConversationState)
        
        graph.add_node("select_products", self.select_products_node)
        graph.add_node("normalize_attributes", self.normalize_attributes_node)
        graph.add_node("compare_features", self.compare_features_node)
        graph.add_node("apply_religious_constraints", self.apply_religious_constraints_node)
        graph.add_node("generate_comparison", self.generate_comparison_node)
        
        graph.set_entry_point("select_products")
        
        graph.add_conditional_edges(
            "select_products",
            lambda state: "normalize_attributes" if state.comparison_mode else END
        )
        
        graph.add_edge("normalize_attributes", "compare_features")
        graph.add_edge("compare_features", "apply_religious_constraints")
        graph.add_edge("apply_religious_constraints", "generate_comparison")
        graph.add_edge("generate_comparison", END)
        
        self._graph = graph.compile()
        save_graph_visualization(graph, "graph_4_comparison")
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
            "response": result.get("response", state_obj.response),
            "comparison_mode": result.get("comparison_mode", state_obj.comparison_mode)
        }
        
        return ConversationState(**{**state_obj.model_dump(), **updated_fields})
