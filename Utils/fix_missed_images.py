from pathlib import Path
import json

MAPPING_PATH = Path("./Processing_Files/Danmachi_vol20/mapping.json")

def main() -> None:
    if not MAPPING_PATH.exists():
        raise FileNotFoundError(MAPPING_PATH)

    data = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))

    # legacy list → dict upgrade
    if isinstance(data, list):
        data = {str(p["page_no"]): p for p in data}

    added = 0
    for num in range(1, 424):          # 001 … 423 inclusive
        key = f"{num:03}"
        if key not in data:
            data[key] = {
                "page_no": key,
                "contains_text": False,
                "contains_illustration": True,
                "rawtext": "",
                "English": "",
                "Glossary": {}
            }
            added += 1

    if added:
        MAPPING_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                encoding="utf-8")
        print(f"✓ Added {added} missing page(s). mapping.json updated.")
    else:
        print("All pages already present – no changes made.")

if __name__ == "__main__":
    main()
