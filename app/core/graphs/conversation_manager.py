from langgraph.graph import StateGraph, START, END
from typing import Literal
import logging
import json
from app.core.config import llm
from app.models.conversation_state import ConversationState
from app.services.inquiry_classifier import InquiryClassifier
from app.services.rag_retriever import RAGRetriever
from app.core.graphs.product_retrieval import ProductRetrievalGraph
from app.core.graphs.comparison import ComparisonGraph
from app.core.graphs.configs import DEPOSIT_ACCOUNTS_CONFIG, CREDIT_CARDS_CONFIG, LOANS_CONFIG
from app.prompts.conversation.greeting import GREETING_RESPONSE_PROMPT
from app.prompts.conversation.product_detection import DETECT_PRODUCT_TYPE_PROMPT
from app.prompts.conversation.eligibility import ELIGIBILITY_CHECK_PROMPT, ELIGIBILITY_REQUEST_INFO_PROMPT
from app.prompts.conversation.rag_explanation import EXPLAIN_WITH_RAG_PROMPT, NO_KNOWLEDGE_RESPONSE, UNCLEAR_RESPONSE

logger = logging.getLogger(__name__)

class ConversationManagerGraph:
    def __init__(self):
        self.llm = llm
        self.classifier = InquiryClassifier()
        self.rag = RAGRetriever()
        self.product_retrieval_graphs = {
            "deposits": ProductRetrievalGraph(DEPOSIT_ACCOUNTS_CONFIG),
            "credit_cards": ProductRetrievalGraph(CREDIT_CARDS_CONFIG),
            "loans": ProductRetrievalGraph(LOANS_CONFIG)
        }
        self.comparison_graph = ComparisonGraph()
        self._graph = None

    def classify_intent_node(self, state: ConversationState) -> dict:
        logger.info(f"🔍 [CLASSIFY] Checking product_type_in_progress: {state.product_type_in_progress}")
        logger.info(f"🔍 [CLASSIFY] Checking comparison_status: {state.comparison_status}")
        
        user_message = state.conversation_history[-1]["content"] if state.conversation_history else ""
        message_lower = user_message.lower()
        
        if state.comparison_status == "collecting_slots":
            logger.info(f"✅ [CLASSIFY] Skipping classification - continuing comparison slot collection")
            return {
                "intent": "COMPARISON_QUERY",
                "inquiry_confidence": 1.0
            }
        
        # CHECK FOR COMPARISON KEYWORDS FIRST - highest priority
        comparison_keywords = ["compare", "versus", "vs", "comparison", "what's the difference", "compare these"]
        user_wants_comparison = any(kw in message_lower for kw in comparison_keywords)
        
        if user_wants_comparison:
            logger.info(f"✅ [CLASSIFY] Comparison keywords detected - routing to COMPARISON_QUERY")
            return {
                "intent": "COMPARISON_QUERY",
                "inquiry_confidence": 1.0
            }
        
        if state.product_type_in_progress:
            logger.info(f"✅ [CLASSIFY] Skipping classification - continuing product flow for {state.product_type_in_progress}")
            return {
                "intent": "PRODUCT_INFO_QUERY",
                "inquiry_confidence": 1.0
            }
        
        user_message = state.conversation_history[-1]["content"] if state.conversation_history else ""
        logger.info(f"⚡ [CLASSIFY_INQUIRY] Pattern-based classification (fast)")
        
        classification = self.classifier.classify(user_message)
        logger.info(f"✅ [CLASSIFY_INQUIRY] Type: {classification.inquiry_type}, Confidence: {classification.confidence}")
        
        return {
            "intent": classification.inquiry_type,
            "inquiry_confidence": classification.confidence,
            "banking_type": classification.extracted_context.banking_type or state.banking_type,
            "product_category": classification.extracted_context.product_category or state.product_category,
            "user_profile": state.user_profile.model_copy(update={
                "age": classification.extracted_context.age or state.user_profile.age,
                "employment_type": classification.extracted_context.employment or state.user_profile.employment_type,
                "income_yearly": classification.extracted_context.income or state.user_profile.income_yearly
            })
        }

    def handle_greeting_node(self, state: ConversationState) -> dict:
        user_message = state.conversation_history[-1]["content"]
        
        prompt = GREETING_RESPONSE_PROMPT.format(user_message=user_message)
        response = self.llm.invoke(prompt)
        
        return {
            "response": response.content,
            "last_agent": "greeting_handler"
        }

    def retrieve_products_node(self, state: ConversationState) -> dict:
        # If we're continuing a product retrieval flow, use the stored product_type
        if state.product_type_in_progress:
            product_type = state.product_type_in_progress
        else:
            product_type = self._detect_product_type(state)
            
        if product_type not in self.product_retrieval_graphs:
            return {
                "response": "I can help you with deposits, credit cards, or loans. Which are you interested in?",
                "last_agent": "product_retrieval"
            }
        
        guide = self.product_retrieval_graphs[product_type]
        result = guide.invoke(state)
        
        logger.info(f"📤 [RETRIEVE_PRODUCTS] Subgraph returned: response={bool(result.get('response'))}, last_agent={result.get('last_agent')}, next_action={result.get('next_action')}")
        
        # Mark that we're in product retrieval flow if there are missing slots (next_action="collect")
        if result.get("next_action") == "collect":
            # This is a slot collection response - include all extracted slot updates
            logger.info(f"✅ [RETRIEVE_PRODUCTS] Returning slot collection response with product_type_in_progress={product_type}")
            return {
                **result,  # Include all updates from subgraph (extracted slots, etc.)
                "last_agent": "product_retrieval",
                "product_type_in_progress": product_type,
            }
        
        # Regular response from search/recommend
        logger.info(f"✅ [RETRIEVE_PRODUCTS] Returning search/recommend response")
        return {
            **result,
            "last_agent": "product_retrieval"
        }
    
    def _detect_product_type(self, state: ConversationState) -> str:
        """Use LLM to detect product type from user message context"""
        message = state.conversation_history[-1]["content"] if state.conversation_history else ""
        
        if not message:
            return state.product_category or "deposits"
        
        # Try LLM-based detection first
        try:
            prompt = DETECT_PRODUCT_TYPE_PROMPT.format(message=message)

            response = self.llm.invoke(prompt)
            detected = response.content.strip().lower()
            
            # Validate response
            if detected in ["deposits", "credit_cards", "loans"]:
                logger.debug(f"📊 [DETECT_PRODUCT] LLM detected: {detected}")
                return detected
        except Exception as e:
            logger.warning(f"LLM product detection failed: {e}. Using fallback.")
        
        # Fallback: simple keyword matching if LLM fails
        message_lower = message.lower()
        if any(kw in message_lower for kw in ["save", "savings", "deposit", "account", "scheme", "interest", "recurring"]):
            return "deposits"
        elif any(kw in message_lower for kw in ["credit card", "card", "cashback", "reward"]):
            return "credit_cards"
        elif any(kw in message_lower for kw in ["loan", "borrow", "lending"]):
            return "loans"
        
        return state.product_category or "deposits"

    def check_eligibility_node(self, state: ConversationState) -> dict:
        user_message = state.conversation_history[-1]["content"]
        
        if state.matched_products:
            products = state.matched_products
        else:
            rag_chunks = self.rag.retrieve(user_message, top_k=5)
            products = [{"name": chunk.get("metadata", {}).get("product_name", "Product"), 
                        "knowledge_chunks": [chunk.get("chunk", "")]} for chunk in rag_chunks]
        
        if not products or not state.user_profile.age:
            return {
                "response": ELIGIBILITY_REQUEST_INFO_PROMPT,
                "missing_slots": ["age", "employment_type"],
                "last_agent": "eligibility_check"
            }
        
        eligible = [p.get('name', '') for p in products]
        chunks = "\n".join(["\n".join(p.get('knowledge_chunks', [])) for p in products if p.get('knowledge_chunks')])
        
        prompt = ELIGIBILITY_CHECK_PROMPT.format(
            age=state.user_profile.age,
            employment=state.user_profile.employment_type,
            income=state.user_profile.income_yearly,
            products=', '.join(eligible),
            knowledge_context=chunks if chunks else 'Product eligibility information available'
        )
        
        try:
            response = self.llm.invoke(prompt)
            return {
                "response": response.content,
                "eligible_products": eligible,
                "matched_products": products,
                "last_agent": "eligibility_check"
            }
        except Exception as e:
            logger.error(f"Error in eligibility check: {e}")
            return {
                "response": f"Based on your profile, you're eligible for: {', '.join(eligible)}",
                "eligible_products": eligible,
                "matched_products": products,
                "last_agent": "eligibility_check"
            }

    def compare_products_node(self, state: ConversationState) -> dict:
        logger.info(f"📊 [COMPARE] Invoking ComparisonGraph subgraph")
        logger.info(f"   matched_products: {len(state.matched_products) if state.matched_products else 0}")
        logger.info(f"   suggested_products: {len(state.suggested_products) if state.suggested_products else 0}")
        
        result = self.comparison_graph.invoke(state)
        
        logger.info(f"✅ [COMPARE] ComparisonGraph returned response")
        logger.info(f"   result keys: {list(result.keys())}")
        
        updates = {
            "response": result.get("response", ""),
            "last_agent": "comparison"
        }
        
        # Get detected product type from result
        detected_product_type = result.get("comparison_product_type", state.comparison_product_type)
        
        # Check for appropriate slots based on product type
        all_slots_collected = False
        if detected_product_type == "credit_cards":
            banking_type = result.get("comparison_banking_type")
            spending_pattern = result.get("comparison_spending_pattern")
            card_tier = result.get("comparison_card_tier")
            income = result.get("comparison_income")
            logger.info(f"   CREDIT_CARD slot VALUES: banking_type={banking_type}, spending_pattern={spending_pattern}, card_tier={card_tier}, income={income}")
            all_slots_collected = (banking_type and spending_pattern and card_tier and income)
            logger.info(f"   Checking CREDIT_CARD slots: banking_type={bool(banking_type)}, spending_pattern={bool(spending_pattern)}, card_tier={bool(card_tier)}, income={bool(income)}")
        elif detected_product_type == "loans":
            all_slots_collected = (
                result.get("comparison_banking_type") and
                result.get("comparison_loan_purpose") and
                result.get("comparison_loan_amount") and
                result.get("comparison_repayment_period")
            )
            logger.info(f"   Checking LOAN slots: banking_type={bool(result.get('comparison_banking_type'))}, purpose={bool(result.get('comparison_loan_purpose'))}, amount={bool(result.get('comparison_loan_amount'))}, repayment={bool(result.get('comparison_repayment_period'))}")
        else:  # deposits (default)
            all_slots_collected = (
                result.get("comparison_banking_type") and
                result.get("comparison_deposit_frequency") and
                result.get("comparison_tenure_range") and
                result.get("comparison_purpose")
            )
            logger.info(f"   Checking DEPOSIT slots: banking_type={bool(result.get('comparison_banking_type'))}, frequency={bool(result.get('comparison_deposit_frequency'))}, tenure={bool(result.get('comparison_tenure_range'))}, purpose={bool(result.get('comparison_purpose'))}")
        
        logger.info(f"   all_slots_collected={all_slots_collected}")
        
        # Set comparison status
        if "response" in result and not all_slots_collected:
            updates["comparison_status"] = "collecting_slots"
            logger.info(f"   Setting comparison_status=collecting_slots")
        else:
            updates["comparison_status"] = "completed"
            logger.info(f"   Setting comparison_status=completed")
        
        # Always propagate product type
        if detected_product_type:
            updates["comparison_product_type"] = detected_product_type
            logger.info(f"   Set comparison_product_type={detected_product_type}")
        
        # Copy all comparison slot values from result
        for key in result.keys():
            if key.startswith("comparison_"):
                updates[key] = result[key]
                logger.info(f"   Set {key}={result[key]}")
        
        logger.info(f"   Final updates keys: {list(updates.keys())}")
        return updates

    def explain_with_rag_node(self, state: ConversationState) -> dict:
        user_message = state.conversation_history[-1]["content"]
        
        rag_chunks = self.rag.retrieve(user_message, top_k=5)
        
        if not rag_chunks:
            return {
                "response": NO_KNOWLEDGE_RESPONSE,
                "last_agent": "rag_explanation"
            }
        
        chunk_texts = "\n".join([c.get('chunk', '') for c in rag_chunks[:3]])
        
        prompt = EXPLAIN_WITH_RAG_PROMPT.format(
            user_message=user_message,
            knowledge_context=chunk_texts
        )
        
        try:
            response = self.llm.invoke(prompt)
            return {
                "response": response.content,
                "last_agent": "rag_explanation"
            }
        except Exception as e:
            logger.error(f"Error in RAG explanation: {e}")
            return {
                "response": UNCLEAR_RESPONSE,
                "last_agent": "rag_explanation"
            }


    def route_conversation(self, state: ConversationState) -> Literal["greeting", "product_retrieval", "eligibility", "comparison", "explanation"]:
        intent = state.intent
        user_message = state.conversation_history[-1]["content"] if state.conversation_history else ""
        
        logger.info(f"🚦 [ROUTE] Intent: {intent}")
        
        if intent == "GREETING":
            logger.info(f"   → routing to GREETING")
            return "greeting"
        
        elif intent == "COMPARISON_QUERY":
            logger.info(f"   → COMPARISON_QUERY detected")
            
            if state.comparison_status == "collecting_slots":
                logger.info(f"   → comparison_status=collecting_slots → routing to COMPARISON (continue slot collection)")
                return "comparison"
            
            has_matched_products = bool(state.matched_products)
            has_user_mentioned_products = self._user_mentioned_specific_products(user_message)
            
            logger.info(f"      has_matched_products={has_matched_products}, mentioned_products={has_user_mentioned_products}")
            
            if has_matched_products or has_user_mentioned_products:
                logger.info(f"   → routing to COMPARISON (products available or mentioned)")
                return "comparison"
            else:
                logger.info(f"   → routing to PRODUCT_RETRIEVAL (need to discover products)")
                return "product_retrieval"
        
        elif intent == "ELIGIBILITY_QUERY":
            logger.info(f"   → routing to ELIGIBILITY")
            return "eligibility"
        
        elif intent == "PRODUCT_INFO_QUERY":
            logger.info(f"   → routing to PRODUCT_RETRIEVAL")
            return "product_retrieval"
        
        logger.info(f"   → routing to EXPLANATION (default)")
        return "explanation"
    
    def _user_mentioned_specific_products(self, user_message: str) -> bool:
        """Check if user mentioned specific product names or types"""
        message_lower = user_message.lower()
        
        # Specific product name keywords
        product_name_keywords = [
            "prime", "youth", "teacher", "edu dps", "fixed deposit", "fd",
            "credit card", "loan", "savings account", "current account",
            "hasanah", "deposit scheme", "dps", "pps"
        ]
        
        # Product type keywords (when asking for category comparison)
        product_type_keywords = [
            "credit card", "deposit", "scheme", "savings account", 
            "current account", "loan", "investment", "fixed deposit"
        ]
        
        has_product_name = any(kw in message_lower for kw in product_name_keywords)
        has_product_type = any(kw in message_lower for kw in product_type_keywords)
        has_comparison_markers = any(marker in message_lower for marker in ["vs", "versus", "between", "two", "compare"])
        
        # User mentioned products if they have:
        # 1. Specific product names, OR
        # 2. Product types + comparison markers
        mentioned = has_product_name or (has_product_type and has_comparison_markers)
        
        logger.info(f"📋 [PRODUCT_MENTION] name={has_product_name}, type={has_product_type}, comparison={has_comparison_markers} → mentioned={mentioned}")
        
        return mentioned

    def build_graph(self):
        graph = StateGraph(ConversationState)
        
        graph.add_node("classify", self.classify_intent_node)
        graph.add_node("greeting", self.handle_greeting_node)
        graph.add_node("product_retrieval", self.retrieve_products_node)
        graph.add_node("eligibility", self.check_eligibility_node)
        graph.add_node("comparison", self.compare_products_node)
        graph.add_node("explanation", self.explain_with_rag_node)
        
        graph.add_edge(START, "classify")
        graph.add_conditional_edges("classify", self.route_conversation, {
            "greeting": "greeting",
            "product_retrieval": "product_retrieval",
            "eligibility": "eligibility",
            "comparison": "comparison",
            "explanation": "explanation"
        })
        
        graph.add_edge("greeting", END)
        graph.add_edge("product_retrieval", END)
        graph.add_edge("eligibility", END)
        graph.add_edge("comparison", END)
        graph.add_edge("explanation", END)
        
        self._graph = graph.compile()
        return self._graph

    def visualize(self):
        if not self._graph:
            self.build_graph()
        return self._graph.get_graph().to_dict()
