from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF
import pytesseract
from pytesseract import Output


@dataclass(frozen=True)
class OCRResult:
    text: str
    method: str  # 'pymupdf' | 'tesseract'
    confidence: float
    pages: int


def _pymupdf_extract(pdf_path: str) -> tuple[str, int, list[dict]]:
    """Returns (full_text, page_count, page_chunks)
    where each chunk = {page: int, text: str}
    """
    doc = fitz.open(pdf_path)
    try:
        pages = doc.page_count
        parts: list[str] = []
        chunks: list[dict] = []
        for i in range(pages):
            page = doc.load_page(i)
            text = page.get_text("text")
            parts.append(text)
            chunks.append({"page": i + 1, "text": text.strip()})
        return "\n".join(parts).strip(), pages, chunks
    finally:
        doc.close()


def _needs_ocr(digital_text: str, pages: int) -> bool:
    if pages <= 0:
        return True
    # Spec: fallback if < 100 chars per page
    return len(digital_text or "") < (100 * pages)


def _tesseract_ocr(pdf_path: str) -> tuple[str, float, int]:
    doc = fitz.open(pdf_path)
    try:
        pages = doc.page_count
        parts: list[str] = []
        confidences: list[float] = []

        for i in range(pages):
            page = doc.load_page(i)
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            data = pytesseract.image_to_data(img_bytes, lang="kan+eng", output_type=Output.DICT)

            words = []
            for txt, conf in zip(data.get("text", []), data.get("conf", [])):
                if txt and txt.strip():
                    words.append(txt.strip())
                    try:
                        c = float(conf)
                        if c >= 0:
                            confidences.append(c)
                    except Exception:
                        pass

            parts.append(" ".join(words))

        avg_word_conf = (sum(confidences) / len(confidences)) if confidences else 0.0
        # Normalize 0..100 -> 0..1
        confidence = max(0.0, min(1.0, avg_word_conf / 100.0))
        return "\n".join(parts).strip(), confidence, pages
    finally:
        doc.close()


def extract_text_from_pdf(pdf_path: str) -> dict:
    p = Path(pdf_path)
    if not p.exists():
        raise FileNotFoundError(pdf_path)

    digital_text, pages, chunks = _pymupdf_extract(pdf_path)
    if not _needs_ocr(digital_text, pages):
        return {"text": digital_text, "method": "pymupdf", "confidence": 0.95, "pages": pages, "chunks": chunks}

    try:
        ocr_text, ocr_conf, pages2 = _tesseract_ocr(pdf_path)
        # Tesseract returns flat text — split into rough page chunks
        ocr_chunks = [{"page": i + 1, "text": t.strip()} for i, t in enumerate(ocr_text.split("\f"))]
        return {"text": ocr_text, "method": "tesseract", "confidence": ocr_conf, "pages": pages2, "chunks": ocr_chunks}
    except Exception:
        return {"text": digital_text or "(no text extracted)", "method": "pymupdf_fallback", "confidence": 0.5, "pages": pages, "chunks": chunks}

