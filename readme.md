# Translation Project

This repo is a **chunked Chinese → English translation workflow** with **glossary enforcement** and **resume support**.

## Process

1. **Prepare input text**
   Put your source Chinese text into the expected input file (see “Run options” below).

2. **Build the glossary (recommended)**
   Generate a `glossary.json` mapping of key terms/names → preferred English renderings. Feel free to manually update this after automated build. This reduces inconsistency across chunks.

3. **Run the Translation script (resumable)**
   The translator splits the input into chunks, translates each chunk, and writes progress to a `mapping.json` so you can re-run safely after failures.

4. **Concatenate output and optionally output as PDF**
   The final English output is produced by stitching translated chunks together (the Gemini script also normalizes whitespace/newlines).

---

## Run options

### Option A: Local translation with Aya Expanse (Ollama)

**What you get:** Fully local translation + strict glossary checking.

**Requirements:** Enough GPU VRAM to run the specific model (aya-expanse:8b), Ollama installed and setup with this model loaded.

1. Run glossary generation:

```bash
python aya_generate_glossary.py
```

2. Run translation:

```bash
python aya_translate_v6.py
```

---

### Option B: Gemini translation (API)

**What you get:** Translation via Gemini, optional style profile generation.

**Requirements:** Gemini API key, ideally a paid one for better limits (free will work, but will require resuming across multiple days).

1. Run glossary generation:

```bash
python gemini_generate_glossary_rawtext.py
```

2. (Optional) Generate a writing style profile:

```bash
python gemini_generate_writing_style.py
```

3. Set API key and translate:
   **Windows (PowerShell)**

```powershell
$env:GOOGLE_API_KEY="YOUR_KEY"
python gemini_translate_v4.py
```

**Linux/macOS**

```bash
export GOOGLE_API_KEY="YOUR_KEY"
python gemini_translate_v4.py
```

---

## Notes

- Re-running scripts is safe: translation progress is stored in `mapping.json` and completed chunks are skipped.
- It is strongly recommended to go to Processing_Files/<YourFolderName>/glossary.json after generating the Glossary, and updating the English names as required before running further steps.
