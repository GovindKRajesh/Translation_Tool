To run:
ollama run aya-expanse
ollama run qwen2.5

Docs:

Code:

- aya_expanse_test.py: Simple REST API call/test
- aya_translate_v1-basic.py: Direct translation, simple prompt
- aya_translate_v2-parallel.py: Parallel calls, basic prompt engineering
- aya_translate_v3-serial.py: Serial calls, overlap introduced, previous translation for context
- aya_translate_v4-glossary.py: Introduced dynamic glossary
- aya_generate_glossary.py: Generated glossary.json, which has Chinese-English mapping for proper nouns.

Text:

- Chinese.txt: Original Chinese Rawtext
- English_v1.txt: Translated using aya_translate_v2-parallel. Names are messed up, preceding text, messy context.
- English_v2.txt: Translated using aya_translate_v3-serial. Context is improved, other issues remain.
- English_v3.txt: Translated using aya_translate_v4-glossary. Names are fixed, only preceding text issue remains.
