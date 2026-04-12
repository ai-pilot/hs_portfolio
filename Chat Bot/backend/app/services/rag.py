import logging
import os
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.services.embeddings import embed_texts, embed_query
from app.services.documents import chunk_text, extract_text

logger = logging.getLogger(__name__)

CV_COLLECTION = "cv_knowledge"
UPLOADS_COLLECTION = "user_uploads"

_client: chromadb.ClientAPI | None = None


def get_chroma_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        os.makedirs(settings.chroma_persist_dir, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def _get_or_create_collection(name: str) -> chromadb.Collection:
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


async def index_cv_on_startup():
    """Index the CV PDF into ChromaDB on app startup."""
    collection = _get_or_create_collection(CV_COLLECTION)

    # Skip if already indexed
    if collection.count() > 0:
        logger.info(f"CV already indexed with {collection.count()} chunks. Skipping.")
        return

    cv_path = Path(settings.data_dir) / "cv.pdf"
    if not cv_path.exists():
        logger.warning(f"CV not found at {cv_path}. Skipping CV indexing.")
        return

    logger.info("Indexing CV with Gemini multimodal extraction...")
    with open(cv_path, "rb") as f:
        pdf_bytes = f.read()

    text = await extract_text(pdf_bytes, "cv.pdf")
    chunks = chunk_text(text, chunk_size=300, overlap=50)

    logger.info(f"Generated {len(chunks)} chunks from CV")
    embeddings = embed_texts(chunks)

    collection.add(
        ids=[f"cv_chunk_{i}" for i in range(len(chunks))],
        embeddings=embeddings,
        documents=chunks,
        metadatas=[{"source": "cv", "chunk_index": i} for i in range(len(chunks))],
    )
    logger.info("CV indexed successfully!")


async def index_uploaded_document(
    file_bytes: bytes, filename: str, session_id: str
) -> tuple[int, str]:
    """Index an uploaded document into ChromaDB. Returns (num_chunks, full_text)."""
    text = await extract_text(file_bytes, filename)
    chunks = chunk_text(text, chunk_size=400, overlap=80)

    embeddings = embed_texts(chunks)
    collection = _get_or_create_collection(UPLOADS_COLLECTION)

    ids = [f"{session_id}_{filename}_{i}" for i in range(len(chunks))]
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=[
            {"source": filename, "session_id": session_id, "chunk_index": i}
            for i in range(len(chunks))
        ],
    )

    return len(chunks), text


# Keywords that signal the user is asking about their uploaded doc, not the CV
_UPLOAD_INTENT_KEYWORDS = [
    "this document", "this file", "uploaded", "the doc", "the file",
    "the jd", "job description", "the pdf", "the report", "the csv",
    "the excel", "summarize it", "summarise it", "what does it say",
    "what's in it", "analyze it", "analyse it", "the data",
]


def _is_upload_query(query: str) -> bool:
    """Detect if user is asking about an uploaded document."""
    q = query.lower()
    return any(kw in q for kw in _UPLOAD_INTENT_KEYWORDS)


def search_knowledge(
    query: str,
    session_id: str | None = None,
    top_k: int = 5,
    source_filter: str | None = None,
) -> list[dict]:
    """Search CV and uploaded documents for relevant chunks.

    Args:
        source_filter: "cv" to search only CV, "uploads" for only uploads,
                       None for auto-detect based on query intent.
    """
    query_embedding = embed_query(query)
    results = []

    # Auto-detect intent if no explicit filter
    if source_filter is None:
        if _is_upload_query(query) and session_id:
            source_filter = "uploads"

    # Search CV (skip if explicitly filtering to uploads only)
    if source_filter != "uploads":
        cv_collection = _get_or_create_collection(CV_COLLECTION)
        if cv_collection.count() > 0:
            cv_results = cv_collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, cv_collection.count()),
            )
            for i, doc in enumerate(cv_results["documents"][0]):
                results.append(
                    {
                        "text": doc,
                        "source": "CV",
                        "score": 1 - cv_results["distances"][0][i],
                    }
                )

    # Search uploads (skip if explicitly filtering to CV only)
    if source_filter != "cv":
        uploads_collection = _get_or_create_collection(UPLOADS_COLLECTION)
        if uploads_collection.count() > 0 and session_id:
            upload_results = uploads_collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, uploads_collection.count()),
                where={"session_id": session_id},
            )
            if upload_results["documents"][0]:
                for i, doc in enumerate(upload_results["documents"][0]):
                    score = 1 - upload_results["distances"][0][i]
                    # Boost uploaded doc scores when user intent is about uploads
                    if source_filter == "uploads":
                        score = min(score + 0.15, 1.0)
                    results.append(
                        {
                            "text": doc,
                            "source": upload_results["metadatas"][0][i].get(
                                "source", "uploaded document"
                            ),
                            "score": score,
                        }
                    )

    # Sort by relevance and return top results
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


def format_rag_context(results: list[dict]) -> str:
    """Format RAG results into a context string for the LLM."""
    if not results:
        return ""

    parts = ["Here is relevant information from available sources:\n"]
    for i, r in enumerate(results, 1):
        parts.append(f"[{i}] (Source: {r['source']}, Relevance: {r['score']:.2f})")
        parts.append(r["text"])
        parts.append("")

    return "\n".join(parts)
