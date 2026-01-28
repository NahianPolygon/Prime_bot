from langgraph.graph import StateGraph, START, END
from app.core.config import llm
from app.models.conversation_state import ConversationState
from app.models.graphs import ExplanationResult
from app.prompts.rag_explanation import RETRIEVE_DOCUMENTS_PROMPT, GROUND_EXPLANATION_PROMPT, FORMAT_EXPLANATION_MESSAGE
from app.services.knowledge_service import load_products
import logging

logger = logging.getLogger(__name__)


class RAGExplanationGraph:
    def __init__(self):
        self.llm = llm

    def retrieve_documents_node(self, state: ConversationState) -> dict:
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

        context = []
        for prod in all_products[:2]:
            context.append({
                "name": prod.get("product_name") or prod.get("name", ""),
                "description": prod.get("description") or prod.get("tagline", ""),
                "features": prod.get("features", []),
                "charges": prod.get("charges", {}) if isinstance(prod.get("charges"), dict) else {}
            })

        return {
            "retrieved_context": context,
            "response": f"Retrieved context for {len(context)} products"
        }

    def ground_explanation_node(self, state: ConversationState) -> dict:
        try:
            product = state.response or "banking product"
            context = getattr(state, "retrieved_context", [])
            profile = state.user_profile.model_dump(exclude_none=True)
            
            prompt = self.GROUND_EXPLANATION_PROMPT.format(
                product=product,
                context=str(context),
                profile=profile
            )

            structured_llm = self.llm.with_structured_output(ExplanationResult)
            result = structured_llm.invoke(prompt)

            return {
                "response": result.explanation,
                "explanation_benefits": result.key_benefits,
                "explanation_terms": result.important_terms
            }
        except Exception as e:
            return {
                "response": f"Let me explain this product to you.",
                "explanation_benefits": [],
                "explanation_terms": {}
            }

    def format_explanation_node(self, state: ConversationState) -> dict:
        try:
            explanation = getattr(state, "response", "")
            benefits = getattr(state, "explanation_benefits", [])
            terms = getattr(state, "explanation_terms", {})
            
            prompt = self.FORMAT_EXPLANATION_MESSAGE.format(
                explanation=explanation or "Explanation pending",
                benefits=", ".join(benefits) if benefits else "None identified",
                terms=str(terms) if terms else "No specific terms"
            )

            response = self.llm.invoke(prompt)
            return {"response": response.content}
        except Exception as e:
            explanation = getattr(state, "response", "")
            if explanation:
                return {"response": explanation}
            return {"response": "I can help explain this banking product to you."}

    def build_graph(self):
        graph = StateGraph(ConversationState)
        
        graph.add_node("retrieve_documents", self.retrieve_documents_node)
        graph.add_node("ground_explanation", self.ground_explanation_node)
        graph.add_node("format_explanation", self.format_explanation_node)
        
        graph.add_edge(START, "retrieve_documents")
        graph.add_edge("retrieve_documents", "ground_explanation")
        graph.add_edge("ground_explanation", "format_explanation")
        graph.add_edge("format_explanation", END)
        
        return graph.compile()

    def visualize(self):
        graph = self.build_graph()
        return graph.get_graph().to_dict()

    def invoke(self, state):
        graph = self.build_graph()
        return graph.invoke(state)
