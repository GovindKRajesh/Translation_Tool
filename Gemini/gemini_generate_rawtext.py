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
MODEL_NAME          = "gemini-2.5-pro"
GEMINI_KEY          = os.environ["GEMINI_KEY"]
IMAGES_DIR          = Path(".\Input\Danmachi_vol20\Images")
TYPE_PATH           = Path(".\Processing_Files\Danmachi_vol20\Type.json")
SIZE_LIMIT_BYTES    = 2 * 1024 * 1024                 # 2 MB
MAX_RETRIES         = 3
RETRY_DELAY         = 6                               # seconds

# ─── System instruction – OCR with ruby tagging ──────────────────────── #
SYSTEM_PROMPT = """
You are an OCR agent for Japanese light-novel pages.

For each page image you receive:
1. Transcribe **all visible text verbatim**, preserving line-breaks. However, do not insert line-breaks in the middle of words.
2. Wrap every ruby/furigana reading in back-ticks, e.g. 漢字`かんじ`.
3. If a name is partially illegible but you recognise it from Danmachi, substitute the **official Japanese spelling**.
4. This image is from the light novel *Danmachi* (“Danjon ni Deai o Motomeru no wa Machigatteiru Darō ka”, “Is It Wrong to Try to Pick Up Girls in a Dungeon?”); use that context for resolving proper-nouns that may not be clear in the image.
5. Return **only** a JSON object following this format:
   {
     "rawtext": "<transcribed text>"
   }
6. Return only a JSON object, without any markdown.
7. Think very carefully about each word that you transcribe. If you find that the word that you're about to output is not meshing with the context thus far, check the image once more to ensure that your transciption is accurate.
8. If you are unsure about what to transcribe for any specific sequence, check the image again and make sure, instead of guessing.
9. Punctuation, brackets, spacing, line breaks, etc. from the image must be perfectly carried over to your transcription.
"""

# ─── Helpers ─────────────────────────────────────────────────────────── #
def call_gemini(image_path: Path) -> dict | None:
    """Ask Gemini for the structured OCR payload of one page image."""
    genai.configure(api_key=GEMINI_KEY or os.getenv("GOOGLE_API_KEY", ""))

    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=SYSTEM_PROMPT,
    )

    prompt = "Transcribe this page per the rules."
    img    = Image.open(image_path)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = model.generate_content([prompt, img])
            raw = resp.candidates[0].content.parts[0].text.strip()
            payload = _strip_code_fence(raw)
            return json.loads(payload)          # validates that we got pure JSON
        except Exception as err:
            if attempt == MAX_RETRIES:
                print(f"[{image_path.name}] failed: {err}")
                return None
            time.sleep(RETRY_DELAY)

def _strip_code_fence(text: str) -> str:
    """
    Remove a leading/closing ``` or ```json fence if present.
    Keeps inner payload unchanged.
    """
    # leading fence
    text = re.sub(r'^\s*```(?:json)?\s*', '', text, flags=re.IGNORECASE)
    # trailing fence
    text = re.sub(r'\s*```\s*$', '', text)
    return text.strip()

# ─── Main ─────────────────────────────────────────────────────────────── #
def main() -> None:
    TYPE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Load existing Type.json if present
    page_types: List[dict]
    if TYPE_PATH.exists():
        with open(TYPE_PATH, encoding="utf-8") as f:
            page_types = json.load(f)
    else:
        page_types = []

    # Map for quick lookup / update
    by_page: Dict[str, dict] = {p["page_no"]: p for p in page_types}

    test_page = IMAGES_DIR / "page_013.png"
    image_paths = [test_page] if test_page.exists() else []
    #image_paths = sorted(IMAGES_DIR.glob("page_*.png"))

    print(f"Processing {len(image_paths)} page(s)…")
    for img_path in tqdm(image_paths, unit="page"):
        page_no = img_path.stem.split("_")[1]

        # skip processed pages
        if by_page.get(page_no, {}).get("rawtext"):
            continue

        # big illustration pages ­– mark, but skip OCR to save quota
        if img_path.stat().st_size > SIZE_LIMIT_BYTES:
            rec = by_page.get(page_no, {})
            rec.update({
                "page_no": page_no,
                "contains_text": False,
                "contains_illustration": True,
                "rawtext": ""
            })
            by_page[page_no] = rec
            continue

        result = call_gemini(img_path)
        if not result:
            continue

        rec = by_page.get(page_no, {})
        rec.update({
            "page_no": page_no,
            "contains_text": True,
            "contains_illustration": False,
            "rawtext": result.get("rawtext", "")
        })
        by_page[page_no] = rec

    # dump back in natural numeric order
    updated = sorted(by_page.values(), key=lambda d: int(d["page_no"]))
    with open(TYPE_PATH, "w", encoding="utf-8") as f:
        json.dump(updated, f, ensure_ascii=False, indent=2)

    print(f"✓ Updated page metadata + raw text written to {TYPE_PATH}")

if __name__ == "__main__":
    main()
