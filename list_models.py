import os
import json

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("GEMINI_API_KEY not set in environment. You can set it for this session in PowerShell with:")
    print("$env:GEMINI_API_KEY = 'your_key_here'")
    raise SystemExit(1)

def try_generativeai():
    try:
        import google.generativeai as genai
        try:
            genai.configure(api_key=API_KEY)
        except Exception:
            pass
        print("Using import: google.generativeai")
        for fn in ("list_models", "available_models"):
            if hasattr(genai, fn):
                try:
                    raw = getattr(genai, fn)()
                    print(f"Called genai.{fn}(), raw type: {type(raw)}")
                    print(json.dumps(raw if isinstance(raw, (dict,list)) else str(raw), indent=2)[:4000])
                    return
                except Exception as e:
                    print(f"genai.{fn}() call failed: {e}")
        if hasattr(genai, "Models") and hasattr(genai.Models, "list"):
            try:
                raw = genai.Models.list()
                print("Called genai.Models.list(), raw type:", type(raw))
                print(json.dumps(raw if isinstance(raw, (dict,list)) else str(raw), indent=2)[:4000])
                return
            except Exception as e:
                print(f"genai.Models.list() failed: {e}")
    except Exception as e:
        print("google.generativeai listing failed:", e)

def try_google_genai():
    try:
        from google import genai
        try:
            genai.configure(api_key=API_KEY)
        except Exception:
            pass
        print("Using import: from google import genai")
        if hasattr(genai, "Models") and hasattr(genai.Models, "list"):
            try:
                raw = genai.Models.list()
                print("Called genai.Models.list(), raw type:", type(raw))
                print(json.dumps(raw if isinstance(raw, (dict,list)) else str(raw), indent=2)[:4000])
                return
            except Exception as e:
                print(f"genai.Models.list() failed: {e}")
        if hasattr(genai, "list_models"):
            try:
                raw = genai.list_models()
                print("Called genai.list_models(), raw type:", type(raw))
                print(json.dumps(raw if isinstance(raw, (dict,list)) else str(raw), indent=2)[:4000])
                return
            except Exception as e:
                print(f"genai.list_models() failed: {e}")
    except Exception as e:
        print("google.genai listing failed:", e)

if __name__ == "__main__":
    try_generativeai()
    try_google_genai()
    print("Done. If neither approach returned a model list, paste the full output here and I'll advise next.")
