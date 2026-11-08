from decimal import Decimal
from .models import Invoice

def run_validation_pipeline(invoice: Invoice) -> dict:
    errors = []

    if not invoice.invoice_number:
        errors.append("Invoice number is missing.")
    if not invoice.total_amount:
        errors.append("Total amount is missing.")
    if not invoice.vendor:
        errors.append("Vendor is not identified.")

    # Duplicate check
    if invoice.invoice_number and invoice.vendor:
        duplicate = Invoice.objects.filter(
            invoice_number=invoice.invoice_number,
            vendor=invoice.vendor
        ).exclude(pk=invoice.pk).exists()
        if duplicate:
            errors.append(f"Duplicate invoice: {invoice.invoice_number} already exists for this vendor.")

    # Amount check (line items vs total)
    if invoice.line_items.exists() and invoice.total_amount:
        line_total = sum(item.total or Decimal('0') for item in invoice.line_items.all())
        if abs(line_total - invoice.total_amount) > Decimal('0.01'):
            errors.append(f"Line item total ({line_total}) does not match invoice total ({invoice.total_amount}).")

    if errors:
        invoice.status = 'uploaded'
        invoice.validation_errors = errors
    else:
        invoice.status = 'validated'
        invoice.validation_errors = []
    
    invoice.save()
    return {'valid': len(errors) == 0, 'errors': errors}