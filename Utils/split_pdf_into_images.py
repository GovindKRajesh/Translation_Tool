from pathlib import Path
from pdf2image import convert_from_path

# ─── Paths ──────────────────────────────────────────────────────────────
PDF_PATH  = Path(".\Input\Danmachi_vol20\Danmachi_vol20.pdf")
OUT_DIR   = Path(".\Input\Danmachi_vol20\Images")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ─── Render & save ───────────────────────────────────────────────────────
# 600 dpi ⇒ ~2× typical screen resolution; adjust if files get too big
pages = convert_from_path(
    PDF_PATH,
    dpi=600,
    fmt="png",            # keeps transparency off; change to "jpeg" if you like
    thread_count=4        # speeds things up on multi-core CPUs
    # poppler_path=r"C:\Tools\poppler-24.02.0\Library\bin"  # <- uncomment if needed
)

for i, page in enumerate(pages, start=1):
    out_file = OUT_DIR / f"page_{i:03}.png"
    page.save(out_file, "PNG")
    print(f"✅  Saved {out_file}")

print(f"\nDone. {len(pages)} pages written to {OUT_DIR.resolve()}")