import os
import json

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("GEMINI_API_KEY not set in environment. Set it with: $env:GEMINI_API_KEY='your_key'")
    raise SystemExit(1)

try:
    import google.generativeai as genai
    try:
        genai.configure(api_key=API_KEY)
    except Exception:
        pass
    print('Using google.generativeai.list_models()')
    raw = genai.list_models()
    # raw may be a generator or an iterable of dicts/strings
    try:
        for item in raw:
            if isinstance(item, dict):
                name = item.get('name') or item.get('id') or item
            else:
                name = item
            print(name)
    except TypeError:
        # not iterable, just print repr
        print(repr(raw))
except Exception as e:
    print('google.generativeai listing failed:', e)

try:
    from google import genai as ggen
    try:
        ggen.configure(api_key=API_KEY)
    except Exception:
        pass
    print('\nUsing google.genai Models.list()')
    if hasattr(ggen, 'Models') and hasattr(ggen.Models, 'list'):
        raw2 = ggen.Models.list()
        try:
            for item in raw2:
                if isinstance(item, dict):
                    name = item.get('name') or item.get('id') or item
                else:
                    name = item
                print(name)
        except TypeError:
            print(repr(raw2))
    elif hasattr(ggen, 'list_models'):
        raw3 = ggen.list_models()
        try:
            for item in raw3:
                if isinstance(item, dict):
                    name = item.get('name') or item.get('id') or item
                else:
                    name = item
                print(name)
        except TypeError:
            print(repr(raw3))
except Exception as e:
    print('google.genai listing failed:', e)

print('\nDone')
