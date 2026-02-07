from pathlib import Path
import json

TYPE_PATH = Path(".\Processing_Files\Danmachi_vol20\Type.json")

def main() -> None:
    if not TYPE_PATH.exists():
        raise FileNotFoundError(TYPE_PATH)

    with TYPE_PATH.open(encoding="utf-8") as f:
        pages = json.load(f)          # List[dict]

    changed = False
    for page in pages:
        if page.pop("__glossary_extracted", None) is not None:
            changed = True

    if changed:
        with TYPE_PATH.open("w", encoding="utf-8") as f:
            json.dump(pages, f, ensure_ascii=False, indent=2)
        print("✓ All '__glossary_extracted' keys removed.")
    else:
        print("No '__glossary_extracted' keys found—nothing to do.")

if __name__ == "__main__":
    main()
