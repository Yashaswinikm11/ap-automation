import io
import os
import re
from datetime import datetime
from PIL import Image
import pytesseract


def extract_text_from_file(file_path):
    """Extract text from PDF or image file."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.pdf':
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(file_path, dpi=300)
            full_text = ''
            for img in images:
                text = pytesseract.image_to_string(img, config='--psm 6')
                full_text += text + '\n'
            return full_text
        except Exception as e:
            return f"PDF extraction error: {str(e)}"
    else:
        try:
            img = Image.open(file_path)
            text = pytesseract.image_to_string(img, config='--psm 6')
            return text
        except Exception as e:
            return f"Image extraction error: {str(e)}"


def parse_invoice_fields(text):
    """Parse structured fields from raw OCR text."""
    fields = {}

    # Invoice number patterns
    inv_patterns = [
        r'\b(?:Invoice|INV|Bill)\s*(?:No\.?|Number|#)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-/]*)',
        r'\b(?:Invoice|INV)\s*[:\-]\s*([A-Z0-9][A-Z0-9\-/]{2,19})',
        r'\b(?:Invoice|INV)\s+(?!Date\b|Total\b|Number\b|No\b)([A-Z0-9][A-Z0-9\-/]{2,19})',
    ]
    for p in inv_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            fields['invoice_number'] = m.group(1).strip()
            break

    date_value_pattern = (
        r'(\d{1,4}[./\-]\d{1,2}[./\-]\d{2,4}|'
        r'[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}|'
        r'\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})'
    )
    date_patterns = [
        rf'\b(?:Invoice|Bill)\s+Date\s*[:\-]?\s*{date_value_pattern}',
        rf'\b(?:Date|Dated)\s*[:\-]?\s*{date_value_pattern}',
    ]
    date_formats = (
        '%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d',
        '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y',
        '%d/%m/%y', '%d-%m-%y', '%d.%m.%y',
        '%B %d, %Y', '%B %d %Y', '%b %d, %Y', '%b %d %Y',
        '%d %B %Y', '%d %b %Y',
    )
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        date_text = match.group(1).strip()
        for date_format in date_formats:
            try:
                fields['invoice_date_str'] = date_text
                fields['invoice_date'] = datetime.strptime(
                    date_text, date_format
                ).date().isoformat()
                break
            except ValueError:
                continue
        if 'invoice_date' in fields:
            break

    # Total amount patterns
    total_patterns = [
        r'\b(?:Grand\s+Total|Amount\s+Due|Net\s+Amount|Total\s+Amount|Total)\b'
        r'\s*[:\-]?\s*(?:₹|Rs\.?|INR|USD|\$|EUR|€|GBP|£)?\s*'
        r'([0-9][0-9,]*(?:\.[0-9]{1,2})?)',
    ]
    for p in total_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            amount_str = m.group(1).replace(',', '')
            try:
                fields['total_amount'] = float(amount_str)
            except ValueError:
                continue
            break

    # Tax amount
    tax_patterns = [
        r'(?:GST|Tax|VAT|CGST|SGST|IGST)[:\s]*(?:Rs\.?|INR)?\s*([0-9,]+\.?[0-9]*)',
    ]
    for p in tax_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            tax_str = m.group(1).replace(',', '')
            try:
                fields['tax_amount'] = float(tax_str)
            except Exception:
                pass
            break

    # GSTIN
    gstin_match = re.search(
        r'\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})\b',
        text,
        re.IGNORECASE
    )
    if gstin_match:
        fields['gstin'] = gstin_match.group(1).upper()

    # Vendor name (first few lines usually have vendor)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if lines:
        fields['vendor_name'] = lines[0][:100]

    # PO Number
    po_match = re.search(
        r'(?:PO|Purchase\s+Order)[\s#:\-]*([A-Z0-9\-/]{3,20})',
        text,
        re.IGNORECASE
    )
    if po_match:
        fields['po_number'] = po_match.group(1).strip()

    return fields


def extract_line_items(text):
    """Attempt to extract line items from invoice text."""
    items = []
    lines = text.split('\n')

    # Look for lines with quantity and amount patterns
    item_pattern = re.compile(
        r'^(.+?)\s+(\d+(?:\.\d+)?)\s+(?:(?:Rs\.?|INR)?\s*)?([0-9,]+\.?[0-9]*)\s+(?:(?:Rs\.?|INR)?\s*)?([0-9,]+\.?[0-9]*)$'
    )

    in_items_section = False
    for line in lines:
        line = line.strip()
        if re.search(r'(?:Description|Item|Particulars|Product|Service)', line, re.IGNORECASE):
            in_items_section = True
            continue
        if re.search(r'(?:Sub\s*Total|Total|Grand Total)', line, re.IGNORECASE):
            in_items_section = False

        if in_items_section and line:
            m = item_pattern.match(line)
            if m:
                try:
                    items.append({
                        'description': m.group(1).strip(),
                        'quantity': float(m.group(2)),
                        'unit_price': float(m.group(3).replace(',', '')),
                        'total': float(m.group(4).replace(',', '')),
                    })
                except Exception:
                    pass

    return items
