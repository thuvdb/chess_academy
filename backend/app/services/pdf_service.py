"""
PDF Service — Sprint 3A
Handles PDF upload, page rendering (300 DPI via PyMuPDF), and storage.

Storage strategy:
  - Dev/fallback: local filesystem at SCAN_STORAGE_PATH
  - Production: MinIO (when MINIO_ENABLED=true)
"""

import os
import io
import uuid
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Local storage path (dev fallback)
SCAN_STORAGE_PATH = Path(os.getenv("SCAN_STORAGE_PATH", "/tmp/cams_scans"))
SCAN_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

# Public base URL for serving stored files
STORAGE_BASE_URL = os.getenv("STORAGE_BASE_URL", "http://localhost:8000/scans")


def _save_local(data: bytes, relative_path: str) -> str:
    """Save bytes to local storage and return public URL."""
    full_path = SCAN_STORAGE_PATH / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(data)
    return f"{STORAGE_BASE_URL}/{relative_path}"


async def save_pdf(file_bytes: bytes, filename: str, job_id: str) -> tuple[str, int]:
    """
    Save uploaded PDF to storage.

    Returns:
        (file_url, file_size_bytes)
    """
    relative = f"{job_id}/source/{filename}"
    url = _save_local(file_bytes, relative)
    logger.info("Saved PDF: %s (%d bytes)", relative, len(file_bytes))
    return url, len(file_bytes)


async def render_pdf_pages(
    file_bytes: bytes,
    job_id: str,
    dpi: int = 300,
) -> list[dict]:
    """
    Render each PDF page to PNG at given DPI using PyMuPDF (fitz).

    Returns:
        list of {page_number (1-based), image_url, width, height}
    """
    try:
        import pymupdf as fitz  # PyMuPDF >= 1.25
    except ImportError:
        try:
            import fitz  # PyMuPDF legacy import
        except ImportError:
            raise RuntimeError(
                "PyMuPDF is required for PDF rendering. "
                "Install it with: pip install pymupdf"
            )

    start = time.monotonic()
    pages = []

    # Open PDF from bytes
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    total_pages = len(doc)
    logger.info("Rendering PDF: %d pages @ %d DPI", total_pages, dpi)

    zoom = dpi / 72.0  # PDF default = 72 DPI
    mat = fitz.Matrix(zoom, zoom)

    for page_num in range(total_pages):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB, alpha=False)

        png_bytes = pix.tobytes("png")
        relative = f"{job_id}/pages/page_{page_num + 1:03d}.png"
        url = _save_local(png_bytes, relative)

        pages.append({
            "page_number": page_num + 1,
            "image_url": url,
            "width": pix.width,
            "height": pix.height,
        })
        logger.debug("  Page %d → %dx%d", page_num + 1, pix.width, pix.height)

    doc.close()
    elapsed_ms = int((time.monotonic() - start) * 1000)
    logger.info("PDF rendered: %d pages in %d ms", total_pages, elapsed_ms)

    return pages


def get_local_file_bytes(file_url: str) -> bytes:
    """
    Retrieve file bytes from local storage using URL.
    Strips the base URL prefix to get the relative path.
    """
    relative = file_url.replace(STORAGE_BASE_URL + "/", "")
    full_path = SCAN_STORAGE_PATH / relative
    if not full_path.exists():
        raise FileNotFoundError(f"File not found: {full_path}")
    return full_path.read_bytes()
