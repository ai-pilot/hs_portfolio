import json
import logging
import time
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.llm import chat_stream
from app.services.rag import search_knowledge, format_rag_context
from app.services.analysis import analyze_dataframe, load_dataframe
from app.services.guardrails import check_input, check_output, redact_pii_in_output
from app.services.followups import generate_followups

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])

# In-memory session storage (per server instance)
_sessions: dict[str, dict] = {}


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    session_id: str | None = None


def _get_session(session_id: str | None) -> tuple[str, dict]:
    if not session_id:
        session_id = str(uuid.uuid4())
    if session_id not in _sessions:
        _sessions[session_id] = {
            "history": [],
            "uploaded_files": {},  # filename -> bytes
            "uploaded_dataframes": {},  # filename -> serialized df info
        }
    return session_id, _sessions[session_id]


@router.post("/chat")
async def chat(request: ChatRequest):
    start_time = time.time()
    session_id, session = _get_session(request.session_id)

    user_message = request.messages[-1].content if request.messages else ""

    # --- Input Guardrails ---
    guard_result = check_input(user_message, session_id)
    if not guard_result.passed:

        async def guard_stream():
            yield f"data: {json.dumps({'type': 'guardrail', 'category': guard_result.category, 'session_id': session_id})}\n\n"
            yield f"data: {json.dumps({'type': 'text', 'content': guard_result.message})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'tokens_used': 0, 'latency_ms': int((time.time() - start_time) * 1000)})}\n\n"

        return StreamingResponse(guard_stream(), media_type="text/event-stream")

    # PII warning (passed but with warning)
    pii_warning = guard_result.message if guard_result.category == "pii_warning" else ""

    # --- Build conversation context ---
    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    # Keep conversation manageable (context windowing)
    if len(messages) > 20:
        messages = messages[:2] + messages[-18:]

    # --- Pre-fetch RAG context upfront (eliminates double LLM call) ---
    rag_context = ""
    try:
        results = search_knowledge(user_message, session_id)
        rag_context = format_rag_context(results)
    except Exception as e:
        logger.warning(f"RAG search failed: {e}")

    async def stream_response():
        yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"

        if pii_warning:
            yield f"data: {json.dumps({'type': 'warning', 'content': pii_warning})}\n\n"

        tool_results = None
        full_response = ""
        buffered_text = ""  # Buffer text in case a tool call discards it

        async for chunk in chat_stream(messages, rag_context, tool_results):
            if chunk["type"] == "thinking":
                yield f"data: {json.dumps(chunk)}\n\n"

            elif chunk["type"] == "tool_call":
                # Discard any text emitted before the tool call — the follow-up
                # stream will produce the real answer with tool context
                if buffered_text:
                    yield f"data: {json.dumps({'type': 'clear', 'reason': 'tool_call'})}\n\n"
                    buffered_text = ""
                    full_response = ""

                yield f"data: {json.dumps({'type': 'tool_start', 'name': chunk['name']})}\n\n"

                # Execute tool inline
                if chunk["name"] == "analyze_data":
                    query = chunk["args"].get("query", "summary")
                    if session["uploaded_dataframes"]:
                        fname = list(session["uploaded_dataframes"].keys())[-1]
                        file_bytes = session["uploaded_files"][fname]
                        df = load_dataframe(file_bytes, fname)
                        tool_result = analyze_dataframe(df, query)
                    else:
                        tool_result = "No data file has been uploaded yet. Please upload a CSV or Excel file first."
                    tool_results = {"name": "analyze_data", "result": tool_result}

                elif chunk["name"] == "explain_code":
                    code = chunk["args"].get("code", "")
                    lang = chunk["args"].get("language", "auto")
                    tool_result = f"Code to explain ({lang}):\n```\n{code}\n```"
                    tool_results = {"name": "explain_code", "result": tool_result}

                elif chunk["name"] == "search_knowledge":
                    query = chunk["args"].get("query", user_message)
                    extra_results = search_knowledge(query, session_id)
                    extra_context = format_rag_context(extra_results)
                    tool_results = {
                        "name": "search_knowledge",
                        "result": extra_context or "No additional information found.",
                    }

                yield f"data: {json.dumps({'type': 'tool_end', 'name': chunk['name']})}\n\n"

            elif chunk["type"] == "text":
                cleaned = redact_pii_in_output(chunk["content"])
                buffered_text += cleaned
                full_response += cleaned
                yield f"data: {json.dumps({'type': 'text', 'content': cleaned})}\n\n"

            elif chunk["type"] == "done":
                if not tool_results:
                    latency = int((time.time() - start_time) * 1000)
                    chunk["latency_ms"] = latency
                    yield f"data: {json.dumps(chunk)}\n\n"

        # If a tool was called, do a follow-up call with the results
        if tool_results:
            async for chunk in chat_stream(messages, rag_context, tool_results):
                if chunk["type"] == "thinking":
                    yield f"data: {json.dumps(chunk)}\n\n"
                elif chunk["type"] == "text":
                    cleaned = redact_pii_in_output(chunk["content"])
                    full_response += cleaned
                    yield f"data: {json.dumps({'type': 'text', 'content': cleaned})}\n\n"
                elif chunk["type"] == "done":
                    latency = int((time.time() - start_time) * 1000)
                    chunk["latency_ms"] = latency
                    yield f"data: {json.dumps(chunk)}\n\n"

        # Send follow-up suggestions
        followups = generate_followups(user_message, full_response)
        yield f"data: {json.dumps({'type': 'followups', 'suggestions': followups})}\n\n"

    return StreamingResponse(stream_response(), media_type="text/event-stream")


@router.get("/health")
async def health():
    return {"status": "ok", "bot": "Orient Express 🚂"}


@router.get("/suggestions")
async def suggestions():
    return {
        "suggestions": [
            "Tell me about Himanshu's experience with AI",
            "What projects has Himanshu built at DAMAC?",
            "What are Himanshu's core skills?",
            "Explain RAG architecture to me",
            "What's Himanshu's education background?",
        ]
    }
