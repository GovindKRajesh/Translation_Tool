from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

TITLE = "Danmachi - Volume 19"


def txt_to_pdf_chapters(txt_file, pdf_file, margin=72, line_spacing=14, paragraph_spacing=20):
    """
    Convert a TXT file to a PDF with text wrapping, retaining paragraph spacing, and starting each chapter on a new page.

    Args:
    - txt_file (str): Path to the input TXT file.
    - pdf_file (str): Path to the output PDF file.
    - margin (int): Margin size in points (default: 72 points or 1 inch).
    - line_spacing (int): Spacing between lines in points (default: 14 points).
    - paragraph_spacing (int): Additional spacing between paragraphs (default: 20 points).
    """
    # Create the PDF canvas
    pdf = canvas.Canvas(pdf_file, pagesize=letter)
    width, height = letter

    pdf.setTitle(TITLE)
    pdf.setFont("Helvetica-Bold", 20)
    title_w = pdf.stringWidth(TITLE, "Helvetica-Bold", 20)
    pdf.drawString((width - title_w) / 2, height * 0.6, TITLE)
    pdf.showPage()
    y = height - margin
    pdf.setFont("Helvetica", 12)

    # Set usable width
    usable_width = width - 2 * margin

    # Start writing at the top of the page
    x = margin
    y = height - margin

    # Open and read the TXT file
    with open(txt_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    for line in lines:
        # Detect chapter headers and start a new page
        if line.strip().startswith("Chapter") or line.strip().startswith("Prologue"):
            pdf.showPage()  # Start a new page
            y = height - margin  # Reset the cursor to the top of the new page
            pdf.setFont("Helvetica-Bold", 14)  # Bold font for chapter title
            pdf.drawString(x, y, line.strip())
            y -= line_spacing * 2  # Add extra spacing after the chapter title
            pdf.setFont("Helvetica", 12)  # Reset font to normal
            continue

        # Retain blank lines as paragraph spacing
        if line.strip() == "":
            y -= paragraph_spacing
            continue

        # Wrap the text to fit within the page width
        wrapped_lines = simpleSplit(line.strip(), "Helvetica", 12, usable_width)

        for wrapped_line in wrapped_lines:
            # If the current line doesn't fit, create a new page
            if y < margin + line_spacing:
                pdf.showPage()
                y = height - margin

            # Write the wrapped line to the PDF
            pdf.drawString(x, y, wrapped_line)
            y -= line_spacing

    # Save the PDF
    pdf.save()
    print(f"PDF generated successfully: {pdf_file}")

# Example usage
txt_to_pdf_chapters("Output\English.txt", "Danmachi Volume 19 - v3.pdf")
