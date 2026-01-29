import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

try:
    from app.services.rag_retriever import RAGRetriever
    rag_available = True
except Exception as e:
    logger.warning(f"RAG not available: {e}")
    rag_available = False


class ProductMatcher:
    def __init__(self, llm):
        self.llm = llm

    def filter_credit_cards(
        self,
        products: List[Dict],
        context: Any
    ) -> List[Dict]:
        from app.services.inquiry_classifier import ExtractedContext
        
        if isinstance(context, dict):
            context = ExtractedContext(**context)
        
        filtered = products
        logger.info(f"🔍 Filter start: {len(filtered)} products, context: banking_type={context.banking_type}, employment={context.employment}, product_category={context.product_category}, keywords={context.keywords}")
        
        
        if context.product_category:
            logger.info(f"✅ Product category already classified as '{context.product_category}', returning all matching products")
            return filtered
        
        if context.banking_type:
            before = len(filtered)
            filtered = [
                p for p in filtered
                if p.get('filtering_metadata', {}).get('banking_type') == context.banking_type
            ]
            logger.info(f"  After banking_type filter: {before} → {len(filtered)} products")
        
        if context.employment:
            before = len(filtered)
            filtered_by_employment = [
                p for p in filtered
                if context.employment in p.get('filtering_metadata', {}).get('suitable_for', [])
            ]
            if filtered_by_employment:
                filtered = filtered_by_employment
                logger.info(f"  After employment filter: {before} → {len(filtered)} products")
            else:
                logger.info(f"  After employment filter: {before} → 0 products (skipping, showing all)")
        
        if context.product_tier:
            before = len(filtered)
            tier_lower = context.product_tier.lower()
            filtered = [
                p for p in filtered
                if p.get('tier', '').lower() == tier_lower
            ]
            logger.info(f"  After tier filter: {before} → {len(filtered)} products")
        
        if context.age:
            before = len(filtered)
            filtered = [
                p for p in filtered
                if self._matches_age_range(p, context.age)
            ]
            logger.info(f"  After age filter: {before} → {len(filtered)} products")
        
        if context.income:
            before = len(filtered)
            filtered = [
                p for p in filtered
                if self._matches_income_range(p, context.income)
            ]
            logger.info(f"  After income filter: {before} → {len(filtered)} products")
        
        if context.keywords:
            before = len(filtered)
            filtered = [
                p for p in filtered
                if self._matches_keywords(p, context.keywords)
            ]
            logger.info(f"  After keywords filter: {before} → {len(filtered)} products")
        
        if context.use_cases:
            before = len(filtered)
            filtered = [
                p for p in filtered
                if self._matches_use_cases(p, context.use_cases)
            ]
            logger.info(f"  After use_cases filter: {before} → {len(filtered)} products")
        
        logger.info(f"🏁 Filter end: {len(filtered)} final products")
        return filtered

    def _matches_age_range(self, product: Dict, age: int) -> bool:
        age_range = product.get('filtering_metadata', {}).get('age_range', {})
        min_age = age_range.get('min', 0)
        max_age = age_range.get('max')
        
        if max_age is None:
            return age >= min_age
        return min_age <= age <= max_age

    def _matches_income_range(self, product: Dict, income: int) -> bool:
        income_range = product.get('filtering_metadata', {}).get('income_range', {})
        min_income = income_range.get('min')
        max_income = income_range.get('max')
        
        if min_income is None:
            return True
        if max_income is None:
            return income >= min_income
        return min_income <= income <= max_income

    def _matches_keywords(self, product: Dict, keywords: List[str]) -> bool:
        if not keywords:
            return True
        
        
        product_name = product.get('name', '').lower()
        product_keywords = [k.lower() for k in product.get('filtering_metadata', {}).get('quick_match_keywords', [])]
        product_use_cases = [u.lower() for u in product.get('filtering_metadata', {}).get('use_cases', [])]
        product_features = [f.lower() for f in product.get('key_benefits', [])]
        
        all_product_text = f"{product_name} {' '.join(product_keywords)} {' '.join(product_use_cases)} {' '.join(product_features)}".lower()
        
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in all_product_text or any(keyword_lower in text for text in [product_name] + product_keywords + product_use_cases + product_features):
                logger.info(f"  Keyword match '{product.get('name')}': True (keyword: '{keyword}')")
                return True
        
        logger.info(f"  Keyword match '{product.get('name')}': False (keywords: {keywords})")
        return False

    def _matches_use_cases(self, product: Dict, use_cases: List[str]) -> bool:
        product_use_cases = product.get('filtering_metadata', {}).get('use_cases', [])
        
        return any(uc in product_use_cases for uc in use_cases)

    def format_products_response(self, products: List[Dict], user_query: str = "") -> str:
        if not products:
            return "I couldn't find any products matching your criteria. Would you like me to help you explore other options or check your eligibility?"
        
        response = f"We have {len(products)} credit card(s) matching your criteria:\n\n"
        
        rag_retriever = None
        rag_context = {}
        if rag_available and user_query:
            try:
                rag_retriever = RAGRetriever.get_instance()
                rag_results = rag_retriever.retrieve(user_query, top_k=2)
                if rag_results:
                    rag_context = {r['metadata'].get('file', ''): r['chunk'] for r in rag_results}
                    logger.info(f"🎯 RAG: Retrieved {len(rag_context)} context chunks")
            except Exception as e:
                logger.warning(f"RAG enrichment failed: {e}")
        
        for idx, product in enumerate(products, 1):
            name = product.get('name', 'Unknown Card')
            tier = product.get('tier', '').title()
            network = product.get('card_network', product.get('network', 'Visa'))
            
            key_benefits = product.get('key_benefits', [])
            benefits_text = "; ".join(key_benefits[:3]) if key_benefits else "Standard benefits"
            
            response += f"{idx}. **{name}** ({network} {tier})\n"
            response += f"   {benefits_text}\n\n"
        
        response += "Would you like to know more about any of these cards or check your eligibility?"
        
        return response
