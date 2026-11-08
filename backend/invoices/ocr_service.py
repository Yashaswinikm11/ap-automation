import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import os
import re

# Set the exact path to tesseract.exe
pytesseract.pytesseract.tesseract_cmd = r'D:\Program Files\tesseract.exe'

# Set the exact path to your tessdata folder
os.environ['TESSDATA_PREFIX'] = r'D:\Program Files\tessdata'

def extract_text_from_file(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        pages = convert_from_path(file_path, dpi=300)
        full_text = []
        for i, page in enumerate(pages):
            text = pytesseract.image_to_string(page)
            full_text.append(f"--- Page {i+1} ---\n{text}")
        return "\n".join(full_text)
    else:
        image = Image.open(file_path)
        return pytesseract.image_to_string(image)

def parse_invoice_fields(raw_text: str) -> dict:
    """
    Extracts invoice number, total amount, and GSTIN from raw OCR text.
    """
    data = {}
    
    # 1. Invoice Number
    inv_patterns = [
        r'(?:Invoice|Inv|Bill)\s*(?:No|Number|#)[:\s]*([A-Z0-9\-/]+)', 
        r'INV[-\s]?([0-9]+)'
    ]
    for pattern in inv_patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            data['invoice_number'] = match.group(1).strip()
            break

    # 2. Total Amount
    total_patterns = [
        r'(?:Total|Grand Total|Amount Due)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+\.?\d*)', 
        r'([\d,]+\.\d{2})\s*(?:Total|Only)'
    ]
    for pattern in total_patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(',', '')
            try:
                data['total_amount'] = float(amount_str)
            except ValueError:
                pass
            break

    # 3. GSTIN
    gst_match = re.search(r'\b(\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1})\b', raw_text)
    if gst_match:
        data['vendor_gstin'] = gst_match.group(1)

    return data