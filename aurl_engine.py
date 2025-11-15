# aurl_engine.py
# Exportable AURL RPG Engine — Plug into FlowIDE!
import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

# --- Config ---
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("Set GEMINI_API_KEY in .env")

genai.configure(api_key=API_KEY)
MODEL = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash")
CONTEXT_FILE = "aurl_context.json"

# --- Context ---
def _load():
    if os.path.exists(CONTEXT_FILE):
        with open(CONTEXT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"messages": [], "rpg": False, "name": "Traveler"}

def _save(ctx):
    with open(CONTEXT_FILE, "w", encoding="utf-8") as f:
        json.dump(ctx, f, indent=2)

ctx = _load()

# --- Core Functions (EXPORT THESE) ---
def input_player() -> str:
    """Get player input (for FlowIDE node)"""
    return input("You: ").strip()

def output_story(text: str):
    """Print AURL's response (for FlowIDE node)"""
    speaker = "AURL the Explorer" if ctx.get("rpg") else "AURL"
    print(f"{speaker}: {text}")

def process_input(user_input: str) -> str:
    """Main AURL logic — returns response"""
    global ctx

    if user_input.startswith("/rpg on"):
        ctx["rpg"] = True
        return "Roleplay mode **enabled**."
    if user_input.startswith("/rpg off"):
        ctx["rpg"] = False
        return "Roleplay mode **disabled**."
    if user_input.startswith("set name "):
        ctx["name"] = user_input[9:].strip()
        return f"Name set to **{ctx['name']}**."
    if user_input.lower() in ["exit", "quit"]:
        _save(ctx)
        return "Goodbye!"

    # Build minimal prompt — context is causing token issues
    name = ctx.get("name")
    prompt = f"You are AURL the Explorer. Reply briefly and creatively to: {user_input}"

    # Call Gemini
    def _extract_text(resp_obj):
        """Extract text from response. Return placeholder for MAX_TOKENS."""
        # FIRST: Check for MAX_TOKENS
        try:
            if hasattr(resp_obj, "candidates"):
                cands = getattr(resp_obj, "candidates") or []
                if cands and len(cands) > 0:
                    c = cands[0]
                    finish = getattr(c, "finish_reason", None)
                    if finish == "MAX_TOKENS":
                        return "[thinking...]"
        except Exception:
            pass

        # SECOND: Try text extraction
        try:
            if hasattr(resp_obj, "text") and resp_obj.text:
                return resp_obj.text
        except Exception:
            pass

        # Check candidates for text
        try:
            if hasattr(resp_obj, "candidates"):
                parts = []
                for c in getattr(resp_obj, "candidates") or []:
                    if hasattr(c, "text") and c.text:
                        parts.append(c.text)
                    elif isinstance(c, dict) and c.get("text"):
                        parts.append(c.get("text"))
                if parts:
                    return "\n".join(parts)
        except Exception:
            pass

        # THIRD: Safe fallback
        return "[thinking...]"

    try:
        model = genai.GenerativeModel(MODEL)
        response = model.generate_content(
            prompt,
            generation_config=types.GenerationConfig(temperature=0.8, max_output_tokens=800)
        )
        resp = _extract_text(response)
    except Exception as e:
        resp = f"[AI error: {e}]"

    # Save
    ctx["messages"].append({"user": user_input, "bot": resp})
    ctx["messages"] = ctx["messages"][-50:]
    _save(ctx)

    return resp

# --- Auto-run if used standalone ---
if __name__ == "__main__":
    print("AURL Engine Ready (export mode)")
    while True:
        user_in = input_player()
        if not user_in: continue
        response = process_input(user_in)
        output_story(response)