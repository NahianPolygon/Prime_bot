from langgraph.graph import StateGraph, END
from typing import Any
from app.models.conversation_state import ConversationState
from app.core.graph_visualizer import save_graph_visualization
from app.services.knowledge_service import load_products


class ProductRetrievalGraph:
    def __init__(self):
        self._graph = None

    def build_query_node(self, state: ConversationState) -> dict:
        banking_type = state.banking_type or "conventional"
        category = state.product_category or "deposit"
        
        return {
            "banking_type": banking_type,
            "product_category": category,
            "response": f"Searching for {banking_type} {category} products..."
        }

    def fetch_products_node(self, state: ConversationState) -> dict:
        banking_type = state.banking_type or "conventional"
        category = state.product_category or "deposit"
        
        # Load products from knowledge base
        products = load_products(banking_type, category)
        
        product_names = []
        if isinstance(products, list):
            product_names = [p.get('product_name') or p.get('name', '') for p in products if p.get('product_name') or p.get('name')]
        elif isinstance(products, dict):
            product_names = list(products.keys())
        
        return {
            "eligible_products": product_names[:10],
            "response": f"Found {len(product_names)} {banking_type} {category} products."
        }

    def rank_products_node(self, state: ConversationState) -> dict:
        products = state.eligible_products if isinstance(state.eligible_products, list) else []
        
        # Rank based on user profile
        ranked = products
        if state.user_profile and state.user_profile.employment_type:
            employment_type = state.user_profile.employment_type.lower()
            
            if "freelancer" in employment_type or "self-employed" in employment_type:
                freelancer_products = [p for p in products if "freelancer" in p.lower()]
                other_products = [p for p in products if "freelancer" not in p.lower()]
                ranked = freelancer_products + other_products
        
        return {
            "eligible_products": ranked[:10],
            "response": f"Ranked {len(ranked)} products."
        }

    def format_response_node(self, state: ConversationState) -> dict:
        message = state.conversation_history[-1]["content"].lower() if state.conversation_history else ""
        banking_type = state.banking_type or "conventional"
        category = state.product_category or "deposit"
        products = state.eligible_products if isinstance(state.eligible_products, list) else []
        
        if any(word in message for word in ["islamic", "shariah", "halal", "islami"]):
            if not products:
                response = "I understand you're interested in Shariah-compliant banking products. What type of product would you like - savings accounts, deposit schemes, or credit products?"
            else:
                top_products = products[:3]
                products_text = "\n".join([f"• {p}" for p in top_products])
                response = f"Great! Here are our Shariah-compliant {category} products:\n{products_text}\n\nWould you like more details?"
        
        elif any(word in message for word in ["deposit", "save", "savings", "account", "dps", "scheme"]):
            if not products:
                response = f"For savings and deposit products, could you tell me more? How much would you like to deposit initially?"
            else:
                top_products = products[:3]
                products_text = "\n".join([f"• {p}" for p in top_products])
                response = f"Based on your interest in savings, here are our top {banking_type} options:\n{products_text}\n\nWould you like more details?"
        
        elif any(word in message for word in ["credit", "card", "loan"]):
            if not products:
                response = f"We have various credit products. What's your annual income and what features matter most to you?"
            else:
                top_products = products[:3]
                products_text = "\n".join([f"• {p}" for p in top_products])
                response = f"Here are our {banking_type} credit cards:\n{products_text}\n\nWould you like to know about features or eligibility?"
        
        else:
            if not products:
                response = f"I'd love to help! Could you tell me more about what type of product you're looking for?"
            else:
                top_products = products[:3]
                products_text = "\n".join([f"• {p}" for p in top_products])
                response = f"Based on your interest, here are my recommendations:\n{products_text}\n\nWould you like more details?"
        
        return {
            "response": response,
            "eligible_products": products
        }

    def build_graph(self) -> Any:
        graph = StateGraph(ConversationState)
        
        graph.add_node("build_query", self.build_query_node)
        graph.add_node("fetch_products", self.fetch_products_node)
        graph.add_node("rank_products", self.rank_products_node)
        graph.add_node("format_response", self.format_response_node)
        
        graph.set_entry_point("build_query")
        graph.add_edge("build_query", "fetch_products")
        graph.add_edge("fetch_products", "rank_products")
        graph.add_edge("rank_products", "format_response")
        graph.add_edge("format_response", END)
        
        self._graph = graph.compile()
        save_graph_visualization(graph, "graph_2_product_retrieval")
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
            "response": result.get("response", state_obj.response)
        }
        
        return ConversationState(**{**state_obj.model_dump(), **updated_fields})
