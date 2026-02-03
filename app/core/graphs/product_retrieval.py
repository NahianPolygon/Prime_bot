from langgraph.graph import StateGraph, START, END
from typing import Literal, Optional
import logging
from app.core.config import llm
from app.models.conversation_state import ConversationState
from app.services.product_retriever import ProductRetrieverService
from app.services.rag_retriever import RAGRetriever
from app.core.graphs.configs import ProductGuideConfig
from app.prompts.product_retrieval.slot_extraction import SLOT_EXTRACTION_PROMPT
from app.prompts.product_retrieval.slot_questions import GENERATE_SLOT_QUESTION_PROMPT
from app.prompts.product_retrieval.recommendations import (
    DEPOSIT_RECOMMENDATION_PROMPT_TEMPLATE,
    CREDIT_CARD_RECOMMENDATION_PROMPT_TEMPLATE,
    LOANS_RECOMMENDATION_PROMPT_TEMPLATE
)

logger = logging.getLogger(__name__)

class ProductRetrievalGraph:
    def __init__(self, config: ProductGuideConfig):
        self.config = config
        self.llm = llm
        self.retriever = ProductRetrieverService()
        self.rag = RAGRetriever()
        
    def collect_slot_node(self, state: ConversationState) -> dict:
        missing_slots = self._get_missing_slots(state)
        logger.info(f"🎯 [PRODUCT_RETRIEVAL] Missing slots: {missing_slots}")
        
        if not missing_slots:
            logger.info(f"✅ [PRODUCT_RETRIEVAL] All slots collected, proceeding to search")
            return {
                "response": f"Perfect! I have all the information I need. Let me find the best {self.config.display_name} for you.",
                "next_action": "search"
            }
        
        # Extract values from user's last message for ALL missing slots
        user_message = state.conversation_history[-1]["content"] if state.conversation_history else ""
        user_message_lower = user_message.lower()
        logger.info(f"📝 [PRODUCT_RETRIEVAL] User message: {user_message}")
        
        updates = {}
        extracted_slots = []
        
        # AGGRESSIVE EXTRACTION: Try to extract ALL missing slots from current message
        for slot in self.config.slots:
            if slot.name in missing_slots:
                # Try to extract slot value from user message
                extracted_value = self._extract_slot_value(slot, user_message_lower, state)
                logger.info(f"🔍 [PRODUCT_RETRIEVAL] Slot {slot.name}: extracted={extracted_value}")
                if extracted_value:
                    # Update state with extracted value
                    setattr(state, slot.name, extracted_value)
                    updates[slot.name] = extracted_value
                    extracted_slots.append(slot.name)
                    logger.info(f"✅ [PRODUCT_RETRIEVAL] Extracted {slot.name} = {extracted_value}")
        
        logger.info(f"📦 [PRODUCT_RETRIEVAL] Extracted slots: {extracted_slots}, Updates: {updates}")
        
        # Recheck which slots are still missing
        remaining_missing = self._get_missing_slots(state)
        logger.info(f"🎯 [PRODUCT_RETRIEVAL] Still missing after extraction: {remaining_missing}")
        
        if not remaining_missing:
            logger.info(f"✅ [PRODUCT_RETRIEVAL] All slots now collected, proceeding to search")
            return {
                "response": f"Great! Let me find the best {self.config.display_name} for you.",
                "next_action": "search",
                **updates
            }
        
        # Ask for next missing slot (prioritize non-banking-type slots first)
        # This ensures we understand product intent before asking banking type
        non_banking_slots = [s for s in remaining_missing if s != "banking_type"]
        next_slot = non_banking_slots[0] if non_banking_slots else remaining_missing[0]
        
        slot_def = next(s for s in self.config.slots if s.name == next_slot)
        
        # Generate dynamic, context-aware question based on what we've learned so far
        question = self._generate_dynamic_question(slot_def, state, user_message)
        
        logger.info(f"🎯 [PRODUCT_RETRIEVAL] Asking for slot: {next_slot}")
        logger.info(f"   Question: {question}")
        
        return {
            "response": question,
            "next_action": "collect",
            "current_slot": next_slot,
            **updates
        }
    
    def search_products_node(self, state: ConversationState) -> dict:
        logger.info(f"🔍 [PRODUCT_RETRIEVAL] Searching {self.config.product_type}...")
        
        # Build search query from collected slot values and original inquiry
        # Find the original product inquiry from conversation history
        query_parts = []
        for msg in state.conversation_history:
            if msg.get("role") == "user":
                content = msg.get("content", "").lower()
                # Skip slot answers (single words like "Islamic", "Teacher", etc.)
                if len(content.split()) > 3 or any(word in content for word in ["want", "need", "save", "deposit", "credit", "loan"]):
                    query_parts.append(msg.get("content", ""))
        
        # Use the original inquiry if available, otherwise construct from slots
        if query_parts:
            query = query_parts[0]  # Use first substantial message
            # Add gender keywords if female and interested in health/locker benefits
            if state.gender and state.gender.lower() in ["female", "woman", "lady"]:
                if state.health_benefits_interest or state.locker_interest:
                    query = f"{query} women's health benefits locker"
        else:
            # Construct query from slot values
            query_parts = []
            if state.account_goal:
                query_parts.append(f"{state.account_goal} savings")
            if state.occupation:
                query_parts.append(f"for {state.occupation}")
            if state.gender and state.gender.lower() in ["female", "woman", "lady"]:
                query_parts.append("women")
            query = " ".join(query_parts) or f"{self.config.display_name}"
        
        # Normalize banking_type for metadata matching
        banking_type = state.banking_type
        if banking_type:
            # Map user inputs to metadata values
            if banking_type.lower() in ["islamic", "islam"]:
                banking_type = "islami"
            elif banking_type.lower() in ["conventional", "conventional banking"]:
                banking_type = "conventional"
        
        logger.info(f"📝 [PRODUCT_RETRIEVAL] Search query: {query}")
        logger.info(f"🔍 [PRODUCT_RETRIEVAL] Filters: banking_type={banking_type}")
        
        products = self.retriever.search_products(
            query=query,
            banking_type=banking_type,
            top_k=5
        )
        
        logger.info(f"✅ [PRODUCT_RETRIEVAL] Found {len(products)} products")
        
        # For deposits: If customer is 50+ with health/locker interests, add targeted 50+ account search
        if self.config.product_type == "deposits" and state.age and state.age >= 50:
            if state.health_benefits_interest or state.locker_interest:
                logger.info(f"🎯 [PRODUCT_RETRIEVAL] Customer is 50+ with health/locker interests - searching for 50+ accounts")
                fifty_plus_products = self.retriever.search_products(
                    query="50 plus account senior savings health benefits locker",
                    banking_type=banking_type,
                    top_k=3
                )
                if fifty_plus_products:
                    logger.info(f"✅ [PRODUCT_RETRIEVAL] Found {len(fifty_plus_products)} 50+ specific products")
                    # Merge: prioritize 50+ products at the top
                    products = fifty_plus_products + products
        
        return {
            "matched_products": products,
            "next_action": "recommend"
        }
    
    def recommend_products_node(self, state: ConversationState) -> dict:
        if not state.matched_products:
            return {
                "response": f"I couldn't find suitable {self.config.display_name} matching your criteria. Could you provide more details?",
                "last_agent": "product_retrieval"
            }
        
        products_text = "\n".join([
            f"- {p.get('name')}: {p.get('knowledge_chunks', [''])[0][:100] if p.get('knowledge_chunks') else 'No details'}"
            for p in state.matched_products[:3]
        ])
        
        slot_values = {slot.name: getattr(state, slot.name, None) or "Not specified" 
                      for slot in self.config.slots}
        
        prompt = self.config.recommendation_prompt_template.format(
            **slot_values,
            income=state.user_profile.income_yearly or "Not specified",
            products=products_text
        )
        
        try:
            response = self.llm.invoke(prompt)
            return {
                "response": response.content,
                "last_agent": "product_retrieval"
            }
        except Exception as e:
            logger.error(f"Error in recommendation: {e}")
            product_names = [p.get('name') for p in state.matched_products[:3]]
            return {
                "response": f"Based on your needs, I recommend: {', '.join(product_names)}",
                "last_agent": "product_retrieval"
            }
    
    
    def route_from_collect(self, state: ConversationState) -> Literal["ask_slot", "search"]:
        """After collecting slots, decide: ask next slot or search"""
        missing_slots = self._get_missing_slots(state)
        
        if missing_slots:
            return "ask_slot"  # Still asking, go to END and wait
        else:
            return "search"  # All collected, proceed to search
    
    def build_graph(self):
        graph = StateGraph(ConversationState)
        
        graph.add_node("collect_slot", self.collect_slot_node)
        graph.add_node("search_products", self.search_products_node)
        graph.add_node("recommend_products", self.recommend_products_node)
        
        graph.add_edge(START, "collect_slot")
        
        # Route from collect_slot: if asking for slot, go to END. If no slots, go to search.
        graph.add_conditional_edges("collect_slot", self.route_from_collect, {
            "ask_slot": END,  # End here, wait for user answer
            "search": "search_products"
        })
        
        graph.add_edge("search_products", "recommend_products")
        graph.add_edge("recommend_products", END)
        
        return graph.compile()
    
    def invoke(self, state: ConversationState):
        graph = self.build_graph()
        return graph.invoke(state)
    
    def _get_missing_slots(self, state: ConversationState) -> list:
        """Get missing slots - all slots are required for most specific recommendations"""
        missing = []
        for slot in self.config.slots:
            if not getattr(state, slot.name, None):
                missing.append(slot.name)
        return missing
    
    def _extract_slot_value(self, slot_def, user_message: str, state: ConversationState) -> Optional[str]:
        """Extract slot value using intelligent LLM-based extraction - NO hardcoded logic"""
        import json
        
        # Build intelligent extraction prompt that understands the product context
        extraction_prompt = SLOT_EXTRACTION_PROMPT.format(
            slot_name=slot_def.name,
            product_type=self.config.product_type,
            product_display_name=self.config.display_name,
            collected_slots=self._get_collected_slots_summary(state),
            user_message=user_message,
            current_slot=state.current_slot,
            slot_question=slot_def.question,
            valid_options=', '.join(slot_def.keywords) if slot_def.keywords else 'Any value (no restrictions)'
        )

        try:
            response = self.llm.invoke(extraction_prompt)
            result_text = response.content.strip()
            
            # Parse JSON - remove markdown if present
            if '```' in result_text:
                result_text = result_text.split('```')[1]
                if result_text.startswith('json'):
                    result_text = result_text[4:]
            
            result = json.loads(result_text)
            extracted_value = result.get('value')
            confidence = result.get('confidence', 0)
            reasoning = result.get('reasoning', '')
            
            # Aggressive extraction: threshold is 0.35 to catch weak signals
            if extracted_value and confidence > 0.35:
                logger.info(f"✅ [LLM EXTRACTION] {slot_def.name}='{extracted_value}' (conf:{confidence:.2f}) - {reasoning}")
                return extracted_value
            else:
                logger.info(f"❌ [LLM EXTRACTION] {slot_def.name} not found (conf:{confidence:.2f})")
                return None
                
        except Exception as e:
            logger.warning(f"⚠️  [LLM EXTRACTION] Failed for {slot_def.name}: {e}")
            return None
    
    def _get_collected_slots_summary(self, state: ConversationState) -> str:
        """Get summary of already collected slots for context"""
        collected = []
        for slot in self.config.slots:
            value = getattr(state, slot.name, None)
            if value:
                collected.append(f"{slot.name}={value}")
        return ", ".join(collected) if collected else "None yet"
    
    def _generate_dynamic_question(self, slot_def, state: ConversationState, context: str) -> str:
        """Generate contextual, natural questions using intelligent prompting"""
        
        # Build context from already-collected slots
        context_summary = []
        for slot in self.config.slots:
            value = getattr(state, slot.name, None)
            if value:
                context_summary.append(f"✓ {slot.name}: {value}")
        
        prompt = GENERATE_SLOT_QUESTION_PROMPT.format(
            slot_name=slot_def.name,
            product_display_name=self.config.display_name,
            user_context=context,
            already_collected='\n'.join(context_summary) if context_summary else '(Just getting started)',
            valid_options=', '.join(slot_def.keywords) if slot_def.keywords else 'Any specific value'
        )

        try:
            response = self.llm.invoke(prompt)
            question = response.content.strip().strip('"').strip("'")
            logger.info(f"✅ [DYNAMIC QUESTION] Generated for {slot_def.name}: {question[:80]}...")
            return question
        except Exception as e:
            logger.warning(f"⚠️  [DYNAMIC QUESTION] Failed, using default: {e}")
            return slot_def.question
