from __future__ import annotations

import json, os, time, re
from pathlib import Path
from typing import Dict, List
from tqdm import tqdm
import google.generativeai as genai
from dotenv import load_dotenv

# ─── Config ──────────────────────────────────────────────────────────── #
load_dotenv()
MODEL_NAME          = "gemini-2.5-flash-preview-05-20"
FALLBACK_MODEL      = "gemini-2.0-flash"
CURRENT_MODEL_NAME  = "gemini-2.5-flash-preview-05-20"
GEMINI_KEY          = os.environ["GEMINI_KEY"]
ALT_KEY             = os.environ["GEMINI_ALT_KEY"]
TYPE_PATH           = Path(".\Processing_Files\Danmachi_vol20\Type.json")
GLOSSARY_PATH       = Path(".\Processing_Files\Danmachi_vol20\Glossary.json")
MAX_RETRIES         = 3
RETRY_DELAY         = 6                               # seconds
START_PAGE          = 13
END_PAGE            = 421

COMBOS = [
    {"key": GEMINI_KEY, "model": MODEL_NAME},         # 1  primary key + 2.5
    {"key": ALT_KEY,   "model": MODEL_NAME},          # 2  alt key     + 2.5
    {"key": GEMINI_KEY, "model": FALLBACK_MODEL},     # 3  primary key + 2.0
    {"key": ALT_KEY,   "model": FALLBACK_MODEL},      # 4  alt key     + 2.0
]
COMBOS = [c for c in COMBOS if c["key"]]
combo_idx = 0

# ─── System instruction – glossary from raw text ─────────────────────── #
SYSTEM_PROMPT = """
You are an expert glossary extractor for the light-novel *Danmachi*
(“Danjon ni Deai o Motomeru no wa Machigatteiru Darō ka”, “Is It Wrong to Try to Pick Up Girls in a Dungeon?”).

For every page worth of raw Japanese text you receive:

1. Scan the text and list **only** proper nouns or world-specific common nouns
   (characters, skills, organisations, places, items, races, monsters, etc.).
2. Keep Japanese honorifics when present (さん→“-san”, さま/様→“-sama”,
   ちゃん→“-chan”, 殿→“-dono”, etc.). Treat the suffix as part of the term.
3. Output a **strict JSON object** – and nothing else – with exactly:
   {
     "glossary": { "<JP>": "<EN>", ... }   # may be empty {}
   }
4. When you recognise an official Yen-Press / SB-Creative spelling, use it
   (e.g. “Syr Flover”, “Ryuu Lion”, “Ganesha Familia”).
5. If official spelling is unknown, transliterate to **Title-Case** and never use ALL-CAPS.
6. Ignore ruby readings that appear wrapped in back-ticks (`こう`).
7. Do not use markdown in your response, return only a JSON object. Adding markdown such as ```json will break the automation, and you will be penalized.
"""

# ─── Helpers ─────────────────────────────────────────────────────────── #
jp_regex   = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
eng_regex  = re.compile(r"^[A-Za-z0-9\s.'\"()\-]+$")

def normalise_case(en: str) -> str:
    """Fix ALL-CAPS or all-lowercase → Title Case; preserve known official spellings."""
    key = en.lower().strip()
    if en.isupper() or en.islower():
        return " ".join(w.capitalize() for w in re.split(r"(\W)", en.lower()))
    return en

def safe_json_load(txt: str):
    """
    1. Try vanilla json.loads().
    2. If that fails, strip Markdown code-fence wrappers like
       ```json { ... } ``` or ``` { ... } ```.
    3. As a last resort, grab the first {...} block in the string.
    """
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        pass

    # remove ```json … ``` or ``` … ```
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", txt, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass

    # fallback: first {...} in the whole payload
    brace_start = txt.find("{")
    brace_end   = txt.rfind("}")
    if brace_start != -1 and brace_end != -1:
        return json.loads(txt[brace_start: brace_end + 1])

    # give up—let the caller handle the error
    raise json.JSONDecodeError("No valid JSON found", txt, 0)

def update_glossary(extracted: Dict[str, str], master: Dict[str, List[str]]) -> None:
    """Merge one page’s glossary dict into the master glossary."""
    for jp, en in extracted.items():
        if not (jp_regex.search(jp) and eng_regex.match(en)):
            continue
        en = normalise_case(en)
        if jp not in master:
            master[jp] = [en]
        elif en not in master[jp]:
            master[jp].append(en)

def call_gemini(page_text: str) -> dict | str | None:
    """Ask Gemini to extract glossary. Walk through COMBOS on 429 errors."""
    global combo_idx
    api_key  = COMBOS[combo_idx]["key"]
    model_id = COMBOS[combo_idx]["model"]

    genai.configure(api_key=api_key)

    prompt = f"""Extract the glossary JSON for the following page:

<BEGIN_PAGE_TEXT>
{page_text}
<END_PAGE_TEXT>"""

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            model = genai.GenerativeModel(
                model_name=model_id,
                system_instruction=SYSTEM_PROMPT,
            )
            resp = model.generate_content(prompt)
            payload = resp.candidates[0].content.parts[0].text.strip()
            return safe_json_load(payload)

        except Exception as err:
            msg = str(err)
            if "429" in msg or "quota" in msg.lower():
                if combo_idx < len(COMBOS) - 1:
                    combo_idx += 1
                    next_combo = COMBOS[combo_idx]
                    print(f"\nRate-limited → switching to {next_combo['model']} on {'alt' if combo_idx%2 else 'primary'} key …")
                    time.sleep(RETRY_DELAY)
                    return call_gemini(page_text)
                else:
                    print("\nRate limit exhausted on all combos, ending safely.")
                    return "LIMITED"

            if attempt == MAX_RETRIES:
                print(f"\n(Gemini) final failure: {err}")
                return None
            time.sleep(RETRY_DELAY)

# ─── Main ─────────────────────────────────────────────────────────────── #
def main() -> None:
    # ---------- load page metadata & prepare output ----------
    if not TYPE_PATH.exists():
        raise FileNotFoundError(TYPE_PATH)

    with TYPE_PATH.open(encoding="utf-8") as f:
        pages = json.load(f)                    # List[dict]

    if GLOSSARY_PATH.exists():
        with GLOSSARY_PATH.open(encoding="utf-8") as f:
            glossary: Dict[str, List[str]] = json.load(f)
    else:
        glossary: Dict[str, List[str]] = {}

    print(f"Scanning {len(pages)} pages for raw text …")
    for page in tqdm(pages, unit="page"):
        page_no   = page["page_no"]
        rawtext   = page.get("rawtext", "").strip()

        if not page.get("contains_text") or not rawtext:
            continue                            # nothing to do

        if int(page_no) < START_PAGE or int(page_no) >= END_PAGE:
            continue

        # skip if we already captured terms from this page in a previous run
        # (quick heuristic: store a hidden marker)
        if "__glossary_extracted" in page:
            continue

        result = call_gemini(rawtext)
        if result == "LIMITED":
            break
        if not result:
            continue

        update_glossary(result.get("glossary", {}), glossary)
        page["__glossary_extracted"] = True     # mark so future reruns skip it

    # ---------- dump glossary ----------
    GLOSSARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with GLOSSARY_PATH.open("w", encoding="utf-8") as f:
        json.dump(glossary, f, ensure_ascii=False, indent=2)

    with TYPE_PATH.open("w", encoding="utf-8") as f:
        json.dump(pages, f, ensure_ascii=False, indent=2)

    print(f"✓ Fresh glossary written to {GLOSSARY_PATH}")

if __name__ == "__main__":
    main()
