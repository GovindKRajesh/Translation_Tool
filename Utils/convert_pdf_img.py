from pathlib import Path
import json
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit, ImageReader
from PIL import Image

# ─── Paths ──────────────────────────────────────────────────────────── #
BASE_DIR   = Path(".")
PROC_DIR   = BASE_DIR / "Processing_Files" / "Danmachi_vol20"
IMG_DIR    = BASE_DIR / "Input" / "Danmachi_vol20" / "Images"

MAPPING_PATH = PROC_DIR / "mapping.json"
OUT_PDF      = BASE_DIR / "Output" / "Danmachi_vol20" / "Danmachi_Vol20_EN.pdf"

TITLE = "Danmachi – Volume 20 (EN)"

# ─── Layout constants ──────────────────────────────────────────────── #
PAGE_SIZE    = letter
MARGIN       = 72        # 1 inch
LINE_SPACING = 14
PARA_SPACING = 20
BODY_FONT    = ("Helvetica", 12)
TITLE_FONT   = ("Helvetica-Bold", 20)

# ─── Image-handling constants (size + JPEG quality) ─────────────────── #
MAX_PX  = 1650   # longest edge after down-sampling  ≈ 300 dpi on Letter
JPEG_Q  = 85

# ─── Text page helper ───────────────────────────────────────────────── #
def _render_text_page(pdf: canvas.Canvas, text: str):
    pdf.showPage()                                          # fresh sheet
    width, height = PAGE_SIZE
    usable_w = width - 2 * MARGIN
    x, y = MARGIN, height - MARGIN
    pdf.setFont(*BODY_FONT)

    for raw in text.splitlines():
        if not raw.strip():                                 # blank line
            y -= PARA_SPACING
            continue
        for line in simpleSplit(raw.strip(), BODY_FONT[0], BODY_FONT[1], usable_w):
            if y < MARGIN + LINE_SPACING:                  # new PDF page
                pdf.showPage()
                pdf.setFont(*BODY_FONT)
                y = height - MARGIN
            pdf.drawString(x, y, line)
            y -= LINE_SPACING

# ─── Image page helper ──────────────────────────────────────────────── #
def _render_image_page(pdf: canvas.Canvas, img_path: Path):
    pdf.showPage()                                          # fresh sheet

    width, height = PAGE_SIZE
    img = Image.open(img_path).convert("RGB")

    # down-sample very large scans
    scale_px = MAX_PX / max(img.size)
    if scale_px < 1.0:
        new_size = (int(img.size[0] * scale_px), int(img.size[1] * scale_px))
        img = img.resize(new_size, Image.LANCZOS)

    # compress to in-memory JPEG
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_Q, optimize=True)
    buf.seek(0)
    img_reader = ImageReader(buf)

    iw, ih = img.size
    max_w, max_h = width - 2 * MARGIN, height - 2 * MARGIN
    scale = min(max_w / iw, max_h / ih)
    dw, dh = iw * scale, ih * scale
    x, y = (width - dw) / 2, (height - dh) / 2

    pdf.drawImage(img_reader, x, y, dw, dh,
                  preserveAspectRatio=True, anchor='c')
    # Do NOT call pdf.showPage() here; the helper already began with one.

# ─── Main converter ─────────────────────────────────────────────────── #
def mapping_to_pdf(mapping_path: Path, img_dir: Path, out_pdf: Path):
    raw = json.loads(mapping_path.read_text(encoding="utf-8"))
    pages = {str(p["page_no"]): p for p in (raw if isinstance(raw, list) else raw.values())}

    pdf = canvas.Canvas(str(out_pdf), pagesize=PAGE_SIZE)
    w, h = PAGE_SIZE

    # cover page
    pdf.setTitle(TITLE)
    pdf.setFont(*TITLE_FONT)
    pdf.drawString((w - pdf.stringWidth(TITLE, *TITLE_FONT)) / 2, h * 0.6, TITLE)
    pdf.showPage()

    for key in sorted(pages.keys(), key=lambda s: int(s)):
        rec = pages[key]
        img_path = img_dir / f"page_{int(key):03}.png"  # adjust ext if needed

        if rec.get("contains_illustration") and img_path.exists():
            _render_image_page(pdf, img_path)
            continue

        eng = rec.get("English", "").strip()
        _render_text_page(pdf, eng or "[Blank page]")

    pdf.save()
    print("✓ PDF written to", out_pdf)

# ─── Run ─────────────────────────────────────────────────────────────── #
if __name__ == "__main__":
    mapping_to_pdf(MAPPING_PATH, IMG_DIR, OUT_PDF)
