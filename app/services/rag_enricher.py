import logging
from typing import Dict, List, Optional
from app.services.rag_retriever import RAGRetriever

logger = logging.getLogger(__name__)

class RAGEnricher:
    def __init__(self, llm):
        self.llm = llm
        self.rag = RAGRetriever.get_instance()
    
    def enrich_product_response(self, product_name: str, query: str) -> Optional[str]:
        if not query or not self.rag.index:
            return None
        
        try:
            combined_query = f"{product_name} {query}"
            results = self.rag.retrieve(combined_query, top_k=1)
            
            if results:
                chunk = results[0].get('chunk', '')
                if chunk:
                    logger.info(f"📚 RAG: Retrieved context for {product_name}")
                    return chunk
        except Exception as e:
            logger.warning(f"RAG enrichment error: {e}")
        
        return None
    
    def answer_product_question(self, product_name: str, query: str) -> Optional[str]:
        context = self.enrich_product_response(product_name, query)
        
        if not context:
            return None
        
        try:
            prompt = f"""Based on the following product information:

Product: {product_name}
Query: {query}

Context:
{context}

Provide a concise answer (2-3 sentences max) to the user's question about {product_name}.
Answer only if the context is relevant, otherwise say you need more information."""

            response = self.llm.invoke(prompt)
            answer = response.content if hasattr(response, 'content') else str(response)
            
            return answer.strip() if answer else None
        except Exception as e:
            logger.error(f"RAG answer generation failed: {e}")
            return None
