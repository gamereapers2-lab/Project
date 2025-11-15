from fastapi import FastAPI
from pydantic import BaseModel
import os
from typing import Any, Dict, Callable, Tuple

app = FastAPI(title="AURL Engine Service")

# Lazy loader for the engine so uvicorn can start even when the engine
# raises on import (for example, missing GEMINI_API_KEY). We import the
# actual process_input and memory helpers on first request and cache them.
_engine_loaded = False
_process_input: Callable[[str], str] | None = None
_add_memory: Callable[[dict], None] | None = None


def _load_engine() -> Tuple[Callable[[str], str], Callable[[dict], None]]:
    """Dynamically import the engine and memory helpers. Raises the
    underlying import error so callers can return helpful messages."""
    global _engine_loaded, _process_input, _add_memory
    if _engine_loaded and _process_input is not None:
        return _process_input, _add_memory

    try:
        # Import the engine module and required functions
        import importlib
        engine = importlib.import_module('aurl_engine')
        proc = getattr(engine, 'process_input')
    except Exception as e:
        raise

    # optional memory store
    try:
        mem = importlib.import_module('memory_store')
        add_mem = getattr(mem, 'add_memory')
    except Exception:
        add_mem = lambda *_: None

    _process_input = proc
    _add_memory = add_mem
    _engine_loaded = True
    return _process_input, _add_memory


class ChatRequest(BaseModel):
    session_id: str | None = None
    input: str
    meta: Dict[str, Any] | None = None


class ChatResponse(BaseModel):
    text: str
    actions: list = []


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        proc, _ = _load_engine()
    except Exception as e:
        return {"text": f"[aurl_engine import error: {e}]", "actions": []}

    # Call the engine's process_input and return a structured response
    try:
        resp = proc(req.input)
    except Exception as e:
        resp = f"[engine runtime error: {e}]"

    return {"text": resp, "actions": []}


class LearnRequest(BaseModel):
    session_id: str | None = None
    text: str
    meta: Dict[str, Any] | None = None


class LearnResponse(BaseModel):
    summary: str
    prompts: list


@app.post("/learn", response_model=LearnResponse)
async def learn(req: LearnRequest):
    try:
        proc, add_mem = _load_engine()
    except Exception as e:
        return {"summary": f"[aurl_engine import error: {e}]", "prompts": []}

    text = req.text
    prompt = (
        "You are a helpful assistant for building a knowledge base. "
        "Given the text below, produce: (1) a concise 1-2 sentence summary, and (2) a list of 5 short Q/A pairs or prompts that someone could use to train a chatbot. "
        "Return the summary first, then the prompts separated clearly.\n\nText:\n" + text
    )

    try:
        resp = proc(prompt)
    except Exception as e:
        return {"summary": f"[engine runtime error: {e}]", "prompts": []}

    lines = [l.strip() for l in resp.splitlines() if l.strip()]
    summary = lines[0] if lines else ""
    prompts = []
    for l in lines[1:]:
        if l:
            prompts.append(l)

    entry = {"text": text, "summary": summary, "prompts": prompts, "meta": req.meta or {}}
    try:
        add_mem(entry)
    except Exception:
        pass

    return {"summary": summary, "prompts": prompts}


@app.get("/health")
async def health():
    return {"status": "ok"}
