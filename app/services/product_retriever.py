import logging
from typing import Dict, List, Optional
from app.core.config import llm
from app.services.rag_retriever import RAGRetriever

logger = logging.getLogger(__name__)

class ProductRetrieverService:
    def __init__(self):
        self.llm = llm
        self.rag = RAGRetriever()

    def search_products(self, query: str, banking_type: Optional[str] = None, top_k: int = 5) -> List[Dict]:
        # Build RAG filter for banking_type if provided
        rag_filters = None
        if banking_type:
            rag_filters = {
                "must": [
                    {"key": "banking_type", "match": {"value": banking_type}}
                ]
            }
            logger.info(f"🔍 [SEARCH] Applying RAG filter for banking_type={banking_type}")
        
        # Retrieve with banking_type filter
        rag_results = self.rag.retrieve(query, top_k=top_k * 2, filters=rag_filters)
        
        logger.info(f"🔍 [SEARCH] RAG returned {len(rag_results)} results for query: '{query}'")
        if rag_results:
            logger.info(f"🔍 [SEARCH] First result metadata: {rag_results[0].get('metadata', {})}")
        
        if not rag_results:
            return []
        
        products = {}
        for result in rag_results:
            meta = result['metadata']
            product_name = meta.get('product_name', '')
            
            logger.info(f"🔍 [SEARCH] Processing: product_name={product_name}, banking_type={meta.get('banking_type')}, filter={banking_type}")
            
            if not product_name:
                continue
            
            if product_name not in products:
                products[product_name] = {
                    'name': product_name,
                    'banking_type': meta.get('banking_type'),
                    'category': meta.get('category'),
                    'card_network': meta.get('card_network'),
                    'tier': meta.get('tier'),
                    'product_id': meta.get('product_id'),
                    'relevance_score': result['similarity'],
                    'knowledge_chunks': []
                }
            
            products[product_name]['knowledge_chunks'].append(result['chunk'])
        
        ranked = sorted(products.values(), key=lambda p: p['relevance_score'], reverse=True)
        return ranked[:top_k]

    def get_rag_chunks(self, query: str, top_k: int = 5) -> List[str]:
        rag_results = self.rag.retrieve(query, top_k=top_k)
        return [r['chunk'] for r in rag_results]


class ProductMatcherService:
    def __init__(self):
        self.llm = llm
        self.retriever = ProductRetrieverService()

    def rank_by_profile(self, products: List[Dict], age: Optional[int] = None, income: Optional[int] = None, employment: Optional[str] = None) -> List[Dict]:
        if not products or len(products) <= 1:
            return products
        
        product_names = [p.get('name') for p in products]
        chunks = "\n".join(["\n".join(p.get('knowledge_chunks', [])) for p in products if p.get('knowledge_chunks')])
        
        prompt = f"""Based on the knowledge base below, rank these banking products by suitability.

User Profile:
- Age: {age if age else 'Not provided'}
- Income: {income if income else 'Not provided'}
- Employment: {employment if employment else 'Not provided'}

Products: {', '.join(product_names)}

Knowledge Base Context:
{chunks}

Return ranked list from most to least suitable, with brief reason."""
        
        try:
            response = self.llm.invoke(prompt)
            return products
        except:
            return products

    def format_product_response(self, products: List[Dict], user_query: str) -> str:
        if not products:
            return "I couldn't find suitable products matching your criteria. Could you provide more details about your needs?"
        
        chunks_text = "\n".join([
            "\n".join(p.get('knowledge_chunks', [])) 
            for p in products[:3] 
            if p.get('knowledge_chunks')
        ])
        
        prompt = f"""Create a clean product recommendation based on user query.

User Query: {user_query}
Recommended Products: {', '.join([p.get('name') for p in products[:3]])}

Knowledge Context:
{chunks_text}

Format response as:
1. 1-2 sentences acknowledging their needs
2. List products as bullet points with key benefit each:
   • Product Name - Key benefit or feature
3. 1-2 sentences with next step

Keep it concise (under 150 words). NO long explanations."""
        
        try:
            response = self.llm.invoke(prompt)
            return response.content
        except Exception as e:
            logger.error(f"Error formatting response: {e}")
            product_list = "\n".join([f"• {p.get('name')}" for p in products[:3]])
            return f"Based on your query:\n{product_list}\n\nWould you like more details about any of these?"
