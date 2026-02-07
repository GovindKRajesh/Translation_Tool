from pathlib import Path
import json

MAPPING_PATH = Path("./Processing_Files/Danmachi_vol20/mapping.json")

def main():
    data = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))

    # tolerant to old list format
    if isinstance(data, list):
        pages = {str(p["page_no"]): p for p in data}
    else:
        pages = {str(k): v for k, v in data.items()}

    both = [
        int(k) for k, rec in pages.items()
        if rec.get("contains_text") and rec.get("contains_illustration")
    ]
    both.sort()

    print("Pages that contain *both* text and illustration:")
    print(both or "[none]")

if __name__ == "__main__":
    main()
