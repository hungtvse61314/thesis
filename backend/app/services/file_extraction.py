from io import BytesIO

def extract_pdf(data:bytes)->tuple[str,str]:
    try:
        from pypdf import PdfReader
        reader=PdfReader(BytesIO(data))
        text='\n'.join((p.extract_text() or '') for p in reader.pages).strip()
        if len(text)>=100: return text,'pdf_text_extracted'
    except Exception:
        text=''
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
        pages=convert_from_bytes(data, dpi=250)
        ocr='\n'.join(pytesseract.image_to_string(p, lang='eng') for p in pages).strip()
        return (ocr,'pdf_ocr_extracted') if ocr else ('','ocr_empty')
    except Exception as e:
        return text, 'ocr_unavailable_or_failed'
