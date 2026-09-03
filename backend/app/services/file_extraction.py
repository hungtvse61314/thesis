import logging
from io import BytesIO

logger = logging.getLogger("raematch.cv_upload")

def extract_pdf(data:bytes)->tuple[str,str]:
    try:
        from pypdf import PdfReader
        reader=PdfReader(BytesIO(data))
        logger.info("  -> Trying direct text extraction (%d page(s))...", len(reader.pages))
        text='\n'.join((p.extract_text() or '') for p in reader.pages).strip()
        if len(text)>=100:
            logger.info("  -> Direct text extraction succeeded (%d chars)", len(text))
            return text,'pdf_text_extracted'
        logger.info("  -> Direct text extraction too short (%d chars), falling back to OCR", len(text))
    except Exception as e:
        logger.warning("  -> Direct text extraction failed: %s", e)
        text=''
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
        logger.info("  -> Running OCR (pdf2image + pytesseract)...")
        pages=convert_from_bytes(data, dpi=250)
        logger.info("  -> Converted to %d image(s), running Tesseract OCR...", len(pages))
        ocr='\n'.join(pytesseract.image_to_string(p, lang='eng') for p in pages).strip()
        if ocr:
            logger.info("  -> OCR succeeded (%d chars)", len(ocr))
            return ocr,'pdf_ocr_extracted'
        logger.warning("  -> OCR produced no text")
        return '','ocr_empty'
    except Exception as e:
        logger.warning("  -> OCR unavailable or failed: %s", e)
        return text, 'ocr_unavailable_or_failed'
