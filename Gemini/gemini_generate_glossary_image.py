from __future__ import annotations

import json, os, time, re
from pathlib import Path
from typing import Dict, List
from PIL import Image
from tqdm import tqdm
import google.generativeai as genai
from dotenv import load_dotenv

# ─── Config ──────────────────────────────────────────────────────────── #
load_dotenv()
MODEL_NAME          = "gemini-2.5-flash-preview-05-20"
GEMINI_KEY          = os.environ["GEMINI_KEY"]
IMAGES_DIR          = Path(".\Input\Danmachi_vol20\Images")
GLOSSARY_PATH       = Path(".\Processing_Files\Danmachi_vol20\Glossary.json")
TYPE_PATH           = Path(".\Processing_Files\Danmachi_vol20\Type.json")
SIZE_LIMIT_BYTES    = 7 * 1024 * 1024                 # 7 MB
MAX_RETRIES         = 3
RETRY_DELAY         = 6

# ─── System instruction – stricter glossary-only extractor ───────────── #
SYSTEM_PROMPT = """
You are an expert Japanese-to-English glossary extractor.

Task for **each page image**:
1. Read the Japanese text in the image (perform OCR if needed).
2. List **only** proper nouns or world-specific common nouns (characters, skills, locations, organisations, items, races, etc.). Ignore normal vocabulary.
3. Output **strictly valid JSON object** with exactly these keys:
   {
     "glossary": { "<JP>": "<EN>", ... },   # may be empty {}
     "contains_text": true|false,
     "contains_illustration": true|false
   }
4. `contains_text` is true if any text is present at all.
5. `contains_illustration` is true if the page includes drawings / diagrams / manga illustrations, otherwise false.
6. Return only a JSON object, without any markdown.
7. This image comes from the Light Novel of Danmachi, also known as "Danjon ni Deai o Motomeru no wa Machigatteiru Darō ka" or "Is It Wrong to Try to Pick Up Girls in a Dungeon?". 
When extracting the glossary, make sure you use the context of this Novel from your knowledge, and use official names where possible.
8. Use the official English renderings that appear in the Yen-Press / SB Creative releases whenever you recognise them (e.g. "Syr Flover", "Ryuu Lion", "Loki Familia").
9. If an official spelling is unknown, write the term in *title case* (only the first letter of each word capitalised) and never in all-caps.

Return nothing else.
"""

# ─── Helpers ─────────────────────────────────────────────────────────── #
jp_regex   = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
eng_regex  = re.compile(r"^[A-Za-z0-9\s.'\"()\-]+$")

def update_glossary(extracted: Dict[str, str], master: Dict[str, List[str]]) -> None:
    """
    Merge one page’s glossary dict into the master glossary,
    keeping a list of distinct English renderings.
    """
    for jp, en in extracted.items():
        if not (jp_regex.search(jp) and eng_regex.match(en)):
            continue
        if jp not in master:
            master[jp] = [en]
        elif en not in master[jp]:
            master[jp].append(en)

def call_gemini(image_path: Path) -> dict | None:
    """Ask Gemini to produce the JSON payload for one image."""
    genai.configure(api_key=GEMINI_KEY or os.getenv("GOOGLE_API_KEY", ""))

    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=SYSTEM_PROMPT,
    )

    prompt = "Extract glossary JSON for this page."
    img    = Image.open(image_path)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = model.generate_content([prompt, img])
            payload = resp.candidates[0].content.parts[0].text.strip()
            return json.loads(payload)          # validates JSON
        except Exception as err:
            if attempt == MAX_RETRIES:
                print(f"[{image_path.name}] failed: {err}")
                return None
            time.sleep(RETRY_DELAY)

# ─── Main ─────────────────────────────────────────────────────────────── #
def main() -> None:
    GLOSSARY_PATH.parent.mkdir(parents=True, exist_ok=True)

    glossary: Dict[str, List[str]]  = {}
    page_types: List[dict]          = []

    image_paths = sorted(IMAGES_DIR.glob("page_*.png"))

    print(f"Processing {len(image_paths)} page(s)…")
    
    for img_path in tqdm(image_paths, unit="page"):
        size_ok = img_path.stat().st_size <= SIZE_LIMIT_BYTES
        if not size_ok:
            page_types.append(
                {"page_no": img_path.stem.split("_")[1],
                 "contains_text": False,
                 "contains_illustration": True}
            )
            continue

        result = call_gemini(img_path)
        if not result:
            continue

        # Update master glossary & type list
        update_glossary(result.get("glossary", {}), glossary)
        page_types.append(
            {"page_no": img_path.stem.split("_")[1],
             "contains_text": bool(result.get("contains_text")),
             "contains_illustration": bool(result.get("contains_illustration"))}
        )

    # ── Dump files ──────────────────────────────────────────────────── #
    with open(GLOSSARY_PATH, "w", encoding="utf-8") as f:
        json.dump(glossary, f, ensure_ascii=False, indent=2)
    with open(TYPE_PATH, "w", encoding="utf-8") as f:
        json.dump(page_types, f, ensure_ascii=False, indent=2)

    print(f"✓ Glossary written to {GLOSSARY_PATH}")
    print(f"✓ Page types written to {TYPE_PATH}")

if __name__ == "__main__":
    main()
