import logging
from pathlib import Path
from typing import List, Dict, Optional
import json
import re
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
from app.core.config import settings

logger = logging.getLogger(__name__)

class RAGRetriever:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.kb_path = Path("/app/app/knowledge/products")
            
            try:
                self.embedder = SentenceTransformer(settings.EMBEDDING_MODEL)
                self.embedding_dim = self.embedder.get_sentence_embedding_dimension()
                logger.info(f"✅ RAG: Loaded embedding model {settings.EMBEDDING_MODEL} (dim={self.embedding_dim})")
            except Exception as e:
                logger.error(f"❌ RAG: Failed to load embedder: {e}")
                self.embedder = None
                self.embedding_dim = 300
            
            try:
                self.client = QdrantClient(
                    host=settings.QDRANT_HOST,
                    port=settings.QDRANT_PORT
                )
                self.collection_name = "prime_knowledge_base"
                logger.info(f"✅ RAG: Connected to Qdrant at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
            except Exception as e:
                logger.error(f"❌ RAG: Failed to connect to Qdrant: {e}")
                self.client = None
            
            self._ensure_collection()
            self._load_documents()
            self._initialized = True
    
    def _ensure_collection(self):
        if not self.client:
            return
        
        try:
            collections = self.client.get_collections()
            existing = [c.name for c in collections.collections]
            
            if self.collection_name not in existing:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✅ RAG: Created Qdrant collection '{self.collection_name}'")
            else:
                logger.info(f"✅ RAG: Using existing collection '{self.collection_name}'")
        except Exception as e:
            logger.error(f"Error ensuring collection: {e}")
    
    def _load_documents(self):
        if not self.client or not self.embedder:
            logger.warning("⚠️  RAG: Cannot load documents - missing client or embedder")
            return
        
        try:
            collection_info = self.client.get_collection(self.collection_name)
            if collection_info.points_count > 0:
                logger.info(f"✅ RAG: Collection already has {collection_info.points_count} documents")
                return
        except Exception as e:
            logger.warning(f"Could not check collection: {e}")
        
        logger.info("🔨 RAG: Building index from all MD files in knowledge base...")
        
        md_files = list(self.kb_path.glob('**/*.md'))
        total_files = len(md_files)
        
        if total_files == 0:
            logger.warning("⚠️  RAG: No MD files found in knowledge base")
            return
        
        points = []
        point_id = 1
        total_chunks = 0
        
        for file_idx, md_file in enumerate(md_files, 1):
            try:
                progress_pct = int((file_idx / total_files) * 100)
                bar_length = 40
                filled = int((progress_pct / 100) * bar_length)
                bar = '█' * filled + '░' * (bar_length - filled)
                logger.info(f"📊 RAG: [{bar}] {progress_pct}% ({file_idx}/{total_files}) - {md_file.name}")
                
                content = md_file.read_text(encoding='utf-8')
                metadata = self._extract_metadata(content)
                cleaned_content = self._clean_md_content(content)
                chunks = self._chunk_content(cleaned_content, chunk_size=600, overlap=150)
                
                # Auto-extract return_rate and scheme_type from content
                return_rate = self._extract_return_rate(content)
                scheme_type = self._extract_scheme_type(content)
                
                for chunk_idx, chunk_text in enumerate(chunks):
                    if not chunk_text.strip():
                        continue
                    
                    embedding = self.embedder.encode(chunk_text)
                    
                    point = PointStruct(
                        id=point_id,
                        vector=embedding.tolist(),
                        payload={
                            'file': md_file.name,
                            'banking_type': metadata.get('banking_type', md_file.parent.parent.parent.name),
                            'category': metadata.get('category', md_file.parent.parent.name),
                            'product_name': metadata.get('product_name', md_file.stem),
                            'product_id': metadata.get('product_id', ''),
                            'card_network': metadata.get('card_network', ''),
                            'tier': metadata.get('tier', ''),
                            'path': str(md_file),
                            'chunk_idx': chunk_idx,
                            'chunk_text': chunk_text[:800],
                            'return_rate': return_rate,
                            'scheme_type': scheme_type
                        }
                    )
                    points.append(point)
                    point_id += 1
                    total_chunks += 1
            except Exception as e:
                logger.error(f"Error processing {md_file}: {e}")
        
        if points:
            try:
                logger.info(f"📊 RAG: [{'█' * 40}] 100% - Uploading {total_chunks} chunks to Qdrant...")
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                logger.info(f"✅ RAG: Indexed {total_chunks} document chunks from {total_files} MD files successfully!")
            except Exception as e:
                logger.error(f"Error upserting points: {e}")
    
    def _extract_metadata(self, md_content: str) -> Dict:
        metadata = {}
        
        lines = md_content.split('\n')
        if lines[0].strip() == '---':
            end_idx = 1
            while end_idx < len(lines) and lines[end_idx].strip() != '---':
                end_idx += 1
            
            for line in lines[1:end_idx]:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip("'\"[]")
                    
                    if value.lower() in ['true', 'false']:
                        metadata[key] = value.lower() == 'true'
                    elif value.isdigit():
                        metadata[key] = int(value)
                    else:
                        metadata[key] = value
        
        return metadata
    
    def _clean_md_content(self, content: str) -> str:
        lines = content.split('\n')
        
        if lines and lines[0].strip() == '---':
            end_idx = 1
            while end_idx < len(lines) and lines[end_idx].strip() != '---':
                end_idx += 1
            lines = lines[end_idx+1:]
        
        cleaned = []
        for line in lines:
            line = line.rstrip()
            line = re.sub(r'^#+\s+', '', line)
            line = re.sub(r'\*{1,2}', '', line)
            line = re.sub(r'_+', '', line)
            cleaned.append(line)
        
        return '\n'.join(cleaned)
    
    def _chunk_content(self, text: str, chunk_size: int = 600, overlap: int = 150) -> List[str]:
        sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 10]
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence.split())
            
            if current_length + sentence_length > chunk_size and current_chunk:
                chunk_text = '. '.join(current_chunk) + '.'
                if len(chunk_text.split()) > 20:
                    chunks.append(chunk_text)
                
                overlap_count = max(1, int(len(current_chunk) * (overlap / chunk_size)))
                current_chunk = current_chunk[-overlap_count:] if overlap_count > 0 else []
                current_length = sum(len(s.split()) for s in current_chunk)
            
            current_chunk.append(sentence)
            current_length += sentence_length
        
        if current_chunk:
            chunk_text = '. '.join(current_chunk) + '.'
            if len(chunk_text.split()) > 20:
                chunks.append(chunk_text)
        
        return [c.strip() for c in chunks if c.strip()]
    
    def _extract_return_rate(self, content: str) -> Optional[str]:
        """Extract interest/profit rate from MD content (e.g., '6%', '9%')"""
        patterns = [
            r'(\d+)%\s+(?:interest|profit|rate)',
            r'(?:interest|profit|rate)[:\s]+(\d+)%',
            r'\*\*(\d+)%',
        ]
        content_lower = content.lower()
        
        for pattern in patterns:
            match = re.search(pattern, content_lower)
            if match:
                return f"{match.group(1)}%"
        
        return None
    
    def _extract_scheme_type(self, content: str) -> Optional[str]:
        """Extract scheme type: lump_sum, monthly_fixed, or monthly_custom"""
        content_lower = content.lower()
        
        # Check for custom goal-based schemes
        if any(keyword in content_lower for keyword in ['custom', 'goal amount', 'you set', 'your target', 'laksma puron']):
            if any(keyword in content_lower for keyword in ['monthly', 'installment', 'deposit']):
                return 'monthly_custom'
        
        # Check for lump sum (fixed deposit type)
        if any(keyword in content_lower for keyword in ['lump sum', 'fixed deposit', 'single deposit', 'upfront']):
            return 'lump_sum'
        
        # Check for monthly fixed
        if any(keyword in content_lower for keyword in ['fixed monthly', 'monthly installment', 'fixed amount', 'monthly payment']):
            if 'custom' not in content_lower and 'goal amount' not in content_lower:
                return 'monthly_fixed'
        
        return None
    
    def retrieve(self, query: str, top_k: int = 5, filters: Dict = None) -> List[Dict]:
        if not self.embedder or not self.client:
            logger.warning("⚠️  RAG: Not available for retrieval")
            return []
        
        try:
            query_embedding = self.embedder.encode(query).tolist()
            
            search_kwargs = {
                "collection_name": self.collection_name,
                "query_vector": query_embedding,
                "limit": top_k
            }
            
            if filters:
                search_kwargs["query_filter"] = filters
            
            results = self.client.search(**search_kwargs)
            
            formatted_results = []
            for hit in results:
                formatted_results.append({
                    'chunk': hit.payload.get('chunk_text', ''),
                    'similarity': hit.score,
                    'metadata': {
                        'file': hit.payload.get('file', ''),
                        'banking_type': hit.payload.get('banking_type', ''),
                        'category': hit.payload.get('category', ''),
                        'product_name': hit.payload.get('product_name', ''),
                        'product_id': hit.payload.get('product_id', ''),
                        'card_network': hit.payload.get('card_network', ''),
                        'tier': hit.payload.get('tier', ''),
                        'path': hit.payload.get('path', ''),
                        'chunk_idx': hit.payload.get('chunk_idx', 0)
                    }
                })
            
            return formatted_results
        except Exception as e:
            logger.error(f"Error during retrieval: {e}")
            return []
    
    def retrieve_by_product(self, product_name: str, top_k: int = 10) -> List[Dict]:
        if not self.client:
            return []
        
        try:
            results = self.client.scroll(
                collection_name=self.collection_name,
                limit=top_k,
                query_filter={
                    "must": [
                        {"key": "product_name", "match": {"value": product_name}}
                    ]
                }
            )
            return results[0] if results else []
        except Exception as e:
            logger.error(f"Error retrieving by product: {e}")
            return []
    
    def retrieve_by_banking_type(self, banking_type: str, top_k: int = 10) -> List[Dict]:
        if not self.embedder or not self.client:
            return []
        
        query_embedding = self.embedder.encode(banking_type).tolist()
        
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k,
                query_filter={
                    "must": [
                        {"key": "banking_type", "match": {"value": banking_type}}
                    ]
                }
            )
            
            formatted = []
            for hit in results:
                formatted.append({
                    'chunk': hit.payload.get('chunk_text', ''),
                    'metadata': {
                        'product_name': hit.payload.get('product_name', ''),
                        'banking_type': hit.payload.get('banking_type', '')
                    }
                })
            return formatted
        except Exception as e:
            logger.error(f"Error retrieving by banking type: {e}")
            return []
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
