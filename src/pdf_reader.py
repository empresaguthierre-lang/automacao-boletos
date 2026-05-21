from __future__ import annotations

from pathlib import Path


def read_pdf_text(pdf_path: Path) -> str:
    """Read all text from a PDF using PyMuPDF."""
    try:
        import fitz
    except ImportError as error:
        raise RuntimeError(
            "Dependencia PyMuPDF nao instalada. Rode: pip install -r requirements.txt"
        ) from error

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF nao encontrado: {pdf_path}")

    text_parts: list[str] = []

    with fitz.open(pdf_path) as document:
        if document.page_count == 0:
            raise ValueError("PDF sem paginas.")

        for page in document:
            page_text = page.get_text("text")
            if page_text:
                text_parts.append(page_text)

    extracted_text = "\n".join(text_parts).strip()
    if not extracted_text:
        raise ValueError("Nao foi possivel extrair texto do PDF.")

    return extracted_text
