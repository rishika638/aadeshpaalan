from __future__ import annotations

from pathlib import Path

import fitz

from app.services.ocr_service import extract_text_from_pdf


def _make_pdf_with_text(tmp_path: Path, text: str) -> Path:
    pdf_path = tmp_path / "digital.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(pdf_path.as_posix())
    doc.close()
    return pdf_path


def test_extract_text_from_pdf_uses_pymupdf_for_digital(tmp_path: Path) -> None:
    pdf = _make_pdf_with_text(tmp_path, "This is a digital judgment text " * 10)
    res = extract_text_from_pdf(str(pdf))
    assert res["method"] == "pymupdf"
    assert res["confidence"] == 0.95
    assert res["pages"] == 1
    assert "digital judgment" in res["text"].lower()

