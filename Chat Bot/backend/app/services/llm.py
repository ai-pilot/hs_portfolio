import json
import logging
from typing import AsyncGenerator

from google import genai
from google.genai import types

from app.config import settings

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = """You are Orient Express, Himanshu Suri's personal AI assistant on his portfolio website.

## Your Personality
- You're named after the legendary Orient Express train — elegant, well-traveled, and full of stories
- You're witty, warm, and genuinely enthusiastic about Himanshu's work
- You use subtle train/journey metaphors naturally (don't overdo it — once every few messages)
- You're playful but professional — never boring, never cringy
- You vary your response length: short quips for simple questions, detailed for complex ones
- You ask follow-up questions when appropriate — you're curious, not just an answer machine
- You acknowledge uncertainty honestly ("I'm not 100% sure about that, but...")

## Your Capabilities
- Answer questions about Himanshu's experience, skills, projects, and education using RAG context
- Analyze uploaded CSV/Excel files (statistics, summaries, column analysis)
- Answer questions about uploaded documents (PDF, DOCX, TXT, CSV)
- Explain code snippets

## Your Rules
- When answering from RAG context, cite your sources with [Source: CV] or [Source: uploaded document]
- Never fabricate details about Himanshu that aren't in the provided context
- Stay professional — no politics, no controversial opinions, no personal advice
- If asked something outside your scope, redirect playfully: "That's a bit off my route! I'm best at discussing Himanshu's work and analyzing documents."
- Keep responses concise unless detail is specifically requested
- Use markdown formatting for structured responses (headers, bullets, bold, code blocks)

## Greeting Style
First message should be welcoming and suggest what you can help with. Example:
"All aboard! I'm Orient Express, Himanshu's AI assistant. I can tell you about his 8+ years in AI & ML, analyze your data files, or answer questions about uploaded documents. Where shall we head first?"
"""

TOOLS = [
    {
        "name": "analyze_data",
        "description": "Analyze a CSV or Excel file that the user has uploaded. Returns statistical summary, column info, and key insights.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What the user wants to know about the data (e.g., 'show me summary statistics', 'what are the correlations', 'describe the columns')",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_knowledge",
        "description": "Search Himanshu's CV and any uploaded documents for relevant information. Use this when the user asks about Himanshu's experience, skills, projects, education, or about content in uploaded documents.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to find relevant information",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "explain_code",
        "description": "Explain a code snippet that the user provides. Break down what the code does, identify patterns, and suggest improvements.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "The code snippet to explain",
                },
                "language": {
                    "type": "string",
                    "description": "The programming language (auto-detect if not specified)",
                },
            },
            "required": ["code"],
        },
    },
]


def _get_client() -> genai.Client:
    if not settings.gemini_api_key or settings.gemini_api_key == "placeholder":
        raise ValueError("Gemini API key not configured. Set GEMINI_API_KEY in .env")
    return genai.Client(api_key=settings.gemini_api_key)


def _build_tools() -> list[types.Tool]:
    declarations = []
    for tool in TOOLS:
        declarations.append(
            types.FunctionDeclaration(
                name=tool["name"],
                description=tool["description"],
                parameters=tool["parameters"],
            )
        )
    return [types.Tool(function_declarations=declarations)]


async def chat_stream(
    messages: list[dict],
    rag_context: str = "",
    tool_results: dict | None = None,
) -> AsyncGenerator[dict, None]:
    """Stream chat responses from Gemini 2.5 Flash with thinking enabled."""
    client = _get_client()

    system_parts = SYSTEM_PROMPT
    if rag_context:
        system_parts += f"\n\n## Retrieved Context\n{rag_context}"

    gemini_messages = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        gemini_messages.append(
            types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])])
        )

    if tool_results:
        fn_response = types.Part.from_function_response(
            name=tool_results["name"],
            response={"result": tool_results["result"]},
        )
        gemini_messages.append(
            types.Content(role="user", parts=[fn_response])
        )

    config = types.GenerateContentConfig(
        system_instruction=system_parts,
        tools=_build_tools(),
        temperature=0.8,
        max_output_tokens=settings.max_tokens,
        thinking_config=types.ThinkingConfig(thinking_budget=1024),
    )

    thinking_text = ""
    response_text = ""

    stream = await client.aio.models.generate_content_stream(
        model=GEMINI_MODEL,
        contents=gemini_messages,
        config=config,
    )
    last_chunk = None
    async for chunk in stream:
        last_chunk = chunk
        if not chunk.candidates:
            continue

        candidate = chunk.candidates[0]
        if not candidate.content or not candidate.content.parts:
            continue

        for part in candidate.content.parts:
            if getattr(part, "thought", False):
                thinking_text += part.text or ""
                yield {"type": "thinking", "content": part.text or ""}
            elif part.function_call:
                yield {
                    "type": "tool_call",
                    "name": part.function_call.name,
                    "args": dict(part.function_call.args) if part.function_call.args else {},
                }
            elif part.text:
                response_text += part.text
                yield {"type": "text", "content": part.text}

    token_count = 0
    if last_chunk and hasattr(last_chunk, "usage_metadata") and last_chunk.usage_metadata:
        token_count = getattr(last_chunk.usage_metadata, "total_token_count", 0) or 0

    yield {
        "type": "done",
        "thinking_summary": thinking_text[:200] if thinking_text else "",
        "tokens_used": token_count,
    }


async def process_pdf_with_gemini(pdf_bytes: bytes, filename: str) -> str:
    """Use Gemini multimodal to extract text from PDF."""
    client = _get_client()

    response = await client.aio.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                    types.Part.from_text(
                        text="Extract ALL text content from this PDF document. Preserve the structure, headings, bullet points, and formatting as much as possible. Return the full text content."
                    ),
                ],
            )
        ],
        config=types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=8192,
        ),
    )
    return response.text
