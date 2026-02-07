from __future__ import annotations

from dotenv import load_dotenv
import json, logging, os, re, sys, time
from pathlib import Path
from typing import Dict, List, Any

import google.generativeai as genai
from tqdm import tqdm

# ───────────────────────── CONFIG ───────────────────────── #
load_dotenv()
PRIMARY_KEY = os.environ["GEMINI_KEY"]   # main key
ALT_KEY     = os.environ["GEMINI_ALT_KEY"]   # backup key

MODEL_ID   = "gemini-2.5-flash-preview-05-20"
MAX_RETRIES, RETRY_DELAY = 3, 5
MISS_ALLOWED = 0

IMG_DIR    = Path(".") / "Input" / "Danmachi_vol20" / "Images"

BASE = Path(".") / "Processing_Files" / "Danmachi_vol20"
TYPE_PATH     = BASE / "Type.json"
GLOSSARY_PATH = BASE / "Glossary_v4.json"
STYLE_PATH    = BASE / "style_profile.json"
MAPPING_PATH  = BASE / "mapping.json"
LOG_PATH      = BASE / "translation_log.log"
STYLE_PROFILE_PATH = BASE / "style_profile.json"

OUT_DIR = Path(".") / "Output" / "Danmachi_vol20"
OUT_DIR.mkdir(parents=True, exist_ok=True)
EN_TXT  = OUT_DIR / "English.txt"

# rotation order
COMBOS = [{"key": k, "tag": tag, "model": MODEL_ID}
          for k, tag in [(PRIMARY_KEY, "primary"), (ALT_KEY, "alt")] if k]
combo_idx = 0

# failure guidance
FAILURE_HINT = {
    "Incomplete": "Your previous attempt contained Japanese characters. Return pure English.",
    "Preceding":  "Do not prefix explanations. Start directly with the translation.",
    "Glossary":   "One or more glossary terms were missing or altered.  Use them verbatim.",
}

# ─────────────── LOGGING ─────────────── #
logging.basicConfig(filename=LOG_PATH,
                    level=logging.INFO,
                    format="%(asctime)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")

# ────────────────────────── LOAD STYLE PROFILE ───────────────────────── #

try:
    with open(STYLE_PROFILE_PATH, encoding="utf-8") as fp:
        STYLE_PROFILE = json.load(fp)
except FileNotFoundError:
    print(f"[ERROR] Style profile '{STYLE_PROFILE_PATH}' not found. "
          "Run the style-extraction script first.")
    sys.exit(1)

STYLE_PROFILE_TXT = json.dumps(STYLE_PROFILE, ensure_ascii=False, indent=2)

# ───────────────── HELPERS ────────────── #
def load_json(p: Path, default):
    return json.load(p.open(encoding="utf-8")) if p.exists() else default

def load_glossary(path: Path) -> Dict[str, List[str]]:
    raw = load_json(path, {})
    return {k: (v if isinstance(v, list) else [v]) for k, v in raw.items()}

JP_RE = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')

def filter_glossary(txt: str, gloss: Dict[str, List[str]]):
    hits = [k for k in gloss if k in txt]
    hits.sort(key=len, reverse=True)
    chosen = []
    for h in hits:
        if not any(h in c for c in chosen):
            chosen.append(h)
    return {k: gloss[k] for k in chosen}

def check_valid(text: str, sub: Dict[str, List[str]]):
    if JP_RE.search(text): return "Incomplete", []
    if text.strip().lower().startswith("translation"): return "Preceding", []
    miss = []
    for jp, en_list in sub.items():
        if not re.search("|".join(map(re.escape, en_list)), text, flags=re.I):
            miss.append(f"{jp} → {en_list[0]}")
    verdict = "AllGood" if len(miss) <= MISS_ALLOWED else "Glossary"
    return verdict, miss

def normalise(txt: str) -> str:
    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return "\n".join(l.rstrip() for l in txt.split("\n")).strip() + "\n"

# ───────────────── GEMINI CALL ────────── #
SYSTEM_TEMPLATE = f"""
You are a highly skilled literary translator (JP ➜ EN).

✦ Formatting rules (MANDATORY) ✦
• Treat every source paragraph break as *exactly* one empty line in English.
  ↳ Dialogue counts as its own paragraph.
• Never output two or more consecutive empty lines.
• Use Unix newlines \\n (not \\r\\n).
• Do NOT indent; no extra spaces at line ends.

Follow these immutable rules:
1. Respect the glossary exactly; names must match spelling & capitalisation. If a glossary term is found in the text, translate exactly as the glossary prescribes.
2. Translate literally unless awkward; then smooth minimally.
3. NO honorifics unless they exist in the glossary.
4. Output only English text, no comments / brackets / Japanese chars.
5. You will be penalized if you do not strictly adhere to the above rules.
6. Do not use literal/phonetic Japanese translations (Romanji) unless it makes sense as per the story.

Target style guide (condensed JSON):
{STYLE_PROFILE_TXT}
"""

def gemini_call(prompt: str):
    global combo_idx
    api_key = COMBOS[combo_idx]["key"]
    genai.configure(api_key=api_key)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            model = genai.GenerativeModel(MODEL_ID, system_instruction=SYSTEM_TEMPLATE)
            txt = model.generate_content(prompt).candidates[0].content.parts[0].text.strip()
            return txt, ""
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                if combo_idx < len(COMBOS) - 1:
                    combo_idx += 1
                    print(f"\nQuota hit → switching to {COMBOS[combo_idx]['tag']} key …")
                    time.sleep(RETRY_DELAY)
                    return gemini_call(prompt)
                return None, "LIMITED"
            if attempt == MAX_RETRIES:
                return None, f"EXCEPTION {e}"
            time.sleep(RETRY_DELAY)

# ────────────────── MAIN FLOW ──────────── #
def main() -> None:
    pages = load_json(TYPE_PATH, [])
    if not pages: print("[ERR] Type.json missing."); return
    glossary = load_glossary(GLOSSARY_PATH)
    if not glossary: print("[ERR] Glossary missing."); return

    raw_map: Any = load_json(MAPPING_PATH, {})
    if isinstance(raw_map, list):
        mapping = {str(p["page_no"]): p for p in raw_map}
    elif isinstance(raw_map, dict):
        mapping = raw_map
    else:
        mapping = {}

    for n in range(1, 424):
        key = f"{n:03}"
        img_file = IMG_DIR / f"page_{key}.png"
        if key not in mapping and img_file.exists() and img_file.stat().st_size > 7*1024*1024:
            mapping[key] = {
                "page_no": key,
                "contains_text": False,
                "contains_illustration": True,
                "rawtext": "",
                "English": "",
                "Glossary": {}
            }

    # --- resolve pages that are wrongly flagged as both text + illustration
    for rec in mapping.values():
        if rec.get("contains_text") and rec.get("contains_illustration"):
            if len(rec.get("rawtext", "")) > 200:
                rec["contains_illustration"] = False
            else:
                rec["contains_text"] = False

    done = [int(k) for k, v in mapping.items()
        if v.get("English") not in (None, "ERROR")]

    prev_tail = ""
    if done:
        last_num  = max(done)
        last_key  = next(k for k in mapping if int(k) == last_num)
        if mapping[last_key].get("English") == "ERROR":
            del mapping[last_key]
            done.remove(last_num)
            prev_tail = ""

    work = [p for p in pages if p.get("contains_text") and p.get("rawtext")]

    # ─── TEST-MODE FILTER (uncomment to limit to pages 13-15) ───
    # work = [p for p in work if 13 <= int(p["page_no"]) <= 15]
    # -----------------------------------------------------------------

    with tqdm(total=len(work), desc="Translating") as bar:
        for page in work:
            pno = str(page["page_no"])
            if mapping.get(pno, {}).get("English"): bar.update(1); continue

            raw = page["rawtext"]
            sub = filter_glossary(raw, glossary)
            gloss_txt = "\n".join(f'"{k}": "{", ".join(v)}"' for k, v in sub.items()) or "[none]"

            retry_hint = ""
            attempt = 0
            answer = None
            while attempt < MAX_RETRIES:
                attempt += 1
                prompt = f"""
Glossary terms (enforce exactly):
{gloss_txt}

Previous English tail:
{prev_tail or '[none]'}

Translate continuously:
{raw}
{retry_hint}
"""
                answer, err = gemini_call(prompt)
                if err == "LIMITED": break
                if answer is None:
                    logging.info(f"Page {pno}: {err}"); time.sleep(RETRY_DELAY); continue

                verdict, miss = check_valid(answer, sub)
                logging.info(f"Page {pno}: attempt {attempt} verdict={verdict} miss={miss}")

                if verdict == "AllGood": break
                if attempt >= MAX_RETRIES: answer = None; break

                retry_hint = ("\n\nYou MISSED/MISTRANSLATED:\n- " + "\n- ".join(miss)
                              if verdict == "Glossary" else "\n\n" + FAILURE_HINT[verdict])
                time.sleep(RETRY_DELAY)

            # store result
            mapping[pno] = {**page,
                            "English": normalise(answer) if answer else "ERROR",
                            "Glossary": sub}
            _flush(mapping)

            if answer == "ERROR" or err == "LIMITED" or answer == None:
                print("\nStopped — fix issues then rerun.")
                return

            prev_tail = "\n".join(answer.strip().splitlines()[-2:])
            bar.update(1)

    _dump_english(EN_TXT, mapping)
    print("\nDone! English output →", EN_TXT)

# ───── file helpers ───── #
def _flush(data):
    with MAPPING_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _dump_english(path: Path, data: dict):
    with path.open("w", encoding="utf-8") as out:
        # sort by numeric value but keep the original zero-padded key
        for key in sorted(data.keys(), key=lambda s: int(s)):
            eng = data[key].get("English", "")
            if eng and eng != "ERROR":
                out.write(eng + "\n")

# ───── run ───── #
if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt:
        print("\nInterrupted – progress saved; run again.")
