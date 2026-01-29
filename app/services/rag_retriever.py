import logging
from pathlib import Path
from typing import List, Dict
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
                self.collection_name = "prime_products"
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
        
        logger.info("🔨 RAG: Building index from MD files...")
        points = []
        point_id = 1
        
        for banking_type in ["conventional", "islami"]:
            for category in ["credit", "save"]:
                category_path = self.kb_path / banking_type / category
                
                if category == "credit":
                    subdir = category_path / "i_need_a_credit_card"
                    prod_type = "credit_card"
                else:
                    subdir = None
                    prod_type = None
                
                if subdir and subdir.exists():
                    for md_file in subdir.glob("*.md"):
                        try:
                            content = md_file.read_text(encoding='utf-8')
                            chunks = self._chunk_content(content, 500, 100)
                            
                            for chunk_text in chunks:
                                embedding = self.embedder.encode(chunk_text)
                                
                                point = PointStruct(
                                    id=point_id,
                                    vector=embedding.tolist(),
                                    payload={
                                        'file': md_file.name,
                                        'banking_type': banking_type,
                                        'product_type': prod_type,
                                        'path': str(md_file),
                                        'chunk': chunk_text[:500]
                                    }
                                )
                                points.append(point)
                                point_id += 1
                        except Exception as e:
                            logger.error(f"Error reading {md_file}: {e}")
        
        if points:
            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                logger.info(f"✅ RAG: Indexed {len(points)} document chunks in Qdrant")
            except Exception as e:
                logger.error(f"Error upserting points: {e}")
    
    def _chunk_content(self, text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence.split())
            
            if current_length + sentence_length > chunk_size and current_chunk:
                chunks.append('. '.join(current_chunk) + '.')
                current_chunk = current_chunk[-overlap:] if overlap else []
                current_length = sum(len(s.split()) for s in current_chunk)
            
            current_chunk.append(sentence)
            current_length += sentence_length
        
        if current_chunk:
            chunks.append('. '.join(current_chunk) + '.')
        
        return [c for c in chunks if c.strip()]
    
    def retrieve(self, query: str, top_k: int = 3) -> List[Dict]:
        if not self.embedder or not self.client:
            logger.warning("⚠️  RAG: Not available for retrieval")
            return []
        
        try:
            query_embedding = self.embedder.encode(query).tolist()
            
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k
            )
            
            formatted_results = []
            for hit in results:
                formatted_results.append({
                    'chunk': hit.payload.get('chunk', ''),
                    'metadata': {
                        'file': hit.payload.get('file', ''),
                        'banking_type': hit.payload.get('banking_type', ''),
                        'product_type': hit.payload.get('product_type', ''),
                        'path': hit.payload.get('path', '')
                    },
                    'similarity': hit.score
                })
            
            return formatted_results
        except Exception as e:
            logger.error(f"Error during retrieval: {e}")
            return []
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
