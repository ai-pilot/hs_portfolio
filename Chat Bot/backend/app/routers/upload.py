import logging

from fastapi import APIRouter, File, Form, UploadFile, HTTPException

from app.services.documents import SUPPORTED_EXTENSIONS, is_tabular
from app.services.rag import index_uploaded_document

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["upload"])

# Shared session storage reference (imported in main.py setup)
_sessions: dict[str, dict] = {}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def set_sessions_ref(sessions: dict):
    global _sessions
    _sessions = sessions


def _generate_summary(text: str, filename: str) -> str:
    """Generate a quick text-based summary of the document."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    total_words = len(text.split())

    summary_parts = [f"**Document: {filename}**"]
    summary_parts.append(f"- {total_words} words, {len(lines)} lines")

    # Show first meaningful lines as preview
    preview_lines = lines[:8]
    if preview_lines:
        summary_parts.append("\n**Key content preview:**")
        for line in preview_lines:
            # Truncate long lines
            display = line[:150] + "..." if len(line) > 150 else line
            summary_parts.append(f"> {display}")

    if len(lines) > 8:
        summary_parts.append(f"\n*...and {len(lines) - 8} more lines*")

    summary_parts.append(
        "\nYou can now ask me questions about this document!"
    )
    return "\n".join(summary_parts)


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(...),
):
    """Upload a document for RAG or data analysis."""
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            400,
            f"Unsupported file type: {ext}. Supported: {', '.join(SUPPORTED_EXTENSIONS)}",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large. Maximum size is 10MB.")

    if len(file_bytes) == 0:
        raise HTTPException(400, "Empty file uploaded.")

    # Store in session
    if session_id not in _sessions:
        _sessions[session_id] = {
            "history": [],
            "uploaded_files": {},
            "uploaded_dataframes": {},
        }

    session = _sessions[session_id]
    session["uploaded_files"][file.filename] = file_bytes

    # Track tabular files
    if is_tabular(file.filename):
        session["uploaded_dataframes"][file.filename] = True

    # Index for RAG — now returns (num_chunks, full_text)
    num_chunks, full_text = await index_uploaded_document(
        file_bytes, file.filename, session_id
    )

    # Auto-generate summary
    summary = _generate_summary(full_text, file.filename)

    # Contextual follow-ups based on file type
    if is_tabular(file.filename):
        followups = [
            "Show me summary statistics",
            "What are the key trends?",
            "Any outliers in the data?",
        ]
    else:
        followups = [
            "Summarize this document",
            "What are the key points?",
            "Any action items in this?",
        ]

    return {
        "status": "success",
        "filename": file.filename,
        "chunks_indexed": num_chunks,
        "is_tabular": is_tabular(file.filename),
        "summary": summary,
        "followups": followups,
        "message": f"'{file.filename}' uploaded and indexed ({num_chunks} chunks).",
    }
