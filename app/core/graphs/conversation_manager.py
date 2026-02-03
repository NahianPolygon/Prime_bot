from langgraph.graph import StateGraph, START, END
from typing import Literal
import logging
import json
from app.core.config import llm
from app.models.conversation_state import ConversationState
from app.services.inquiry_classifier import InquiryClassifier
from app.services.rag_retriever import RAGRetriever
from app.core.graphs.product_retrieval import ProductRetrievalGraph
from app.core.graphs.configs import DEPOSIT_ACCOUNTS_CONFIG, CREDIT_CARDS_CONFIG, LOANS_CONFIG
from app.prompts.conversation.greeting import GREETING_RESPONSE_PROMPT
from app.prompts.conversation.product_detection import DETECT_PRODUCT_TYPE_PROMPT
from app.prompts.conversation.comparison import PREPARE_COMPARISON_PROMPT, COMPARISON_CLARIFICATION_PROMPT
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
        self._graph = None

    def classify_intent_node(self, state: ConversationState) -> dict:
        # If we're in the middle of product retrieval, skip classification and continue the flow
        logger.info(f"🔍 [CLASSIFY] Checking product_type_in_progress: {state.product_type_in_progress}")
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
        user_message = state.conversation_history[-1]["content"]
        
        rag_chunks = self.rag.retrieve(user_message, top_k=5)
        products = [{"name": chunk.get("metadata", {}).get("product_name", "Product"), 
                    "knowledge_chunks": [chunk.get("chunk", "")]} for chunk in rag_chunks]
        
        if len(products) < 2:
            return {
                "response": "I need at least 2 products to compare. Let me search for more options.",
                "last_agent": "comparison"
            }
        
        product_names = [p.get('name') for p in products[:3]]
        chunks = "\n".join(["\n".join(p.get('knowledge_chunks', [])) for p in products[:3] if p.get('knowledge_chunks')])
        
        # Check if user mentioned specific product/banking types
        message_lower = user_message.lower()
        product_keywords = ["deposit", "savings", "credit card", "card", "loan", "investment", "scheme"]
        banking_keywords = ["conventional", "islamic", "islami", "shariah"]
        
        has_product_mention = any(kw in message_lower for kw in product_keywords)
        has_banking_mention = any(kw in message_lower for kw in banking_keywords)
        
        # If too vague, ask for clarification
        if not has_product_mention and not has_banking_mention:
            return {
                "response": COMPARISON_CLARIFICATION_PROMPT,
                "last_agent": "comparison"
            }
        
        prompt = PREPARE_COMPARISON_PROMPT.format(
            num_products=len(product_names),
            user_message=user_message,
            product_names=', '.join(product_names),
            chunks=chunks if chunks else 'Product details available in system'
        )
        
        try:
            response = self.llm.invoke(prompt)
            return {
                "response": response.content,
                "comparison_mode": True,
                "last_agent": "comparison"
            }
        except Exception as e:
            logger.error(f"Error in comparison: {e}")
            return {
                "response": f"Comparing {', '.join(product_names[:2])} for you...",
                "comparison_mode": True,
                "last_agent": "comparison"
            }

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
        
        if intent == "GREETING":
            return "greeting"
        elif intent == "COMPARISON_QUERY":
            return "comparison"
        elif intent == "ELIGIBILITY_QUERY":
            return "eligibility"
        elif intent == "PRODUCT_INFO_QUERY":
            return "product_retrieval"
        
        return "explanation"

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
