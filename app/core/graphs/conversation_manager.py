from langgraph.graph import StateGraph, START, END
from typing import Literal
from app.core.config import llm
from app.models.conversation_state import ConversationState
from app.models.graphs import IntentClassification, SlotRequirements
from app.core.graphs.slot_collection import SlotCollectionGraph
from app.core.graphs.eligibility import EligibilityGraph
from app.core.graphs.product_retrieval import ProductRetrievalGraph
from app.core.graphs.comparison import ComparisonGraph
from app.core.graphs.rag_explanation import RAGExplanationGraph
from app.prompts.conversation_manager import INTENT_PROMPT, SLOT_VALIDATION_PROMPT, GREETING_PROMPT
from app.prompts.slot_collection import EXTRACT_SLOT_PROMPT
from app.models.graphs import SlotExtractionResult
from app.services.product_matcher import ProductMatcher
from app.services.knowledge_cache import KnowledgeBaseCache
from app.services.inquiry_classifier import InquiryClassifier
import json
import logging

logger = logging.getLogger(__name__)


class ConversationManagerGraph:
    def __init__(self):
        self.llm = llm
        self._graph = None
        self.slot_collection_graph = SlotCollectionGraph()
        self.eligibility_graph = EligibilityGraph()
        self.product_retrieval_graph = ProductRetrievalGraph()
        self.comparison_graph = ComparisonGraph()
        self.rag_explanation_graph = RAGExplanationGraph()
        self.product_matcher = ProductMatcher(llm)
        self.kb_cache = KnowledgeBaseCache.get_instance()


    def extract_slot_if_needed_node(self, state: ConversationState) -> dict:
        """Extract slot value if we're responding to a slot collection prompt"""
        logger.info(f"🔨 [EXTRACT_SLOT] Node entered - Missing slots: {state.missing_slots}")
        
        if not state.missing_slots or state.missing_slots == []:
            logger.info(f"✅ [EXTRACT_SLOT] No missing slots - skipping extraction")
            return {}
        
        # Check if we have a current_slot being asked
        current_slot = state.missing_slots[0] if state.missing_slots else None
        if not current_slot:
            logger.info(f"⚠️  [EXTRACT_SLOT] No current slot identified")
            return {}
        
        user_message = state.conversation_history[-1]["content"] if state.conversation_history else ""
        
        try:
            slot_types = {
                "age": "numeric",
                "income_monthly": "numeric",
                "income_yearly": "numeric",
                "deposit": "numeric",
                "employment_type": "categorical",
                "banking_type": "categorical",
                "product_category": "categorical"
            }

            prompt = EXTRACT_SLOT_PROMPT.format(
                slot_name=current_slot,
                user_message=user_message,
                slot_type=slot_types.get(current_slot, "string")
            )

            logger.info(f"🔨 [EXTRACT_SLOT] Extracting value for slot: {current_slot}")
            structured_llm = self.llm.with_structured_output(SlotExtractionResult)
            result = structured_llm.invoke(prompt)
            logger.info(f"📊 [EXTRACT_SLOT] LLM response - Valid: {result.is_valid}, Confidence: {result.confidence}, Value: {result.extracted_value}")

            updates = {}
            if result.is_valid and result.confidence > 0.5:
                logger.info(f"✅ [EXTRACT_SLOT] ACCEPTED - Extracted value: {result.extracted_value} (confidence: {result.confidence})")
                
                if current_slot == "age":
                    updates["user_profile"] = state.user_profile.model_copy(
                        update={"age": int(float(result.extracted_value))}
                    )
                elif current_slot == "income_monthly":
                    updates["user_profile"] = state.user_profile.model_copy(
                        update={"income_monthly": float(result.extracted_value)}
                    )
                elif current_slot == "income_yearly":
                    updates["user_profile"] = state.user_profile.model_copy(
                        update={"income_yearly": float(result.extracted_value)}
                    )
                elif current_slot == "employment_type":
                    updates["user_profile"] = state.user_profile.model_copy(
                        update={"employment_type": result.extracted_value.lower()}
                    )
                elif current_slot == "banking_type":
                    updates["banking_type"] = result.extracted_value.lower()
                elif current_slot == "product_category":
                    updates["product_category"] = result.extracted_value.lower()
                
                new_slots = state.missing_slots.copy()
                new_slots.pop(0)
                updates["missing_slots"] = new_slots
                logger.info(f"✅ [EXTRACT_SLOT] Removed '{current_slot}' from missing slots - Remaining: {new_slots}")
            else:
                logger.warning(f"❌ [EXTRACT_SLOT] REJECTED - is_valid={result.is_valid}, confidence={result.confidence} (need > 0.5) for value: {result.extracted_value}")

            return updates
        except Exception as e:
            logger.error(f"❌ [EXTRACT_SLOT] Error: {str(e)}", exc_info=True)
            return {}

    def classify_intent_node(self, state: ConversationState) -> dict:
        logger.info(f"🔷 [CLASSIFY_INTENT] Starting intent classification...")
        
        if state.intent and state.missing_slots:
            logger.info(f"✅ [CLASSIFY_INTENT] Intent already set to '{state.intent}' during slot collection - preserving it")
            return {
                "intent": state.intent,
                "banking_type": state.banking_type,
                "product_category": state.product_category,
                "last_agent": "classify_intent"
            }
        
        message = state.conversation_history[-1]["content"] if state.conversation_history else ""
        history = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in state.conversation_history[-3:]
        ])

        prompt = INTENT_PROMPT.format(
            user_message=message,
            history=history or "No prior history"
        )
        logger.info(f"📝 [CLASSIFY_INTENT] Calling LLM for intent detection...")

        structured_llm = self.llm.with_structured_output(IntentClassification)
        result = structured_llm.invoke(prompt)
        logger.info(f"✅ [CLASSIFY_INTENT] Intent classified: {result.intent} | Banking Type: {result.banking_type} | Category: {result.product_category}")

        
        message_lower = message.lower()
        has_explicit_banking_type = any(word in message_lower for word in ["conventional", "islami", "islamic", "shariah", "sharia"])
        
        
        banking_type = result.banking_type if has_explicit_banking_type else None
        if not has_explicit_banking_type:
            logger.info(f"📝 [CLASSIFY_INTENT] User didn't explicitly mention banking type - will ask later")

        return {
            "intent": result.intent,
            "banking_type": banking_type,
            "product_category": result.product_category,
            "last_agent": "classify_intent"
        }

    def validate_slots_node(self, state: ConversationState) -> dict:
        logger.info(f"🔶 [VALIDATE_SLOTS] Validating required slots for intent: {state.intent}")
        history = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in state.conversation_history[-3:]
        ])
        profile = json.dumps(state.user_profile.model_dump(), default=str)

        prompt = SLOT_VALIDATION_PROMPT.format(
            intent=state.intent,
            profile=profile,
            history=history
        )
        logger.info(f"📝 [VALIDATE_SLOTS] Calling LLM for slot validation...")

        structured_llm = self.llm.with_structured_output(SlotRequirements)
        result = structured_llm.invoke(prompt)
        
        filtered_slots = []
        
        # ALWAYS ask for banking_type first if not set
        if not state.banking_type:
            logger.info(f"🔴 [VALIDATE_SLOTS] Banking type NOT set - adding to front of queue (PRIORITY)")
            filtered_slots.append("banking_type")
        
        # Then filter other slots that have already been extracted
        for slot in result.missing_slots:
            if slot == "banking_type":
                # Skip banking_type from LLM list if we already added it above
                if state.banking_type:
                    logger.info(f"⏭️  [VALIDATE_SLOTS] Skipping 'banking_type' - already extracted: {state.banking_type}")
                continue
            if slot == "age" and state.user_profile.age:
                logger.info(f"⏭️  [VALIDATE_SLOTS] Skipping 'age' - already extracted: {state.user_profile.age}")
                continue
            if slot == "income_monthly" and state.user_profile.income_monthly:
                logger.info(f"⏭️  [VALIDATE_SLOTS] Skipping 'income_monthly' - already extracted: {state.user_profile.income_monthly}")
                continue
            if slot == "income_yearly" and state.user_profile.income_yearly:
                logger.info(f"⏭️  [VALIDATE_SLOTS] Skipping 'income_yearly' - already extracted: {state.user_profile.income_yearly}")
                continue
            if slot == "employment_type" and state.user_profile.employment_type:
                logger.info(f"⏭️  [VALIDATE_SLOTS] Skipping 'employment_type' - already extracted: {state.user_profile.employment_type}")
                continue
            if slot == "product_category" and state.product_category:
                logger.info(f"⏭️  [VALIDATE_SLOTS] Skipping 'product_category' - already extracted: {state.product_category}")
                continue
            filtered_slots.append(slot)
        
        logger.info(f"✅ [VALIDATE_SLOTS] Missing slots (after filtering, priority order): {filtered_slots} | Reason: {result.reason}")

        return {
            "missing_slots": filtered_slots,
            "last_agent": "validate_slots"
        }

    def route_to_subgraph_node(self, state: ConversationState) -> dict:
        logger.info(f"🏠 [ROUTE_SUBGRAPH] Routing to appropriate subgraph...")
        state_dict = state.model_dump() if isinstance(state, ConversationState) else state
        
        try:
            if state.missing_slots:
                logger.info(f"📋 [ROUTE_SUBGRAPH] Missing slots detected: {state.missing_slots} → Invoking SlotCollectionGraph")
                result_dict = self.slot_collection_graph.invoke(state_dict)
            elif state.intent == "eligibility":
                logger.info(f"📋 [ROUTE_SUBGRAPH] Intent is 'eligibility' → Invoking EligibilityGraph")
                result_dict = self.eligibility_graph.invoke(state_dict)
            elif state.intent == "compare":
                logger.info(f"📋 [ROUTE_SUBGRAPH] Intent is 'compare' → Invoking ComparisonGraph")
                result_dict = self.comparison_graph.invoke(state_dict)
            elif state.intent == "explain":
                logger.info(f"📋 [ROUTE_SUBGRAPH] Intent is 'explain' → Invoking RAGExplanationGraph")
                result_dict = self.rag_explanation_graph.invoke(state_dict)
            else:
                logger.info(f"📋 [ROUTE_SUBGRAPH] Default intent → Invoking ProductRetrievalGraph")
                result_dict = self.product_retrieval_graph.invoke(state_dict)
            
            logger.info(f"✅ [ROUTE_SUBGRAPH] Subgraph execution completed")
            result_state = ConversationState(**result_dict) if isinstance(result_dict, dict) else result_dict
        except Exception as e:
            logger.error(f"❌ [ROUTE_SUBGRAPH] Subgraph error: {type(e).__name__}: {str(e)}", exc_info=True)
            return {
                "response": f"I encountered an error: {str(e)}. Please try again.",
                "last_agent": "route_to_subgraph_error"
            }
        
        return {
            "user_profile": result_state.user_profile,
            "missing_slots": result_state.missing_slots if result_state.missing_slots else [],
            "response": result_state.response,
            "eligible_products": result_state.eligible_products if result_state.eligible_products else [],
            "comparison_mode": result_state.comparison_mode,
            "banking_type": result_state.banking_type,
            "product_category": result_state.product_category,
            "last_agent": "route_to_subgraph"
        }

    def classify_inquiry_type_node(self, state: ConversationState) -> dict:
        logger.info(f"⚡ [CLASSIFY_INQUIRY] Pattern-based classification (fast)")
        
        message = state.conversation_history[-1]["content"] if state.conversation_history else ""
        
        classification = InquiryClassifier.classify(message)
        logger.info(f"✅ [CLASSIFY_INQUIRY] Type: {classification.inquiry_type}, Confidence: {classification.confidence}")
        
        if classification.inquiry_type == "GREETING":
            greeting_prompt = GREETING_PROMPT.format(user_message=message)
            greeting_response = self.llm.invoke(greeting_prompt)
            return {
                "response": greeting_response.content,
                "inquiry_type": "GREETING",
                "inquiry_confidence": classification.confidence,
                "last_agent": "classify_inquiry"
            }
        
        return {
            "inquiry_type": classification.inquiry_type,
            "inquiry_confidence": classification.confidence,
            "extracted_context": classification.extracted_context.model_dump(),
            "last_agent": "classify_inquiry"
        }

    def product_matcher_node(self, state: ConversationState) -> dict:
        logger.info(f"🎯 [PRODUCT_MATCHER] Starting product matching for credit cards...")
        
        try:
            context_dict = state.extracted_context or {}
            from app.services.product_matcher import ExtractedContext
            context = ExtractedContext(**context_dict)
            
            logger.info(f"📝 [PRODUCT_MATCHER] Extracted context: banking_type={context.banking_type}, employment={context.employment}, keywords={context.keywords}")
            
            products = self.kb_cache.get_credit_cards(context.banking_type)
            logger.info(f"📦 [PRODUCT_MATCHER] Loaded {len(products)} products from knowledge base")
            
            matched_products = self.product_matcher.filter_credit_cards(products, context)
            logger.info(f"✅ [PRODUCT_MATCHER] Matched {len(matched_products)} products after filtering")
            
            user_query = state.conversation_history[-1]["content"] if state.conversation_history else ""
            response = self.product_matcher.format_products_response(matched_products, user_query)
            
            return {
                "response": response,
                "matched_products": matched_products,
                "last_agent": "product_matcher"
            }
        except Exception as e:
            logger.error(f"❌ [PRODUCT_MATCHER] Error: {str(e)}")
            return {
                "response": "I couldn't retrieve product information. Please try again.",
                "matched_products": [],
                "last_agent": "product_matcher_error"
            }

    def build_graph(self):
        graph = StateGraph(ConversationState)
        
        graph.add_node("classify_inquiry", self.classify_inquiry_type_node)
        graph.add_node("product_matcher", self.product_matcher_node)
        graph.add_node("extract_slot", self.extract_slot_if_needed_node)
        graph.add_node("classify_intent", self.classify_intent_node)
        graph.add_node("validate_slots", self.validate_slots_node)
        graph.add_node("route_to_subgraph", self.route_to_subgraph_node)
        
        graph.add_edge(START, "classify_inquiry")
        
        def route_after_inquiry(state: ConversationState) -> str:
            inquiry_type = state.inquiry_type
            confidence = state.inquiry_confidence
            
            # If it's a greeting, end immediately
            if inquiry_type == "GREETING":
                logger.info(f"🎯 [ROUTE] Greeting detected → END")
                return END
            
            if confidence >= 0.7 and inquiry_type == "PRODUCT_INFO_QUERY":
                logger.info(f"🎯 [ROUTE] FAQ Query detected (confidence: {confidence}) → Product Matcher")
                return "product_matcher"
            
            if confidence >= 0.7 and inquiry_type == "MIXED_QUERY":
                logger.info(f"🎯 [ROUTE] Mixed Query detected (confidence: {confidence}) → Product Matcher")
                return "product_matcher"
            
            logger.info(f"🎯 [ROUTE] Eligibility Query (confidence: {confidence}) → Slot Extraction")
            return "extract_slot"
        
        graph.add_conditional_edges("classify_inquiry", route_after_inquiry, {
            END: END,
            "product_matcher": "product_matcher",
            "extract_slot": "extract_slot"
        })
        
        graph.add_edge("product_matcher", END)
        graph.add_edge("extract_slot", "classify_intent")
        graph.add_edge("classify_intent", "validate_slots")
        graph.add_edge("validate_slots", "route_to_subgraph")
        graph.add_edge("route_to_subgraph", END)
        
        self._graph = graph.compile()
        return self._graph
        
        self._graph = graph.compile()
        return self._graph
    
    def visualize(self):
        if self._graph is None:
            self.build_graph()
        mermaid_dict = self._graph.get_graph().to_dict()
        return mermaid_dict
    
    def invoke(self, state: ConversationState) -> ConversationState:
        graph = self.build_graph()
        result = graph.invoke(state)
        
        updated_fields = {
            "intent": result.get("intent", state.intent),
            "banking_type": result.get("banking_type", state.banking_type),
            "product_category": result.get("product_category", state.product_category),
            "user_profile": result.get("user_profile", state.user_profile),
            "missing_slots": result.get("missing_slots", state.missing_slots),
            "response": result.get("response", state.response),
            "eligible_products": result.get("eligible_products", state.eligible_products),
            "comparison_mode": result.get("comparison_mode", state.comparison_mode),
            "last_agent": result.get("last_agent", state.last_agent)
        }
        
        return ConversationState(**{**state.model_dump(), **updated_fields})
