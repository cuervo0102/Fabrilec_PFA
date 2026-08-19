import os
import pdfplumber
import pytesseract
from pdf2image import convert_from_path

TESSERACT_CMD = os.environ.get("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
if os.path.exists(TESSERACT_CMD):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

MIN_CHARS_PER_PAGE = 40
RUN_OCR = True


def extract_pdf(path: str) -> dict:
    text_pages = []
    method = "text"

    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text_pages.append(page.extract_text() or "")
    except Exception as e:
        return {"text": "", "method": "error", "error": str(e), "n_pages": 0}

    n_pages = len(text_pages)
    total_chars = sum(len(t) for t in text_pages)
    needs_ocr = n_pages > 0 and (total_chars / max(n_pages, 1)) < MIN_CHARS_PER_PAGE

    if needs_ocr:
        if not RUN_OCR:
            return {"text": "\n".join(text_pages), "method": "needs_ocr", "n_pages": n_pages}

        method = "ocr"
        max_ocr_pages = min(n_pages, 25)
        ocr_pages = []
        try:
            for i in range(1, max_ocr_pages + 1):
                images = convert_from_path(path, dpi=150, first_page=i, last_page=i)
                if images:
                    ocr_pages.append(pytesseract.image_to_string(images[0], lang="fra"))
                    del images
            text_pages = ocr_pages
        except Exception as e:
            return {"text": "\n".join(ocr_pages), "method": "ocr_partial_failed", "error": str(e), "n_pages": n_pages}

    return {"text": "\n".join(text_pages), "method": method, "n_pages": n_pages}