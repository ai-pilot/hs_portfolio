import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import chat, upload
from app.services.rag import index_cv_on_startup
from app.middleware import RateLimitMiddleware, OriginCheckMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: index CV into ChromaDB."""
    logger.info("🚂 Orient Express starting up...")
    try:
        await index_cv_on_startup()
        logger.info("CV indexed and ready!")
    except Exception as e:
        logger.error(f"Failed to index CV: {e}")
    yield
    logger.info("🚂 Orient Express shutting down...")


app = FastAPI(
    title="Orient Express - AI Chatbot",
    description="Himanshu Suri's portfolio AI assistant",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(OriginCheckMiddleware)

# Share session storage between routers
upload.set_sessions_ref(chat._sessions)

app.include_router(chat.router)
app.include_router(upload.router)


@app.get("/")
async def root():
    return {
        "name": "Orient Express",
        "version": "1.0.0",
        "status": "All aboard! 🚂",
    }
