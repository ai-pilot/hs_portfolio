import io
import csv
import logging
from pathlib import Path

import docx
import pandas as pd

from app.services.llm import process_pdf_with_gemini

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".csv", ".xlsx", ".xls"}


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks by sentences."""
    sentences = []
    for para in text.split("\n"):
        para = para.strip()
        if not para:
            continue
        # Split on sentence endings
        import re
        parts = re.split(r"(?<=[.!?])\s+", para)
        sentences.extend(parts)

    chunks = []
    current_chunk = []
    current_len = 0

    for sentence in sentences:
        sentence_len = len(sentence.split())
        if current_len + sentence_len > chunk_size and current_chunk:
            chunks.append(" ".join(current_chunk))
            # Keep overlap
            overlap_words = []
            overlap_count = 0
            for s in reversed(current_chunk):
                words = s.split()
                if overlap_count + len(words) > overlap:
                    break
                overlap_words.insert(0, s)
                overlap_count += len(words)
            current_chunk = overlap_words
            current_len = overlap_count

        current_chunk.append(sentence)
        current_len += sentence_len

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks if chunks else [text]


async def extract_text(file_bytes: bytes, filename: str) -> str:
    """Extract text from various file formats."""
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        return await process_pdf_with_gemini(file_bytes, filename)

    elif ext in (".docx", ".doc"):
        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)

    elif ext == ".txt":
        return file_bytes.decode("utf-8", errors="ignore")

    elif ext in (".csv", ".xlsx", ".xls"):
        if ext == ".csv":
            df = pd.read_csv(io.BytesIO(file_bytes))
        else:
            df = pd.read_excel(io.BytesIO(file_bytes))
        # Return a text representation
        text_parts = [
            f"Dataset with {len(df)} rows and {len(df.columns)} columns.",
            f"Columns: {', '.join(df.columns.tolist())}",
            "",
            "First 10 rows:",
            df.head(10).to_string(),
        ]
        return "\n".join(text_parts)

    else:
        raise ValueError(f"Unsupported file type: {ext}")


def is_tabular(filename: str) -> bool:
    """Check if a file is a tabular data file."""
    ext = Path(filename).suffix.lower()
    return ext in (".csv", ".xlsx", ".xls")
