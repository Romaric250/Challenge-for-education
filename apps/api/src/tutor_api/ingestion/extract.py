# mypy: disable-error-code="no-untyped-call,var-annotated,arg-type"
import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf

_CHAPTER = re.compile(r"^(chapter\s+\d+\b[^\n]*)$", re.IGNORECASE | re.MULTILINE)
_EQUATION = re.compile(r"[=≈∑√∫]|(?:\d+\s*[+\-*/]\s*\d+)")


@dataclass(frozen=True)
class ExtractedPage:
    number: int
    kind: str
    text: str
    ocr_confidence: float | None


@dataclass(frozen=True)
class ChapterSpan:
    title: str
    page_start: int
    page_end: int


def extract_pdf(path: Path, *, ocr_threshold: float) -> tuple[list[ExtractedPage], list[str]]:
    warnings: list[str] = []
    tables = _tables_by_page(path, warnings)
    document = pymupdf.open(path)
    pages: list[ExtractedPage] = []
    try:
        for index, page in enumerate(document, start=1):
            text = page.get_text("text").strip()
            image_count = len(page.get_images())
            table_text = tables.get(index, "")
            kind = _kind(text, image_count, bool(table_text))
            confidence: float | None = None
            if len(text) < 40 and image_count:
                ocr_text, confidence = _ocr_page(page, warnings, index)
                if ocr_text:
                    text = ocr_text
                    if confidence is not None and confidence < ocr_threshold:
                        warnings.append(f"Page {index} OCR confidence is {confidence:.2f}.")
            if table_text:
                text = f"{text}\n{table_text}".strip()
                if kind == "text":
                    kind = "table"
            pages.append(
                ExtractedPage(number=index, kind=kind, text=text, ocr_confidence=confidence)
            )
    finally:
        document.close()
    return pages, warnings


def chapter_spans(pages: list[ExtractedPage]) -> list[ChapterSpan]:
    if not pages:
        return []
    found: list[tuple[str, int]] = []
    for page in pages:
        match = _CHAPTER.search(page.text)
        if match is not None:
            found.append((match.group(1).strip(), page.number))
    if not found:
        return [ChapterSpan("Document", pages[0].number, pages[-1].number)]
    spans: list[ChapterSpan] = []
    for index, (title, start) in enumerate(found):
        next_page = found[index + 1][1] if index + 1 < len(found) else pages[-1].number + 1
        spans.append(ChapterSpan(title, start, max(next_page - 1, start)))
    return spans


def _kind(text: str, image_count: int, has_table: bool) -> str:
    if has_table:
        return "table"
    if len(text) < 20 and image_count == 0:
        return "blank"
    if len(text) < 40 and image_count:
        return "image"
    if _EQUATION.search(text) and len(text) < 400:
        return "equation"
    if image_count and len(text) >= 40:
        return "mixed"
    return "text"


def _tables_by_page(path: Path, warnings: list[str]) -> dict[int, str]:
    try:
        import pdfplumber
    except ImportError:
        warnings.append("pdfplumber is not installed, so tables were not extracted.")
        return {}
    found: dict[int, str] = {}
    with pdfplumber.open(path) as document:
        for index, page in enumerate(document.pages, start=1):
            rows = page.extract_tables() or []
            rendered = [_render_table(table) for table in rows if table]
            if rendered:
                found[index] = "\n".join(rendered)
    return found


def _render_table(table: list[list[str | None]]) -> str:
    lines: list[str] = []
    for row in table:
        cells = ["" if cell is None else str(cell).strip() for cell in row]
        lines.append(" | ".join(cells))
    return "\n".join(lines)


def _ocr_page(page: pymupdf.Page, warnings: list[str], number: int) -> tuple[str, float | None]:
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        warnings.append(f"Page {number} needs OCR, and the OCR libraries are not installed.")
        return "", None
    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))
    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    try:
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    except pytesseract.TesseractNotFoundError:
        warnings.append("Tesseract is not installed, so image pages were not read.")
        return "", None
    words: list[str] = []
    confidences: list[float] = []
    texts = data.get("text", [])
    scores = data.get("conf", [])
    if isinstance(texts, list) and isinstance(scores, list):
        for word, score in zip(texts, scores, strict=False):
            if not isinstance(word, str) or not word.strip():
                continue
            words.append(word.strip())
            try:
                value = float(score)
            except (TypeError, ValueError):
                continue
            if value >= 0:
                confidences.append(value / 100)
    confidence = sum(confidences) / len(confidences) if confidences else None
    return " ".join(words), confidence
