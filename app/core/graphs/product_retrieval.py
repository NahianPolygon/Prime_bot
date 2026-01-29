from langgraph.graph import StateGraph, START, END
from app.core.config import llm
from app.models.conversation_state import ConversationState
from app.models.graphs import ProductSelection
from app.services.knowledge_cache import KnowledgeBaseCache
from app.prompts.product_retrieval import RETRIEVE_PRODUCTS_PROMPT, RANK_PRODUCTS_PROMPT, GENERATE_RETRIEVAL_MESSAGE
import logging

logger = logging.getLogger(__name__)


class ProductRetrievalGraph:
    def __init__(self):
        self.llm = llm
    def retrieve_products_node(self, state: ConversationState) -> dict:
        try:
            banking_type = state.banking_type or "conventional"
            category = state.product_category or "credit"
            
            kb_cache = KnowledgeBaseCache.get_instance()
            products = kb_cache.get_credit_cards(banking_type) if category == "credit" else []
            product_names = []
            
            if isinstance(products, list):
                product_names = [
                    p.get("product_name") or p.get("name", "") 
                    for p in products if p.get("product_name") or p.get("name")
                ]
            elif isinstance(products, dict):
                product_names = list(products.keys())
            
            profile = state.user_profile.model_dump(exclude_none=True)
            
            prompt = self.RETRIEVE_PRODUCTS_PROMPT.format(
                banking_type=banking_type,
                product_category=category,
                profile=profile,
                available_products=", ".join(product_names[:10]) or "None"
            )

            structured_llm = self.llm.with_structured_output(ProductSelection)
            result = structured_llm.invoke(prompt)

            return {
                "eligible_products": result.selected_products,
                "response": result.ranking_reason
            }
        except Exception as e:
            return {
                "eligible_products": [],
                "response": "I'm retrieving available products for you."
            }

    def rank_products_node(self, state: ConversationState) -> dict:
        if not state.eligible_products:
            return {}
        
        try:
            products = state.eligible_products if isinstance(state.eligible_products, list) else []
            profile = state.user_profile
            
            prompt = self.RANK_PRODUCTS_PROMPT.format(
                products=", ".join(products),
                age=profile.age or "Unknown",
                employment=profile.employment_type or "Unknown",
                income=profile.income_monthly or "Unknown"
            )

            structured_llm = self.llm.with_structured_output(ProductSelection)
            result = structured_llm.invoke(prompt)

            return {"eligible_products": result.selected_products}
        except Exception as e:
            return {"eligible_products": state.eligible_products}

    def generate_recommendation_message_node(self, state: ConversationState) -> dict:
        try:
            products = state.eligible_products or []
            profile_category = state.product_category or "banking"
            
            prompt = self.GENERATE_RETRIEVAL_MESSAGE.format(
                products=", ".join(products) or "None currently",
                profile_category=profile_category
            )

            response = self.llm.invoke(prompt)
            return {"response": response.content}
        except Exception as e:
            products = state.eligible_products or []
            if products:
                return {"response": f"Here are some products you might be interested in: {', '.join(products[:3])}"}
            return {"response": "Let me help you find the right product for your needs."}

    def build_graph(self):
        graph = StateGraph(ConversationState)
        
        graph.add_node("retrieve_products", self.retrieve_products_node)
        graph.add_node("rank_products", self.rank_products_node)
        graph.add_node("generate_message", self.generate_recommendation_message_node)
        
        graph.add_edge(START, "retrieve_products")
        graph.add_edge("retrieve_products", "rank_products")
        graph.add_edge("rank_products", "generate_message")
        graph.add_edge("generate_message", END)
        
        return graph.compile()

    def visualize(self):
        graph = self.build_graph()
        return graph.get_graph().to_dict()

    def invoke(self, state):
        graph = self.build_graph()
        return graph.invoke(state)
