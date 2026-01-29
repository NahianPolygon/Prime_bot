from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from app.api.chat import router as chat_router
from app.core.config import settings
from app.core.redis import init_redis, close_redis, get_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    
    await init_redis()
        
    try:
        from app.services.rag_retriever import RAGRetriever
        logger = logging.getLogger(__name__)
        logger.info("🚀 [STARTUP] Initializing RAG system...")
        rag = RAGRetriever()
        logger.info("✅ [STARTUP] RAG system initialized successfully")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"⚠️  [STARTUP] RAG initialization failed: {e}")
    
    yield
    
    await close_redis()


app = FastAPI(
    title="Prime Bank Chatbot",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api", tags=["chat"])


@app.get("/health")
async def health():
    redis = get_redis()
    if redis is None:
        return {"status": "unhealthy", "error": "Redis not initialized"}
    
    try:
        await redis.ping()
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.get("/")
async def root():
    return {
        "service": "Prime Bank Chatbot",
        "version": "1.0.0",
        "docs": "/docs"
    }
