import logging
from google import genai
from app.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768


def _get_client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts using Gemini."""
    client = _get_client()
    embeddings = []

    # Process in batches of 100 (API limit)
    for i in range(0, len(texts), 100):
        batch = texts[i : i + 100]
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=batch,
            config={"output_dimensionality": EMBEDDING_DIM},
        )
        for emb in result.embeddings:
            embeddings.append(emb.values)

    return embeddings


def embed_query(text: str) -> list[float]:
    """Generate embedding for a single query."""
    return embed_texts([text])[0]
