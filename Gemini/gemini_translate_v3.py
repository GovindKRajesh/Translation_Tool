from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
import re
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv

import google.generativeai as genai
import tiktoken
from tqdm import tqdm

# ──────────────────────────────── CONFIG ──────────────────────────────── #
load_dotenv()
GEMINI_KEY = os.environ["GEMINI_KEY"]

MODEL_NAME = "gemini-2.5-flash-preview-05-20"
TOKENS_PER_CHUNK = 1000
MAX_RETRIES = 3
RETRY_DELAY = 5
MISS_ALLOWED = 0

STYLE_PROFILE_PATH = ".\Processing_Files\style_profile.json"
GLOSSARY_PATH       = ".\Processing_Files\glossary.json"
STAGING_PATH        = ".\Processing_Files\mapping.json"
INPUT_CHINESE_PATH  = ".\Input\Chinese.txt"
OUTPUT_ENGLISH_PATH = ".\Output\English.txt"

# ──────────────────────── LOGGING (same file as before) ───────────────── #

logging.basicConfig(
    filename="translation_log.log",
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ────────────────────────── LOAD STYLE PROFILE ───────────────────────── #

try:
    with open(STYLE_PROFILE_PATH, encoding="utf-8") as fp:
        STYLE_PROFILE = json.load(fp)
except FileNotFoundError:
    print(f"[ERROR] Style profile '{STYLE_PROFILE_PATH}' not found. "
          "Run the style-extraction script first.")
    sys.exit(1)

STYLE_PROFILE_TXT = json.dumps(STYLE_PROFILE, ensure_ascii=False, indent=2)

# ───────────────────── STATIC PART OF SYSTEM MESSAGE ──────────────────── #

SYSTEM_TEMPLATE = f"""
You are a highly skilled literary translator (CN ➜ EN).

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
4. Output only English text, no comments / brackets / Chinese chars.
5. You will be penalized if you do not strictly adhere to the above rules.

Target style guide (condensed JSON):
{STYLE_PROFILE_TXT}
"""

# ────────────────────────── FAILURE MESSAGES ─────────────────────────── #

FAILURE_HINT = {
    "Incomplete": "Your previous attempt contained Chinese characters. Return pure English.",
    "Preceding":  "Do not prefix explanations.  Start directly with the translation.",
    "Glossary":   "One or more glossary terms were missing or altered.  Use them verbatim.",
}

# ───────────────────────── HELPER FUNCTIONS ──────────────────────────── #


def chunk_text(file_path: str, tokens_per_chunk: int, encoding_name: str = "cl100k_base") -> List[str]:
    enc = tiktoken.get_encoding(encoding_name)
    with open(file_path, encoding="utf-8") as fh:
        lines = fh.readlines()

    chunks, buf, buf_tokens = [], [], 0
    for line in lines:
        toks = enc.encode(line)
        if buf_tokens + len(toks) > tokens_per_chunk:
            chunks.append(enc.decode(sum(buf, [])))
            buf, buf_tokens = [], 0
        buf.append(toks)
        buf_tokens += len(toks)
    if buf:
        chunks.append(enc.decode(sum(buf, [])))

    print(f"[INFO] File split into {len(chunks)} chunks "
          f"({sum(len(enc.encode(c)) for c in chunks)} tokens).")
    return chunks


def filter_glossary(chunk: str, glossary: Dict[str, List[str]]) -> Dict[str, List[str]]:
    hits = [k for k in glossary if k in chunk]
    if not hits:
        return {}
    hits.sort(key=len, reverse=True)
    selected: list[str] = []
    for key in hits:
        if not any(key in longer for longer in selected):
            selected.append(key)
    return {k: glossary[k] for k in selected}


def translation_validity(text: str, glossary_subset: Dict[str, List[str]]) -> tuple[str, list[str]]:
    """
    Returns (verdict, missing_terms)
    verdict ∈ {"AllGood", "Incomplete", "Preceding", "Glossary"}
    """
    if re.search(r"[\u4e00-\u9fff]", text):
        return "Incomplete", []

    if text.strip().lower().startswith("translation"):
        return "Preceding", []

    missing = []
    for cn_term, eng_variants in glossary_subset.items():
        pattern = "|".join(map(re.escape, eng_variants))
        if not re.search(pattern, text, flags=re.I):
            missing.append(f'{cn_term} → {eng_variants[0]}')

    # Apply tolerance
    if len(missing) <= MISS_ALLOWED:
        return "AllGood", missing

    return "Glossary", missing


def gemini_call(prompt: str) -> tuple[str | None, str]:
    """
    Returns (text_or_None, err_reason).  err_reason is '' on success.
    """
    try:
        genai.configure(api_key=GEMINI_KEY or os.getenv("GOOGLE_API_KEY", ""))

        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=SYSTEM_TEMPLATE,
        )

        resp = model.generate_content(
            prompt
        )

        if not resp.candidates:
            reason = getattr(resp, "prompt_feedback", None)
            return None, f"SAFETY_BLOCK ({reason})"

        cand = resp.candidates[0]
        if not getattr(cand, "content", None) or not cand.content.parts:
            return None, "EMPTY_PARTS"

        return cand.content.parts[0].text.strip(), ""

    except Exception as exc:
        return None, f"EXCEPTION {exc}"


def build_user_prompt(prev_tail: str, chunk: str, gloss_subset_txt: str) -> str:
    return f"""
Glossary terms to enforce:
{gloss_subset_txt}

Previous English context (tail):
{prev_tail}

Translate the following Chinese text **continuously**:
{chunk}
"""


def load_json(path: str, default):
    if Path(path).exists():
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return default


def _normalise_newlines(text: str) -> str:
    """Collapse multiple blank lines, unify \\r\\n → \\n, strip trail-spaces."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 1+ blank lines → exactly one
    text = re.sub(r"\n{3,}", "\n\n", text)
    # strip spaces at EOL
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return text.strip() + "\n"


# ────────────────────── MAIN PROCESSING FUNCTION ─────────────────────── #

def process_file() -> None:
    # — Load resources -------------------------------------------------- #
    chunks = chunk_text(INPUT_CHINESE_PATH, TOKENS_PER_CHUNK)
    glossary: Dict[str, List[str]] = load_json(GLOSSARY_PATH, {})
    if not glossary:
        print("[ERROR] Glossary not found / empty.")
        return

    staging = load_json(STAGING_PATH, {})

    # Figure out where to resume
    completed_ids = {
        int(k.split()[1])
        for k, v in staging.items()
        if v.get("English") and v["English"] != "ERROR"
    }
    next_index = max(completed_ids) + 1 if completed_ids else 1
    prev_translation_tail = "[No previous context available]"
    if next_index > 1:
        # get last two lines of the previous successful English
        prev_text = staging[f"chunk {next_index-1}"]["English"]
        prev_translation_tail = "\n".join(prev_text.strip().splitlines()[-2:])

    # — Translate loop -------------------------------------------------- #
    with tqdm(total=len(chunks), initial=next_index - 1, desc="Translating") as bar:
        for idx in range(next_index, len(chunks) + 1):
            chunk = chunks[idx - 1]
            gloss_subset = filter_glossary(chunk, glossary)
            gloss_txt = "\n".join(
                f'"{k}": "{", ".join(v)}"' for k, v in gloss_subset.items()
            )

            retry_hint = ""
            response: str | None = None
            attempt = 0

            while attempt < MAX_RETRIES:
                attempt += 1

                user_prompt = build_user_prompt(
                    prev_translation_tail, chunk, gloss_txt
                ) + retry_hint

                response, err = gemini_call(user_prompt)

                if response is None:
                    logging.info(f"Chunk {idx}: attempt {attempt} -> {err}")
                    time.sleep(RETRY_DELAY)
                    continue

                verdict, missing = translation_validity(response, gloss_subset)
                logging.info(
                    f"Chunk {idx}: attempt {attempt} verdict={verdict} "
                    f"missing={missing}"
                )

                if verdict == "AllGood":
                    response = _normalise_newlines(response)
                    break

                if attempt >= MAX_RETRIES:
                    print("\n",response)
                    response = None
                    break

                # Build corrective hint for next attempt
                retry_hint = (
                    "\n\nYou MISSED/MISTRANSLATED the following glossary terms; "
                    "include them exactly:\n- " + "\n- ".join(missing)
                    if verdict == "Glossary"
                    else "\n\n" + FAILURE_HINT.get(verdict, "")
                )
                time.sleep(RETRY_DELAY)

            # — Record result & update tail ----------------------------- #
            staging[f"chunk {idx}"] = {
                "Chinese": chunk,
                "English": response,
                "Glossary": gloss_subset,
            }
            _flush_staging(staging)
            if response == "ERROR":
                print(f"\n[STOPPED] Validation failed for chunk {idx}. "
                      "Fix glossary or rerun later.")
                return

            prev_translation_tail = "\n".join(response.strip().splitlines()[-2:])
            bar.update(1)

    # — Concatenate all English snippets into final file --------------- #
    _extract_english(STAGING_PATH, OUTPUT_ENGLISH_PATH)
    print("\nTranslation complete!  Check", OUTPUT_ENGLISH_PATH)


# ──────────────────────────── UTILITIES ──────────────────────────────── #

def _flush_staging(data) -> None:
    with open(STAGING_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _extract_english(mapping_file: str, out_file: str) -> None:
    data = load_json(mapping_file, {})
    with open(out_file, "w", encoding="utf-8") as out:
        for idx in range(1, len(data) + 1):
            eng = data.get(f"chunk {idx}", {}).get("English", "")
            if eng and eng != "ERROR":
                out.write(eng + "\n")


# ──────────────────────────────── MAIN ──────────────────────────────── #

if __name__ == "__main__":
    try:
        process_file()
    except KeyboardInterrupt:
        print("\nInterrupted by user. Progress is saved; run again to resume.")
