import os
import logging
from PIL import Image
import pytesseract
import pypdf

logger = logging.getLogger('apps.ai')

# Explicitly configure local Windows Tesseract executable path
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
else:
    logger.warning(f"Tesseract executable not found at specified path: {TESSERACT_PATH}. Relying on system environment PATH.")

def extract_text_from_file(file_obj, filename: str) -> str:
    """
    Extracts text from an uploaded file object.
    Supports PDF (via pypdf digital extraction) and Images (via pytesseract OCR).
    """
    ext = os.path.splitext(filename)[1].lower()
    text = ""

    try:
        if ext == '.pdf':
            logger.info(f"Extracting digital text from PDF: {filename}")
            reader = pypdf.PdfReader(file_obj)
            pages_text = []
            for i, page in enumerate(reader.pages):
                page_content = page.extract_text()
                if page_content:
                    pages_text.append(page_content)
            
            text = "\n".join(pages_text).strip()
            
            if not text:
                logger.warning("Digital PDF text extraction returned empty. This might be a scanned PDF image.")
                text = "[WARNING: Scanned PDF detected. Digital text extraction was empty. Please upload image or digital PDF format.]"
        
        elif ext in ['.png', '.jpg', '.jpeg', '.webp']:
            logger.info(f"Extracting OCR text from image: {filename}")
            img = Image.open(file_obj)
            text = pytesseract.image_to_string(img)
        else:
            raise ValueError(f"Unsupported file extension: {ext}")

        logger.debug(f"Successfully extracted {len(text)} characters of raw text.")
        return text.strip()

    except Exception as e:
        logger.error(f"Error extracting text from file {filename}: {e}", exc_info=True)
        raise e
