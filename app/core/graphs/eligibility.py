from langgraph.graph import StateGraph, START, END
from app.core.config import llm
from app.models.conversation_state import ConversationState
from app.models.graphs import EligibilityAssessment
from app.prompts.eligibility import ASSESS_ELIGIBILITY_PROMPT, GENERATE_RESPONSE_PROMPT
import json
import logging

logger = logging.getLogger(__name__)


class EligibilityGraph:
    def __init__(self):
        self.llm = llm

    def assess_eligibility_node(self, state: ConversationState) -> dict:
        logger.info(f"📊 [ELIGIBILITY_ASSESS] Assessing eligibility for user...")
        try:
            profile = state.user_profile
            
            prompt = ASSESS_ELIGIBILITY_PROMPT.format(
                age=profile.age or "Unknown",
                employment=profile.employment_type or "Unknown",
                income=profile.income_monthly or "Unknown",
                credit_score=profile.credit_score or "Not checked",
                banking_type=state.banking_type or "conventional",
                product_category=state.product_category or "deposit"
            )
            logger.info(f"📝 [ELIGIBILITY_ASSESS] Calling LLM for eligibility assessment...")

            structured_llm = self.llm.with_structured_output(EligibilityAssessment)
            result = structured_llm.invoke(prompt)
            logger.info(f"✅ [ELIGIBILITY_ASSESS] Eligible products: {result.eligible_products}")

            return {
                "eligible_products": result.eligible_products,
                "response": result.reasoning
            }
        except Exception as e:
            return {
                "eligible_products": [],
                "response": "I'm assessing your eligibility. Please provide more details about yourself."
            }

    def filter_by_category_node(self, state: ConversationState) -> dict:
        if not state.eligible_products:
            return {"eligible_products": []}
        
        products = state.eligible_products
        category = state.product_category or "all"
        
        category_mapping = {
            "deposit": ["savings_account", "dps", "fdr", "deposit"],
            "credit": ["credit_card", "personal_loan", "auto_loan"],
            "investment": ["mutual_fund", "investment_account", "wealth"]
        }
        
        if category in category_mapping:
            filtered = [p for p in products if any(
                cat_keyword in p.lower() 
                for cat_keyword in category_mapping[category]
            )]
            return {"eligible_products": filtered or products}
        
        return {"eligible_products": products}

    def apply_banking_type_node(self, state: ConversationState) -> dict:
        if state.banking_type == "islami":
            products = state.eligible_products or []
            filtered = [p for p in products if "islamic" in p.lower() or "islami" in p.lower()]
            return {"eligible_products": filtered or products}
        
        return {}

    def generate_eligibility_message_node(self, state: ConversationState) -> dict:
        try:
            profile = state.user_profile
            eligible = state.eligible_products or []
            
            recommendations = eligible[:2] if eligible else []
            
            prompt = self.GENERATE_RESPONSE_PROMPT.format(
                eligible_products=", ".join(eligible) or "None at this time",
                age=profile.age or "Unknown",
                employment=profile.employment_type or "Unknown",
                income=profile.income_monthly or "Unknown",
                recommendations=", ".join(recommendations)
            )

            response = self.llm.invoke(prompt)
            return {"response": response.content}
        except Exception as e:
            eligible = state.eligible_products or []
            if eligible:
                return {"response": f"Based on your profile, you may be eligible for: {', '.join(eligible[:3])}"}
            return {"response": "I need more information to assess your eligibility."}

    def build_graph(self):
        graph = StateGraph(ConversationState)
        
        graph.add_node("assess_eligibility", self.assess_eligibility_node)
        graph.add_node("filter_category", self.filter_by_category_node)
        graph.add_node("apply_banking_type", self.apply_banking_type_node)
        graph.add_node("generate_message", self.generate_eligibility_message_node)
        
        graph.add_edge(START, "assess_eligibility")
        graph.add_edge("assess_eligibility", "filter_category")
        graph.add_edge("filter_category", "apply_banking_type")
        graph.add_edge("apply_banking_type", "generate_message")
        graph.add_edge("generate_message", END)
        
        return graph.compile()

    def visualize(self):
        graph = self.build_graph()
        return graph.get_graph().to_dict()

    def invoke(self, state):
        graph = self.build_graph()
        return graph.invoke(state)
