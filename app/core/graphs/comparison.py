from langgraph.graph import StateGraph, START, END
from app.core.config import llm
from app.models.conversation_state import ConversationState
from app.models.graphs import ComparisonResult
from app.prompts.comparison import COMPARE_PRODUCTS_PROMPT, GENERATE_COMPARISON_MESSAGE
from app.services.knowledge_service import load_products
import logging

logger = logging.getLogger(__name__)


class ComparisonGraph:
    def __init__(self):
        self.llm = llm

    def prepare_comparison_node(self, state: ConversationState) -> dict:
        logger.info(f"⚖️  [COMPARISON_PREP] Preparing comparison for {len(state.eligible_products)} products")
        products = state.eligible_products or []
        
        if len(products) < 2:
            logger.info(f"⚠️  [COMPARISON_PREP] Not enough products to compare (need 2+, have {len(products)})")
            return {
                "response": "Need at least 2 products to compare. Let me retrieve more options.",
                "comparison_mode": False
            }

        logger.info(f"✅ [COMPARISON_PREP] Ready to compare {len(products[:3])} products")
        return {
            "response": f"Comparing {len(products[:3])} products for you...",
            "comparison_mode": True
        }

    def fetch_product_details_node(self, state: ConversationState) -> dict:
        products = state.eligible_products or []
        banking_type = state.banking_type or "conventional"
        category = state.product_category or "deposit"
        
        # Map product categories to knowledge service categories
        category_map = {
            "credit": "credit",
            "deposit": "deposit",
            "schemes": "schemes"
        }
        kb_category = category_map.get(category, "deposit")
        
        # Load products from knowledge base
        all_products = load_products(banking_type, kb_category)

        product_details = {}
        for product_name in products[:3]:
            for product_data in all_products:
                if product_data.get("name") == product_name or product_data.get("product_name") == product_name:
                    product_details[product_name] = {
                        "min_balance": product_data.get("min_balance", "N/A"),
                        "interest_rate": product_data.get("interest_rate", "N/A"),
                        "charges": product_data.get("charges", "N/A"),
                        "shariah_compliant": product_data.get("shariah_compliant", False),
                        "features": product_data.get("features", [])
                    }
                    break

        return {"product_details": product_details}

    def compare_products_node(self, state: ConversationState) -> dict:
        try:
            products = state.eligible_products or []
            profile = state.user_profile.model_dump(exclude_none=True)
            
            prompt = self.COMPARE_PRODUCTS_PROMPT.format(
                products=", ".join(products[:3]),
                profile=profile,
                banking_type=state.banking_type or "conventional"
            )

            structured_llm = self.llm.with_structured_output(ComparisonResult)
            result = structured_llm.invoke(prompt)

            return {
                "response": result.comparison_text,
                "comparison_recommendation": result.recommendation,
                "comparison_key_differences": result.key_differences
            }
        except Exception as e:
            return {
                "response": "I'm comparing these products for you.",
                "comparison_recommendation": "",
                "comparison_key_differences": []
            }

    def generate_comparison_message_node(self, state: ConversationState) -> dict:
        try:
            comparison = getattr(state, "response", "")
            recommendation = getattr(state, "comparison_recommendation", "")
            differences = getattr(state, "comparison_key_differences", [])
            
            prompt = self.GENERATE_COMPARISON_MESSAGE.format(
                comparison=comparison or "Comparison in progress",
                recommendation=recommendation or "Analysis pending",
                differences=", ".join(differences) if differences else "None identified"
            )

            response = self.llm.invoke(prompt)
            return {"response": response.content}
        except Exception as e:
            products = state.eligible_products or []
            if products:
                return {"response": f"Compared products: {', '.join(products[:3])}. Let me know if you need more details."}
            return {"response": "I can help you compare these products."}

    def build_graph(self):
        graph = StateGraph(ConversationState)
        
        graph.add_node("prepare_comparison", self.prepare_comparison_node)
        graph.add_node("fetch_details", self.fetch_product_details_node)
        graph.add_node("compare_products", self.compare_products_node)
        graph.add_node("generate_message", self.generate_comparison_message_node)
        
        graph.add_edge(START, "prepare_comparison")
        graph.add_edge("prepare_comparison", "fetch_details")
        graph.add_edge("fetch_details", "compare_products")
        graph.add_edge("compare_products", "generate_message")
        graph.add_edge("generate_message", END)
        
        return graph.compile()

    def visualize(self):
        graph = self.build_graph()
        return graph.get_graph().to_dict()

    def invoke(self, state):
        graph = self.build_graph()
        return graph.invoke(state)
