"""
resume_client.py — Parse PDF or DOCX resume into plain text.
Supports: PDF (PyMuPDF or pdfplumber), DOCX (python-docx), plain TXT.
"""
from __future__ import annotations
import os, logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def parse_resume(filepath: str) -> str:
    """
    Parse a resume file and return clean plain text.
    Supports .pdf, .docx, .doc, .txt
    """
    path = Path(filepath)
    if not path.exists():
        return ""
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return _parse_pdf(filepath)
    elif suffix in (".docx", ".doc"):
        return _parse_docx(filepath)
    elif suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    else:
        logger.warning("Unsupported resume format: %s", suffix)
        return ""


def _parse_pdf(filepath: str) -> str:
    # Try PyMuPDF first (faster, better layout)
    try:
        import fitz
        doc = fitz.open(filepath)
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return _clean(text)
    except ImportError:
        pass

    # Fallback: pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(filepath) as pdf:
            text = "\n".join(
                page.extract_text() or "" for page in pdf.pages
            )
        return _clean(text)
    except ImportError:
        pass

    # Last fallback: pypdf
    try:
        from pypdf import PdfReader
        reader = PdfReader(filepath)
        text = "\n".join(
            page.extract_text() or "" for page in reader.pages
        )
        return _clean(text)
    except ImportError:
        logger.error("No PDF library found. pip install pymupdf OR pdfplumber OR pypdf")
        return "[PDF parsing unavailable — install pymupdf: pip install pymupdf]"


def _parse_docx(filepath: str) -> str:
    try:
        from docx import Document
        doc = Document(filepath)
        text = "\n".join(p.text for p in doc.paragraphs)
        return _clean(text)
    except ImportError:
        logger.error("python-docx not installed. pip install python-docx")
        return "[DOCX parsing unavailable — pip install python-docx]"


def _clean(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    lines = [l for l in lines if l]
    return "\n".join(lines)


def summarise_for_prompt(text: str, max_chars: int = 3000) -> str:
    """Trim resume text to fit in the prompt context window."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n[... resume truncated for context ...]"
