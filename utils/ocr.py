"""OCR helpers for extracting readable text from uploaded images."""

from PIL import Image

try:
    import pytesseract
except ImportError:
    pytesseract = None


def extract_text_from_pil(image: Image.Image) -> str:
    """Return any text found inside a PIL image using Tesseract OCR.

    Returns an empty string if pytesseract or the Tesseract binary is not
    available, or if no text is detected, rather than raising.
    """
    if pytesseract is None:
        return ""

    try:
        text = pytesseract.image_to_string(image)
    except Exception:
        # Covers the common "tesseract is not installed / not in PATH" error
        # so the rest of the app keeps working without OCR.
        return ""

    return text.strip()
