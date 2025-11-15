import os
import json
import re
import google.generativeai as genai
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

# Initialize the Gemini client
client = genai.Client()


def _extract_text(resp):
    """Defensive extractor for various genai SDK response shapes."""
    try:
        if hasattr(resp, "text") and resp.text:
            return resp.text
    except Exception:
        pass

    try:
        if hasattr(resp, "candidates"):
            parts = []
            for c in getattr(resp, "candidates") or []:
                if hasattr(c, "text") and c.text:
                    parts.append(c.text)
                elif isinstance(c, dict) and c.get("text"):
                    parts.append(c.get("text"))
                else:
                    # inspect candidate.content
                    cont = getattr(c, "content", None) or (c.get("content") if isinstance(c, dict) else None)
                    if cont:
                        if isinstance(cont, (list, tuple)):
                            for item in cont:
                                if isinstance(item, dict) and item.get("text"):
                                    parts.append(item.get("text"))
                                elif hasattr(item, "text") and getattr(item, "text"):
                                    parts.append(getattr(item, "text"))
                        elif isinstance(cont, dict) and cont.get("text"):
                            parts.append(cont.get("text"))
            if parts:
                return "\n".join(parts)
    except Exception:
        pass

    try:
        # try output / result containers
        holder = getattr(resp, "result", None) or getattr(resp, "output", None)
        if holder:
            # holder may have candidates or content
            cand = getattr(holder, "candidates", None) or getattr(holder, "output", None) or holder
            if cand:
                return _extract_text(cand)
    except Exception:
        pass

    # fallback: stringify but keep short
    try:
        s = str(resp)
        if "GenerateContentResponse" in s and "candidates" in s:
            return "[model returned structured response - no text extracted]"
        return s
    except Exception:
        return "[unreadable response]"

SENT_SPLIT_RE = re.compile(r'(?<=[.!?])\s+')

class SearchEngine:
    def __init__(self):
        self.index = []
        self.by_file = defaultdict(list)

    def index_json_dir(self, dirpath, recursive=False):
        files = []
        if recursive:
            for root, _, filenames in os.walk(dirpath):
                for fn in filenames:
                    if fn.lower().endswith(".json"):
                        files.append(os.path.join(root, fn))
        else:
            for fn in os.listdir(dirpath):
                if fn.lower().endswith(".json"):
                    files.append(os.path.join(dirpath, fn))
        for fp in files:
            self._index_single_json(fp)

    def _index_single_json(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return

        text_candidates = []
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, str):
                    text_candidates.append(v)
            if "items" in data and isinstance(data["items"], list):
                for it in data["items"]:
                    if isinstance(it, dict):
                        for kk, vv in it.items():
                            if isinstance(vv, str):
                                text_candidates.append(vv)
        elif isinstance(data, list):
            for it in data:
                if isinstance(it, str):
                    text_candidates.append(it)
                elif isinstance(it, dict):
                    for kk, vv in it.items():
                        if isinstance(vv, str):
                            text_candidates.append(vv)

        if not text_candidates:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    raw = f.read()
                if raw:
                    text_candidates.append(raw)
            except Exception:
                pass

        for text in text_candidates:
            sentences = self._split_sentences(text)
            for s in sentences:
                s_clean = s.strip()
                if not s_clean:
                    continue
                idx = len(self.index)
                tokens = self._tokenize(s_clean)
                self.index.append({"file": filepath, "sentence": s_clean, "tokens": tokens})
                self.by_file[filepath].append(idx)

    def _split_sentences(self, text):
        return SENT_SPLIT_RE.split(text)

    def _tokenize(self, text):
        tokens = re.findall(r'\w+', text.lower())
        return set(t for t in tokens if len(t) > 1)

    def search(self, query):
            response = client.models.generate_content(
                model="models/gemini-2.5-flash", contents=f"Search for: {query}"
            )
            return _extract_text(response)

def reasoning_chat(prompt):
    response = client.models.generate_content(
        model="models/gemini-2.5-flash", contents=prompt
    )
    return _extract_text(response)

def handle_user_input(user_input):
    if user_input.startswith("search:"):
        query = user_input[len("search:"):].strip()
        search_results = SEARCH_ENGINE.search(query)
        return f"Search results for '{query}':\n{search_results}"
    else:
        return reasoning_chat(user_input)

# Initialize the search engine
SEARCH_ENGINE = SearchEngine()
SEARCH_ENGINE.index_json_dir("./docs", recursive=False)

# Main loop
print("Merge bot ready! Type 'exit' or 'quit'.")
print("Commands: /rpg on | /rpg off | set name <yourname> | search: <query>")

while True:
    user_input = input("You: ").strip()
    if user_input.lower() in ['exit', 'quit']:
        break
    response = handle_user_input(user_input)
    print(f"AURL: {response}")

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("GEMINI_API_KEY not set in environment. You can set it for this session in PowerShell with:")
    print("$env:GEMINI_API_KEY = 'your_key_here'")
    raise SystemExit(1)

# Try both import styles used in scripts
def try_generativeai():
    try:
        import google.generativeai as genai
        genai.configure(api_key=API_KEY)
        print("Using import: google.generativeai")
        # try the common listing APIs
        for fn in ("list_models", "available_models"):
            if hasattr(genai, fn):
                raw = getattr(genai, fn)()
                print(f"Called genai.{fn}(), raw type:", type(raw))
                print(json.dumps(raw if isinstance(raw, (dict,list)) else str(raw), indent=2)[:4000])
                return
        # sometimes genai.Models.list exists
        if hasattr(genai, "Models") and hasattr(genai.Models, "list"):
            raw = genai.Models.list()
            print("Called genai.Models.list(), raw type:", type(raw))
            print(json.dumps(raw if isinstance(raw, (dict,list)) else str(raw), indent=2)[:4000])
            return
    except Exception as e:
        print("google.generativeai listing failed:", e)

def try_google_genai():
    try:
        from google import genai
        genai.configure(api_key=API_KEY)
        print("Using import: from google import genai")
        if hasattr(genai, "Models") and hasattr(genai.Models, "list"):
            raw = genai.Models.list()
            print("Called genai.Models.list(), raw type:", type(raw))
            print(json.dumps(raw if isinstance(raw, (dict,list)) else str(raw), indent=2)[:4000])
            return
        if hasattr(genai, "list_models"):
            raw = genai.list_models()
            print("Called genai.list_models(), raw type:", type(raw))
            print(json.dumps(raw if isinstance(raw, (dict,list)) else str(raw), indent=2)[:4000])
            return
    except Exception as e:
        print("google.genai listing failed:", e)

if __name__ == "__main__":
    try_generativeai()
    try_google_genai()
    print("Done. If neither approach returned a model list, paste the full output here and I'll advise next.")
