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
        self.current_config: Optional[ProductGuideConfig] = None
        self.detected_product_type: Optional[str] = None
    
    def _detect_comparison_product_type(self, state: ConversationState) -> str:
        """Detect what product type user wants to compare (deposits, credit_cards, loans)"""
        message = state.conversation_history[-1]["content"] if state.conversation_history else ""
        
        if not message:
            return "deposits"
        
        message_lower = message.lower()
        
        # Try LLM-based detection first
        try:
            prompt = DETECT_PRODUCT_TYPE_PROMPT.format(message=message)
            response = self.llm.invoke(prompt)
            detected = response.content.strip().lower()
            
            # Validate response
            if detected in ["deposits", "credit_cards", "loans"]:
                logger.info(f"🔍 [COMPARISON] LLM detected product type: {detected}")
                return detected
        except Exception as e:
            logger.warning(f"⚠️ [COMPARISON] LLM detection failed: {e}. Using fallback keywords.")
        
        # Fallback: keyword matching
        if any(kw in message_lower for kw in ["save", "savings", "deposit", "account", "scheme", "dps", "recurring", "interest"]):
            logger.info(f"🔍 [COMPARISON] Keyword detected: deposits")
            return "deposits"
        elif any(kw in message_lower for kw in ["credit card", "card", "cashback", "reward", "lounge", "tier"]):
            logger.info(f"🔍 [COMPARISON] Keyword detected: credit_cards")
            return "credit_cards"
        elif any(kw in message_lower for kw in ["loan", "borrow", "lending", "home", "auto", "personal"]):
            logger.info(f"🔍 [COMPARISON] Keyword detected: loans")
            return "loans"
        
        return "deposits"  # Default fallback
    
    def _get_comparison_config(self, product_type: str) -> ProductGuideConfig:
        """Get product-type specific comparison config"""
        config = self.comparison_configs.get(product_type, DEPOSIT_COMPARISON_CONFIG)
        logger.info(f"✅ [COMPARISON] Using config for {product_type}: slots={[s.name for s in config.slots]}")
        return config
    
    def _get_missing_slots(self, state: ConversationState, config: ProductGuideConfig) -> list:
        """Get missing slots for the current product type"""
        missing = []
        for slot in config.slots:
            if not getattr(state, slot.name, None):
                missing.append(slot.name)
        return missing
    
    def _extract_slot_value_llm(self, slot_def, user_message: str, state: ConversationState, product_type: str) -> Optional[str]:
        """Extract slot value using LLM with product type context"""
        import json
        
        # Build collected slots summary
        collected_slots_summary = []
        for slot in self.current_config.slots:
            value = getattr(state, slot.name, None)
            if value:
                collected_slots_summary.append(f"{slot.name}={value}")
        collected_summary = ", ".join(collected_slots_summary) if collected_slots_summary else "None"
        
        extraction_prompt = f"""Extract the user's preference for: {slot_def.name}

Product Type: {product_type}
Product Category: {self.current_config.display_name}

Slot Description: {slot_def.question}
Valid Keywords: {', '.join(slot_def.keywords) if slot_def.keywords else 'Any value'}

User Message: "{user_message}"
Already Collected: {collected_summary}

Task: Extract the {slot_def.name} value if mentioned. Return JSON with:
{{"value": null or string value, "confidence": 0.0-1.0, "reasoning": "brief explanation"}}

If not mentioned, set value to null and confidence to 0.0.
RETURN ONLY JSON, NO MARKDOWN."""
        
        try:
            response = self.llm.invoke(extraction_prompt)
            result_text = response.content.strip()
            
            # Clean markdown if present
            if '```' in result_text:
                result_text = result_text.split('```')[1]
                if result_text.startswith('json'):
                    result_text = result_text[4:]
            result_text = result_text.strip()
            
            result = json.loads(result_text)
            extracted_value = result.get('value')
            confidence = result.get('confidence', 0.0)
            
            if extracted_value and confidence > 0.35:
                logger.info(f"✅ [COMPARISON] Extracted {slot_def.name}={extracted_value} (conf:{confidence:.2f})")
                return extracted_value
            
            logger.info(f"❌ [COMPARISON] {slot_def.name} not found (conf:{confidence:.2f})")
            return None
        
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ [COMPARISON] JSON parse error for {slot_def.name}: {e}")
            return None
        except Exception as e:
            logger.warning(f"⚠️ [COMPARISON] LLM extraction failed for {slot_def.name}: {e}")
            return None
    
    def collect_slots_node(self, state: ConversationState) -> dict:
        """Collect product-type-specific comparison slots"""
        user_message = state.conversation_history[-1]["content"] if state.conversation_history else ""
        updates = {}
        
        # Detect product type if not already detected
        if not self.detected_product_type:
            self.detected_product_type = self._detect_comparison_product_type(state)
            self.current_config = self._get_comparison_config(self.detected_product_type)
            logger.info(f"🎯 [COMPARISON] Detected product type: {self.detected_product_type}")
            updates["comparison_product_type"] = self.detected_product_type
            
            # On FIRST call, try to extract products from the original message
            if not state.comparison_products:
                logger.info(f"🔍 [COMPARISON] First call - attempting to extract product mentions from user message")
                extraction = self._extract_product_mentions(user_message)
                mentioned_products = extraction.get("mentioned_products", [])
                
                if mentioned_products:
                    logger.info(f"✅ [COMPARISON] Extracted {len(mentioned_products)} products: {mentioned_products}")
                    # Search RAG for these products
                    combined_search = " ".join(mentioned_products)
                    rag_results = self.rag.retrieve(combined_search, top_k=20)
                    
                    products_found = []
                    seen_names = set()
                    for chunk in rag_results:
                        name = chunk.get("metadata", {}).get("product_name", "")
                        if name and name not in seen_names:
                            products_found.append({
                                "name": name,
                                "knowledge_chunks": [chunk.get("chunk", "")],
                                "banking_type": chunk.get("metadata", {}).get("banking_type", "conventional")
                            })
                            seen_names.add(name)
                    
                    if len(products_found) >= 2:
                        updates["comparison_products"] = products_found[:5]
                        logger.info(f"✅ [COMPARISON] Found {len(products_found)} products, storing in state")
                    else:
                        logger.info(f"⚠️ [COMPARISON] Found {len(products_found)} products, need at least 2 - will ask later")
                else:
                    logger.info(f"ℹ️ [COMPARISON] No specific products mentioned - will ask after slots collected")
        
        # Check for direct comparison intent
        message_lower = user_message.lower()
        direct_keywords = ["compare", "versus", "vs", "difference", "feature", "detail"]
        is_direct = any(kw in message_lower for kw in direct_keywords)
        
        # For credit cards and loans: Skip slot collection for direct comparisons
        if self.detected_product_type in ["credit_cards", "loans"] and is_direct:
            logger.info(f"✅ [COMPARISON] Direct comparison for {self.detected_product_type} - skipping slots")
            updates["products_identified"] = False
            updates["next_action"] = "identify_products"
            return updates
        
        # Get missing slots for this product type
        missing_slots = self._get_missing_slots(state, self.current_config)
        logger.info(f"🎯 [COMPARISON] Missing slots: {missing_slots}")
        
        # AGGRESSIVE EXTRACTION: Try to extract ALL missing slots from current message
        for slot_def in self.current_config.slots:
            if slot_def.name in missing_slots:
                extracted_value = self._extract_slot_value_llm(slot_def, user_message, state, self.detected_product_type)
                if extracted_value:
                    updates[slot_def.name] = extracted_value
                    setattr(state, slot_def.name, extracted_value)
                    logger.info(f"✅ [COMPARISON] Extracted {slot_def.name}={extracted_value}")
        
        # Recheck missing slots after extraction
        remaining_missing = self._get_missing_slots(state, self.current_config)
        logger.info(f"🎯 [COMPARISON] Still missing: {remaining_missing}")
        
        # If all slots collected, proceed to product identification
        if not remaining_missing:
            logger.info(f"✅ [COMPARISON] All slots collected! Proceeding to product identification.")
            updates["response"] = f"Perfect! Let me find the best {self.current_config.display_name} for you to compare."
            updates["next_action"] = "identify_products"
            updates["comparison_product_type"] = self.detected_product_type
            return updates
        
        # Ask for next missing slot
        next_slot_def = next((s for s in self.current_config.slots if s.name in remaining_missing), None)
        if not next_slot_def:
            return updates
        
        # Generate dynamic question from config
        question = next_slot_def.question
        logger.info(f"🎯 [COMPARISON] Asking for slot: {next_slot_def.name}")
        
        updates["response"] = question
        updates["next_action"] = "collect_slots"
        updates["comparison_product_type"] = self.detected_product_type
        return updates
    
    def _extract_product_mentions(self, user_message: str) -> dict:
        """Use LLM to extract product mentions from comparison request"""
        logger.info(f"🧠 [COMPARISON] Extracting product mentions")
        
        prompt = EXTRACT_PRODUCT_MENTIONS_PROMPT.format(user_message=user_message)
        
        try:
            response = self.llm.invoke(prompt)
            result_text = response.content.strip()
            
            # Clean markdown code blocks if present
            if result_text.startswith('```'):
                result_text = result_text.split('```')[1]
                if result_text.startswith('json'):
                    result_text = result_text[4:]
            
            result = json.loads(result_text)
            
            logger.info(f"   Products: {result.get('mentioned_products', [])}")
            logger.info(f"   Confidence: {result.get('confidence', 0)}")
            
            return result
        
        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}. Returning empty result.")
            return {
                "mentioned_products": [],
                "comparison_intent": False,
                "confidence": 0.0,
                "reasoning": "Extraction failed"
            }
    
    def _filter_products_by_slots(self, products: list, state: ConversationState) -> list:
        """Filter products based on collected comparison slots"""
        if not products or not self.current_config:
            return products
        
        logger.info(f"🔍 [COMPARISON] Filtering {len(products)} products by collected slots")
        
        # For deposits: filter by frequency and tenure preference
        if self.detected_product_type == "deposits":
            filtered = products
            if state.comparison_deposit_frequency:
                logger.info(f"   Filtering by frequency: {state.comparison_deposit_frequency}")
            if state.comparison_tenure_range:
                logger.info(f"   Filtering by tenure: {state.comparison_tenure_range}")
            return filtered
        
        # For credit cards: filter by tier and spending preference
        elif self.detected_product_type == "credit_cards":
            filtered = products
            if state.comparison_card_tier:
                logger.info(f"   Filtering by tier: {state.comparison_card_tier}")
            if state.comparison_spending_pattern:
                logger.info(f"   Filtering by spending: {state.comparison_spending_pattern}")
            return filtered
        
        # For loans: filter by purpose and amount
        elif self.detected_product_type == "loans":
            filtered = products
            if state.comparison_loan_purpose:
                logger.info(f"   Filtering by purpose: {state.comparison_loan_purpose}")
            if state.comparison_loan_amount:
                logger.info(f"   Filtering by amount: {state.comparison_loan_amount}")
            return filtered
        
        return products
    
    def identify_products_node(self, state: ConversationState) -> dict:
        # Use the FIRST user message (the comparison request) not the last one
        # The last message is just the final slot answer (e.g., "Wealth building")
        first_user_message = None
        for msg in state.conversation_history:
            if msg.get("role") == "user":
                first_user_message = msg.get("content", "")
                break
        
        user_message = first_user_message or (state.conversation_history[-1]["content"] if state.conversation_history else "")
        updates = {}
        
        # Detect product type if not already detected
        if not self.detected_product_type:
            self.detected_product_type = self._detect_comparison_product_type(state)
            self.current_config = self._get_comparison_config(self.detected_product_type)
            logger.info(f"🎯 [COMPARISON] Detected product type in identify_products: {self.detected_product_type}")
            updates["comparison_product_type"] = self.detected_product_type
        
        products_to_compare = []
        source = ""
        
        # If products were already identified in collect_slots_node (on first message), use them
        if state.comparison_products and len(state.comparison_products) >= 2:
            logger.info(f"✅ [IDENTIFY] Products already found in collect_slots: {len(state.comparison_products)} products")
            products_to_compare = state.comparison_products
            source = "collect_slots_extraction"
        else:
            logger.info(f"🔍 [IDENTIFY] No products found yet, attempting extraction from first message")
            # This is fallback - product extraction should have happened in collect_slots_node
        
        # If user mentioned specific products, SEARCH RAG for them first
        if mentioned_products:
            logger.info(f"🔍 [COMPARISON] Searching RAG for {len(mentioned_products)} mentioned products")
            
            combined_search = " ".join(mentioned_products)
            rag_results = self.rag.retrieve(combined_search, top_k=20)
            
            seen_products = {}  # Map product_name to full product dict
            
            # 1. Collect all candidate products from RAG
            candidates = {}  # Map product_name to product_data
            for chunk in rag_results:
                name = chunk.get("metadata", {}).get("product_name", "")
                if name and name not in candidates:
                    candidates[name] = {
                        "name": name,
                        "knowledge_chunks": [chunk.get("chunk", "")],
                        "banking_type": chunk.get("metadata", {}).get("banking_type", "conventional")
                    }
            
            # 2. Match each mentioned product to the BEST candidate
            for mentioned in mentioned_products:
                mentioned_lower = mentioned.lower()
                best_match = None
                best_score = 0
                
                for cand_name, cand_data in candidates.items():
                    cand_name_friendly = cand_name.replace("prime_", "").replace("_", " ").lower()
                    
                    # Calculate simple overlap score
                    mentioned_words = set(w for w in mentioned_lower.split() if len(w) > 2)
                    cand_words = set(w for w in cand_name_friendly.split() if len(w) > 2)
                    
                    if not mentioned_words:
                        continue
                        
                    overlap = len(mentioned_words.intersection(cand_words))
                    score = overlap / len(mentioned_words)
                    
                    # Bonus for exact substring match
                    if mentioned_lower in cand_name_friendly:
                        score += 0.5
                    # Bonus for reverse substring
                    elif cand_name_friendly in mentioned_lower:
                        score += 0.3
                    
                    # Penalize if candidate has many extra words
                    if len(cand_words) > len(mentioned_words):
                        score -= 0.1 * (len(cand_words) - len(mentioned_words))

                    if score > best_score and score > 0.4:
                        best_score = score
                        best_match = cand_data
                
                if best_match:
                    product_name = best_match["name"]
                    if product_name not in seen_products:
                         seen_products[product_name] = best_match
                         logger.info(f"   ✓ Linked mention '{mentioned}' to product '{product_name}' (score={best_score:.2f})")

            
            if seen_products:
                products_to_compare = list(seen_products.values())
                source = "rag_mentioned_products"
                logger.info(f"✅ [COMPARISON] Found {len(products_to_compare)} products from RAG for mentioned products")
            else:
                # If no matches in RAG, try to filter matched_products
                logger.info(f"⚠️ [COMPARISON] No RAG matches found, trying to filter matched_products")
                if state.matched_products:
                    mentioned_lower = [p.lower() for p in mentioned_products]
                    
                    filtered_products = []
                    for product in state.matched_products:
                        product_name_lower = product.get("name", "").lower() if isinstance(product, dict) else str(product).lower()
                        # Check if product name matches any mentioned product
                        for mentioned in mentioned_lower:
                            if mentioned in product_name_lower or product_name_lower in mentioned:
                                filtered_products.append(product)
                                logger.info(f"   ✓ Matched: {product.get('name', product)} with mention '{mentioned}'")
                                break
                    
                    if filtered_products:
                        products_to_compare = filtered_products
                        source = "matched_products_filtered"
                        logger.info(f"✅ [COMPARISON] Filtered matched_products to {len(products_to_compare)} products")
                    else:
                        # Fallback: use all matched products
                        logger.info(f"⚠️ [COMPARISON] No filtered matches, using all matched products")
                        products_to_compare = state.matched_products[:5]
                        source = "matched_products"
        
        elif state.suggested_products and len(state.suggested_products) >= 2:
            logger.info(f"✅ [COMPARISON] Using suggested_products: {len(state.suggested_products)} products")
            products_to_compare = state.suggested_products[:5]
            source = "suggested_products"
        
        else:
            logger.info(f"🧠 [COMPARISON] Using LLM to extract product mentions")
            extraction = self._extract_product_mentions(user_message)
            mentioned_products = extraction.get("mentioned_products", [])
            
            if mentioned_products:
                logger.info(f"🔍 [COMPARISON] Searching for {len(mentioned_products)} mentioned products")
                
                combined_search = " ".join(mentioned_products)
                rag_results = self.rag.retrieve(combined_search, top_k=10)
                
                seen_products = set()
                for chunk in rag_results:
                    product_name = chunk.get("metadata", {}).get("product_name", "")
                    if product_name and product_name not in seen_products:
                        products_to_compare.append({
                            "name": product_name,
                            "knowledge_chunks": [chunk.get("chunk", "")],
                            "banking_type": chunk.get("metadata", {}).get("banking_type", "conventional")
                        })
                        seen_products.add(product_name)
                        logger.info(f"   ✓ Found: {product_name}")
                
                source = "llm_extracted_products"
            else:
                logger.info(f"🔍 [COMPARISON] LLM couldn't extract specific products, doing generic search")
                rag_results = self.rag.retrieve(user_message, top_k=10)
                seen_products = set()
                for chunk in rag_results:
                    product_name = chunk.get("metadata", {}).get("product_name", "")
                    if product_name and product_name not in seen_products:
                        products_to_compare.append({
                            "name": product_name,
                            "knowledge_chunks": [chunk.get("chunk", "")],
                            "banking_type": chunk.get("metadata", {}).get("banking_type", "conventional")
                        })
                        seen_products.add(product_name)
                source = "generic_rag_search"
        
        filtered_products = self._filter_products_by_slots(products_to_compare, state)
        
        if len(filtered_products) < 2:
            logger.info(f"⚠️ [COMPARISON] Found {len(filtered_products)} products, need at least 2")
            updates["products_identified"] = False
            updates["next_action"] = "clarify"
            updates["source"] = source
            return updates
        
        logger.info(f"✅ [COMPARISON] Identified {len(filtered_products)} products from {source}")
        updates["comparison_products"] = filtered_products[:5]
        updates["products_identified"] = True
        updates["next_action"] = "compare"
        updates["source"] = source
        return updates
    
    def clarify_products_node(self, state: ConversationState) -> dict:
        user_message = state.conversation_history[-1]["content"] if state.conversation_history else ""
        
        logger.info(f"🤔 [COMPARISON] Clarifying which products to compare by searching vector DB")
        
        # Search vector DB for products related to what user mentioned
        rag_results = self.rag.retrieve(user_message, top_k=10)
        
        # Extract unique product names from search results
        available_products = []
        seen = set()
        for chunk in rag_results:
            product_name = chunk.get("metadata", {}).get("product_name", "")
            if product_name and product_name not in seen:
                available_products.append(product_name)
                seen.add(product_name)
        
        logger.info(f"   Found {len(available_products)} available products from vector DB")
        
        # Build product list for prompt
        products_str = "\n".join([f"- {prod}" for prod in available_products[:5]])
        
        prompt = f"""The user wants to compare banking products. They said: "{user_message}"

Available products in our system that match their interest:
{products_str}

User context:
- Age: {state.age or "Not specified"}
- Occupation: {state.occupation or "Not specified"}
- Banking preference: {state.banking_type or "Not specified"}

Provide a helpful response that:
1. Acknowledges what they asked for
2. Lists the available options we found
3. Asks them to specify which 2-3 products they want to compare
4. Be conversational and brief

Keep it concise (2-3 sentences)."""
        
        try:
            response = self.llm.invoke(prompt)
            return {
                "response": response.content,
                "clarification_message": response.content,
                "last_agent": "comparison_clarify"
            }
        except Exception as e:
            logger.error(f"Error in clarification: {e}")
            
            # Fallback: directly show available products
            fallback = "I found several products that match your interest:\n"
            for product in available_products[:5]:
                fallback += f"- {product}\n"
            fallback += f"\nWhich ones would you like me to compare?"
            
            return {
                "response": fallback,
                "clarification_message": fallback,
                "last_agent": "comparison_clarify"
            }
    
    def generate_comparison_node(self, state: ConversationState) -> dict:
        user_message = state.conversation_history[-1]["content"] if state.conversation_history else ""
        updates = {}
        
        # Ensure product type is detected
        if not self.detected_product_type and state.comparison_product_type:
            self.detected_product_type = state.comparison_product_type
        
        logger.info(f"📊 [COMPARISON] Generating comparison for {len(state.comparison_products)} products")
        
        products_text = "\n".join([
            f"- **{p.get('name')}**: {(p.get('knowledge_chunks', [''])[0] if p.get('knowledge_chunks') else 'No details')[:200]}"
            for p in state.comparison_products[:5]
        ])
        
        prompt = PERSONALIZED_COMPARISON_PROMPT.format(
            num_products=len(state.comparison_products),
            user_message=user_message,
            age=state.age or "Not specified",
            occupation=state.occupation or "Not specified",
            banking_type=state.banking_type or "Not specified",
            income=state.user_profile.income_yearly or "Not specified",
            goal=state.account_goal or "Not specified",
            deposit_frequency=state.comparison_deposit_frequency or "Not specified",
            tenure_range=state.comparison_tenure_range or "Not specified",
            purpose=state.comparison_purpose or "Not specified",
            interest_priority=state.comparison_interest_priority or "Not specified",
            flexibility_priority=state.comparison_flexibility_priority or "Not specified",
            products_text=products_text
        )
        
        try:
            response = self.llm.invoke(prompt)
            updates["response"] = response.content
            updates["last_agent"] = "comparison_generate"
            if self.detected_product_type:
                updates["comparison_product_type"] = self.detected_product_type
            return updates
        except Exception as e:
            logger.error(f"Error in comparison generation: {e}")
            product_names = [p.get('name') for p in state.comparison_products[:3]]
            updates["response"] = f"Here's a comparison of {', '.join(product_names)}:\n\nBased on your profile and preferences, I recommend considering the features that best match your needs."
            updates["last_agent"] = "comparison_generate"
            if self.detected_product_type:
                updates["comparison_product_type"] = self.detected_product_type
            return updates
    
    def route_comparison(self, state: ConversationState) -> Literal["clarify", "compare"]:
        if state.products_identified:
            return "compare"
        else:
            return "clarify"
    
    def route_slot_collection(self, state: ConversationState) -> Literal["identify_products", "end"]:
        """Route based on whether slots are collected or if we should skip to product identification"""
        # If next_action was set in collect_slots_node, follow it
        if state.next_action == "identify_products":
            logger.info(f"✅ [ROUTE] Slots completed → identify_products")
            return "identify_products"
        
        # If products already identified (direct comparison), skip to comparison
        if state.products_identified:
            logger.info(f"✅ [ROUTE] Products identified → identify_products")
            return "identify_products"
        
        # Otherwise, wait for more input (END will be called again when user responds)
        logger.info(f"🔄 [ROUTE] Still collecting slots → end (wait for user)")
        return "end"
    
    def build_graph(self):
        graph = StateGraph(ConversationState)
        
        graph.add_node("collect_slots", self.collect_slots_node)
        graph.add_node("identify_products", self.identify_products_node)
        graph.add_node("clarify_products", self.clarify_products_node)
        graph.add_node("generate_comparison", self.generate_comparison_node)
        
        graph.add_edge(START, "collect_slots")
        
        graph.add_conditional_edges("collect_slots", self.route_slot_collection, {
            "identify_products": "identify_products",
            "end": END
        })
        
        graph.add_conditional_edges("identify_products", self.route_comparison, {
            "clarify": "clarify_products",
            "compare": "generate_comparison"
        })
        
        graph.add_edge("clarify_products", END)
        graph.add_edge("generate_comparison", END)
        
        return graph.compile()
    
    def invoke(self, state: ConversationState):
        graph = self.build_graph()
        return graph.invoke(state)
