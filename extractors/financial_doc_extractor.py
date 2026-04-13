"""
Financial Document Extractor
Handles zip files containing financial documents (tax returns, bank statements,
P&L statements, balance sheets, etc.).  Extracts text from each PDF inside the
zip, with OCR fallback for scanned/image-only PDFs.
"""
import io
import logging
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Union

import pdfplumber
from PIL import Image

from extractors.doc_classifier import classify_document

logger = logging.getLogger(__name__)


def _extract_text_from_pdf_bytes(pdf_bytes: bytes, filename: str) -> str:
    """Extract text from PDF bytes using pdfplumber, falling back to OCR."""
    text_parts: list[str] = []

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text_parts.append(page_text)
    except Exception as e:
        logger.warning("pdfplumber failed on %s: %s", filename, e)

    full_text = "\n".join(text_parts).strip()


    if len(full_text) < 200:
        logger.info("Sparse text in %s — attempting OCR fallback.", filename)
        full_text = _ocr_pdf_bytes(pdf_bytes, filename)

    return full_text


def _ocr_pdf_bytes(pdf_bytes: bytes, filename: str) -> str:
    """Render PDF pages as images and run pytesseract OCR on each."""
    try:
        import fitz  
        import pytesseract
    except ImportError as e:
        logger.error("OCR dependencies missing (%s). Install PyMuPDF and pytesseract.", e)
        return ""

    text_parts: list[str] = []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page_num, page in enumerate(doc):
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            ocr_text = pytesseract.image_to_string(img)
            text_parts.append(ocr_text)
            logger.debug("OCR page %d of %s: %d chars", page_num + 1, filename, len(ocr_text))
    except Exception as e:
        logger.error("OCR failed for %s: %s", filename, e)

    return "\n".join(text_parts)


class FinancialDocExtractor:
    """
    Extract and classify all financial documents from a zip archive.

    Usage:
        extractor = FinancialDocExtractor("path/to/docs.zip")
        docs = extractor.extract()
        # docs is a list of dicts:
        # {
        #   "filename": str,
        #   "doc_type": str,       # classified type
        #   "raw_text": str,       # full extracted text
        #   "char_count": int,
        #   "used_ocr": bool,
        # }
    """

    SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".txt"}

    def __init__(self, source: Union[str, Path, bytes]):
        """
        source can be:
          - a file path to a .zip file
          - raw bytes of a zip archive (e.g. from Streamlit file uploader)
        """
        if isinstance(source, (str, Path)):
            self.file_path = Path(source)
            if not self.file_path.exists():
                raise FileNotFoundError(f"Zip archive not found: {self.file_path}")
            with open(self.file_path, "rb") as f:
                self._zip_bytes = f.read()
        else:
            self.file_path = None
            self._zip_bytes = source

    def extract(self) -> list[dict[str, Any]]:
        """Return list of extracted document dicts from the zip."""
        results: list[dict[str, Any]] = []

        if not zipfile.is_zipfile(io.BytesIO(self._zip_bytes)):
            raise ValueError("Provided source is not a valid zip archive.")

        with zipfile.ZipFile(io.BytesIO(self._zip_bytes)) as zf:
            for entry in zf.infolist():
                if entry.is_dir():
                    continue
                ext = Path(entry.filename).suffix.lower()
                if ext not in self.SUPPORTED_EXTENSIONS:
                    logger.debug("Skipping unsupported file: %s", entry.filename)
                    continue

                file_bytes = zf.read(entry.filename)
                doc_result = self._process_file(entry.filename, ext, file_bytes)
                results.append(doc_result)

        logger.info(
            "Extracted %d document(s) from zip%s",
            len(results),
            f" ({self.file_path.name})" if self.file_path else "",
        )
        return results

    # ── private ────────────────────────────────────────────────────────────

    def _process_file(self, filename: str, ext: str, file_bytes: bytes) -> dict[str, Any]:
        if ext == ".pdf":
            raw_text = _extract_text_from_pdf_bytes(file_bytes, filename)
        elif ext == ".txt":
            raw_text = file_bytes.decode("utf-8", errors="replace")
        else:
            # Direct image — run OCR immediately
            raw_text = self._ocr_image_bytes(file_bytes, filename)

        pre_ocr_len = len(raw_text)
        used_ocr = ext != ".pdf" or pre_ocr_len < 200

        doc_type = classify_document(raw_text, filename)

        return {
            "filename":   filename,
            "doc_type":   doc_type,
            "raw_text":   raw_text,
            "char_count": len(raw_text),
            "used_ocr":   used_ocr,
        }

    def _ocr_image_bytes(self, image_bytes: bytes, filename: str) -> str:
        try:
            import pytesseract
            img = Image.open(io.BytesIO(image_bytes))
            return pytesseract.image_to_string(img)
        except Exception as e:
            logger.error("Image OCR failed for %s: %s", filename, e)
            return ""
