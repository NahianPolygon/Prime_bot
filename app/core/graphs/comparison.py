from langgraph.graph import StateGraph, START, END
from typing import Literal, Optional
import logging
import json
from app.core.config import llm
from app.models.conversation_state import ConversationState
from app.services.rag_retriever import RAGRetriever
from app.prompts.conversation.comparison import (
    EXTRACT_PRODUCT_MENTIONS_PROMPT,
    CLARIFY_PRODUCTS_PROMPT,
    PERSONALIZED_COMPARISON_PROMPT,
    FILTER_PRODUCTS_EXPLANATION_PROMPT
)
from app.prompts.conversation.product_detection import DETECT_PRODUCT_TYPE_PROMPT
from app.core.graphs.configs import (
    DEPOSIT_COMPARISON_CONFIG,
    CREDIT_CARD_COMPARISON_CONFIG,
    LOAN_COMPARISON_CONFIG,
    ProductGuideConfig
)

logger = logging.getLogger(__name__)


class ComparisonGraph:
    def __init__(self):
        self.llm = llm
        self.rag = RAGRetriever()
        # Product-type specific comparison configs
        self.comparison_configs = {
            "deposits": DEPOSIT_COMPARISON_CONFIG,
            "credit_cards": CREDIT_CARD_COMPARISON_CONFIG,
            "loans": LOAN_COMPARISON_CONFIG
        }

    def _get_first_user_message(self, state: ConversationState) -> str:
        """Get the FIRST user message in conversation"""
        for msg in state.conversation_history:
            if msg.get("role") == "user":
                return msg.get("content", "")
        return ""

    def _get_last_user_message(self, state: ConversationState) -> str:
        """Get the LAST user message in conversation"""
        for msg in reversed(state.conversation_history):
            if msg.get("role") == "user":
                return msg.get("content", "")
        return ""

    def _detect_product_type(self, state: ConversationState) -> str:
        """Detect product type from conversation"""
        first_message = self._get_first_user_message(state)
        
        if not first_message:
            return "deposits"
        
        message_lower = first_message.lower()
        
        # Try LLM detection first
        try:
            prompt = DETECT_PRODUCT_TYPE_PROMPT.format(message=first_message)
            response = self.llm.invoke(prompt)
            detected = response.content.strip().lower()
            
            if detected in ["deposits", "credit_cards", "loans"]:
                logger.info(f"🔍 [COMPARISON] LLM detected product type: {detected}")
                return detected
        except Exception as e:
            logger.warning(f"⚠️ [COMPARISON] LLM detection failed: {e}")
        
        # Fallback: keyword matching
        if any(kw in message_lower for kw in ["save", "savings", "deposit", "account", "scheme", "dps", "fd"]):
            return "deposits"
        elif any(kw in message_lower for kw in ["credit card", "card", "cashback", "reward", "visa", "jcb"]):
            return "credit_cards"
        elif any(kw in message_lower for kw in ["loan", "borrow", "lending"]):
            return "loans"
        
        return "deposits"

    def _extract_products_from_message(self, message: str) -> list:
        """Extract product names from message"""
        logger.info(f"🧠 [COMPARISON] Extracting products from message")
        
        try:
            prompt = EXTRACT_PRODUCT_MENTIONS_PROMPT.format(user_message=message)
            response = self.llm.invoke(prompt)
            result_text = response.content.strip()
            
            # Handle markdown
            if result_text.startswith('```'):
                result_text = result_text.split('```')[1]
                if result_text.startswith('json'):
                    result_text = result_text[4:]
            
            result = json.loads(result_text)
            products = result.get('mentioned_products', [])
            logger.info(f"   Found products: {products}")
            return products
        except Exception as e:
            logger.warning(f"Product extraction failed: {e}")
            return []

    def _extract_slots_from_message(self, message: str, config: ProductGuideConfig, state: ConversationState = None) -> dict:
        """Extract slot values from message using LLM - ONLY extract slots that haven't been collected yet"""
        extracted = {}
        
        for slot_def in config.slots:
            # Skip if slot is already in state (don't overwrite existing values!)
            existing_value = getattr(state, slot_def.name, None) if state else None
            if existing_value:
                logger.info(f"⏭️ [COMPARISON] Skipping {slot_def.name} - already has value: {existing_value}")
                continue
            
            try:
                prompt = f"""Extract the value for "{slot_def.name}" from this message.
Message: "{message}"

Context: {slot_def.question}

Return ONLY the extracted value or "NOT_FOUND" if not in message. No explanations."""
                
                response = self.llm.invoke(prompt)
                value = response.content.strip()
                
                if value and value != "NOT_FOUND":
                    extracted[slot_def.name] = value
                    logger.info(f"✅ [COMPARISON] Extracted {slot_def.name}={value}")
            except Exception as e:
                logger.warning(f"Slot extraction failed for {slot_def.name}: {e}")
        
        return extracted

    def _get_missing_items(self, state: ConversationState, product_type: str, updates: dict = None) -> dict:
        """Get missing products and slots (checking both state and current updates)"""
        config = self.comparison_configs.get(product_type, DEPOSIT_COMPARISON_CONFIG)
        
        # Check if products exist in state or updates
        has_products_in_state = bool(state.comparison_products)
        has_products_in_updates = bool(updates and updates.get('comparison_products'))
        missing_products = not (has_products_in_state or has_products_in_updates)
        
        missing_slots = []
        for slot_def in config.slots:
            # Check both state and updates for the slot value
            state_value = getattr(state, slot_def.name, None)
            update_value = updates.get(slot_def.name) if updates else None
            has_value = state_value or update_value
            
            if not has_value:
                missing_slots.append(slot_def.name)
        
        return {
            "missing_products": missing_products,
            "missing_slots": missing_slots,
            "config": config
        }

    def unified_comparison_node(self, state: ConversationState) -> dict:
        """Unified node that extracts products and slots from EVERY message"""
        first_message = self._get_first_user_message(state)
        current_message = self._get_last_user_message(state)
        updates = {}
        
        # Detect product type (once, from first message)
        if not state.comparison_product_type:
            product_type = self._detect_product_type(state)
            updates["comparison_product_type"] = product_type
        else:
            product_type = state.comparison_product_type
        
        config = self.comparison_configs.get(product_type, DEPOSIT_COMPARISON_CONFIG)
        
        # Extract products from FIRST message (if not already found)
        if not state.comparison_products and first_message:
            products = self._extract_products_from_message(first_message)
            if products:
                logger.info(f"✅ Found products: {products}")
                # Search RAG for each product - FILTER to only requested products
                all_products = []
                for product_name in products:
                    rag_results = self.rag.retrieve(product_name, top_k=10)
                    for chunk in rag_results:
                        prod_name = chunk.get("metadata", {}).get("product_name", "")
                        prod_key = prod_name.lower().replace(" ", "_") if prod_name else ""
                        req_key = product_name.lower().replace(" ", "_")
                        
                        # FILTER: Only include products that match the extracted product names
                        if prod_key and req_key and (
                            prod_key == req_key or 
                            prod_name.lower().startswith(product_name.lower()) or
                            product_name.lower() in prod_name.lower()
                        ):
                            if prod_name and prod_name not in [p.get("name") for p in all_products]:
                                all_products.append({
                                    "name": prod_name,
                                    "knowledge_chunks": [chunk.get("chunk", "")],
                                    "banking_type": chunk.get("metadata", {}).get("banking_type", "")
                                })
                                logger.info(f"   ✓ Matched: {prod_name}")
                
                if len(all_products) >= 2:
                    updates["comparison_products"] = all_products[:10]
                    updates["products_identified"] = True
                    logger.info(f"✅ [COMPARISON] Found {len(all_products)} matching products")
                    
                    # INFER banking_type from matched products
                    banking_types = set()
                    for product in all_products:
                        if product.get("banking_type"):
                            banking_types.add(product.get("banking_type"))
                    
                    if len(banking_types) == 1:
                        # All products have same banking type → infer it!
                        inferred_type = banking_types.pop()
                        updates["comparison_banking_type"] = inferred_type
                        logger.info(f"🔍 [COMPARISON] Inferred banking_type from products: {inferred_type}")
                    elif len(banking_types) > 1:
                        # Mixed banking types - need to ask user
                        logger.info(f"⚠️ [COMPARISON] Products have mixed banking types: {banking_types}")
                else:
                    logger.info(f"⚠️ [COMPARISON] Need at least 2 products, found {len(all_products)}")
        
        # Extract slots from CURRENT message
        if current_message:
            extracted_slots = self._extract_slots_from_message(current_message, config, state)
            updates.update(extracted_slots)
        
        # Check what's missing (pass updates so newly extracted slots are considered)
        status = self._get_missing_items(state, product_type, updates)
        
        logger.info(f"📊 [COMPARISON] Status:")
        logger.info(f"   Products identified: {bool(state.comparison_products or updates.get('comparison_products'))}")
        logger.info(f"   Missing slots: {status['missing_slots']}")
        
        # If both products and slots complete → ready for comparison
        has_products = bool(state.comparison_products or updates.get('comparison_products'))
        missing_slots = status['missing_slots']
        
        if has_products and not missing_slots:
            logger.info(f"✅ [COMPARISON] All products and slots collected!")
            # Include all slots from state for conversation_manager
            for slot_def in config.slots:
                slot_value = getattr(state, slot_def.name, None) or updates.get(slot_def.name)
                if slot_value:
                    updates[slot_def.name] = slot_value
            updates["next_action"] = "generate_comparison"
            updates["response"] = f"Perfect! I have all the information I need. Let me generate a detailed comparison."
            return updates
        
        # Ask for next missing item
        if not has_products:
            updates["next_action"] = "clarify"
            updates["response"] = "I'd like to compare products for you. Which products would you like me to compare?"
            return updates
        
        if missing_slots:
            # Ask for next missing slot
            next_slot_name = missing_slots[0]
            next_slot = next((s for s in config.slots if s.name == next_slot_name), None)
            
            if next_slot:
                # Include all currently collected slots for conversation_manager to persist
                for slot_def in config.slots:
                    slot_value = getattr(state, slot_def.name, None) or updates.get(slot_def.name)
                    if slot_value:
                        updates[slot_def.name] = slot_value
                
                # CRITICAL: Ensure all extracted slots from updates are included in return
                logger.info(f"🔄 [COMPARISON] Including extracted slots: {[k for k in updates.keys() if k.startswith('comparison_')]}")
                
                updates["next_action"] = "collect_slots"
                updates["response"] = next_slot.question
                logger.info(f"🎯 [COMPARISON] Asking for: {next_slot_name}")
                return updates
        
        # Should not reach here
        updates["next_action"] = "end"
        return updates

    def clarify_products_node(self, state: ConversationState) -> dict:
        """Handle unclear product requests"""
        user_message = self._get_last_user_message(state)
        
        logger.info(f"🤔 [COMPARISON] Clarifying products")
        
        prompt = CLARIFY_PRODUCTS_PROMPT.format(
            user_message=user_message,
            age=state.age or "Not specified",
            occupation=state.occupation or "Not specified",
            banking_type=state.banking_type or "Not specified"
        )
        
        try:
            response = self.llm.invoke(prompt)
            return {
                "response": response.content,
                "last_agent": "comparison_clarify"
            }
        except Exception as e:
            logger.error(f"Clarification failed: {e}")
            return {
                "response": "I can help you compare deposits, credit cards, or loans. Which would you like to explore?",
                "last_agent": "comparison_clarify"
            }

    def generate_comparison_node(self, state: ConversationState) -> dict:
        """Generate the final comparison"""
        updates = {}
        
        logger.info(f"📊 [COMPARISON] Generating comparison for {len(state.comparison_products)} products")
        
        products_text = "\n".join([
            f"- **{p.get('name')}**: {(p.get('knowledge_chunks', [''])[0] if p.get('knowledge_chunks') else 'No details')[:200]}"
            for p in state.comparison_products[:5]
        ])
        
        # Build prompt with product-type specific slots
        slot_values = {}
        if state.comparison_product_type:
            config = self.comparison_configs.get(state.comparison_product_type, DEPOSIT_COMPARISON_CONFIG)
            for slot_def in config.slots:
                value = getattr(state, slot_def.name, None)
                slot_values[slot_def.name] = value or "Not specified"
        
        prompt = PERSONALIZED_COMPARISON_PROMPT.format(
            num_products=len(state.comparison_products),
            user_message=self._get_first_user_message(state),
            age=state.age or "Not specified",
            occupation=state.occupation or "Not specified",
            banking_type=state.banking_type or "Not specified",
            income=state.user_profile.income_yearly or "Not specified",
            goal=state.account_goal or "Not specified",
            deposit_frequency=slot_values.get('comparison_deposit_frequency', 'Not specified'),
            tenure_range=slot_values.get('comparison_tenure_range', 'Not specified'),
            purpose=slot_values.get('comparison_purpose', 'Not specified'),
            interest_priority=slot_values.get('comparison_interest_priority', 'Not specified'),
            flexibility_priority=slot_values.get('comparison_flexibility_priority', 'Not specified'),
            products_text=products_text
        )
        
        try:
            response = self.llm.invoke(prompt)
            updates["response"] = response.content
        except Exception as e:
            logger.error(f"Error generating comparison: {e}")
            product_names = [p.get('name') for p in state.comparison_products[:3]]
            updates["response"] = f"Here's a comparison of {', '.join(product_names)}:\n\nBased on your preferences, these are the key differences and recommendations."
        
        updates["last_agent"] = "comparison_generate"
        return updates

    def route_unified_node(self, state: ConversationState) -> Literal["generate_comparison", "clarify_products", "end"]:
        """Route from unified node"""
        if state.next_action == "generate_comparison":
            logger.info(f"✅ [ROUTE] → generate_comparison")
            return "generate_comparison"
        elif state.next_action == "clarify":
            logger.info(f"❓ [ROUTE] → clarify_products")
            return "clarify_products"
        else:
            logger.info(f"⏳ [ROUTE] → end (waiting for more info)")
            return "end"

    def build_graph(self):
        graph = StateGraph(ConversationState)
        
        # Simplified graph with unified node
        graph.add_node("process", self.unified_comparison_node)
        graph.add_node("clarify", self.clarify_products_node)
        graph.add_node("generate", self.generate_comparison_node)
        
        graph.add_edge(START, "process")
        
        # From process node, route based on status
        graph.add_conditional_edges("process", self.route_unified_node, {
            "generate_comparison": "generate",
            "clarify_products": "clarify",
            "end": END
        })
        
        # Both clarify and generate end the flow
        graph.add_edge("clarify", END)
        graph.add_edge("generate", END)
        
        return graph.compile()
    
    def invoke(self, state: ConversationState):
        graph = self.build_graph()
        return graph.invoke(state)
