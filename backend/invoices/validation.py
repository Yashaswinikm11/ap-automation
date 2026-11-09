import re
from .models import Invoice

GSTIN_REGEX = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'


def run_validation_pipeline(invoice):
    """
    Run validation pipeline for an invoice.
    Returns:
        dict: {
            'passed': bool,
            'errors': list of str,
            'warnings': list of str
        }
    """
    errors = []
    warnings = []

    # 1. Mandatory fields: invoice_number, vendor, invoice_date, total_amount
    if not invoice.invoice_number or not str(invoice.invoice_number).strip():
        errors.append("Mandatory field missing: invoice_number.")

    if not invoice.vendor:
        errors.append("Mandatory field missing: vendor.")

    if not invoice.invoice_date:
        errors.append("Mandatory field missing: invoice_date.")

    if invoice.total_amount is None:
        errors.append("Mandatory field missing: total_amount.")

    # 2. Duplicate check: check if another invoice with same invoice_number and vendor exists
    is_dup = False
    dup_of = None
    if invoice.invoice_number and invoice.vendor:
        duplicate_qs = Invoice.objects.filter(
            invoice_number__iexact=str(invoice.invoice_number).strip(),
            vendor=invoice.vendor
        ).exclude(pk=invoice.pk)

        if duplicate_qs.exists():
            dup_of = duplicate_qs.first()
            is_dup = True
            errors.append(
                f"Duplicate invoice detected: matches existing invoice #{dup_of.id} "
                f"with invoice number '{dup_of.invoice_number}' for vendor '{invoice.vendor.name}'."
            )

    # 3. Amount check: total_amount > 0
    if invoice.total_amount is not None:
        try:
            if invoice.total_amount <= 0:
                errors.append(f"Total amount must be greater than zero. Found: {invoice.total_amount}.")
        except (TypeError, ValueError):
            errors.append("Total amount has an invalid numerical value.")

    if invoice.tax_amount is not None:
        if invoice.tax_amount < 0:
            errors.append("Tax amount cannot be negative.")
        elif invoice.total_amount is not None and invoice.tax_amount > invoice.total_amount:
            errors.append("Tax amount cannot exceed the invoice total.")

    # 4. GSTIN format validation (regex check)
    gstin_val = invoice.gstin or (invoice.vendor.gstin if invoice.vendor else None)
    if gstin_val:
        gstin_clean = gstin_val.strip().upper()
        if not re.match(GSTIN_REGEX, gstin_clean):
            errors.append(f"Invalid GSTIN format: '{gstin_val}'.")
        else:
            try:
                state_code = int(gstin_clean[:2])
                if state_code < 1 or state_code > 37:
                    errors.append(
                        f"GSTIN state code {state_code} in '{gstin_clean}' is outside the standard 01-37 range."
                    )
            except ValueError:
                errors.append(f"GSTIN state code must be numeric in '{gstin_val}'.")
    else:
        warnings.append("GSTIN is not provided on invoice or vendor record.")

    # 5. Vendor is active check
    if invoice.vendor:
        if not invoice.vendor.is_active:
            errors.append(f"Vendor '{invoice.vendor.name}' is currently inactive.")
        if invoice.vendor.onboarding_status != 'approved':
            warnings.append(
                f"Vendor '{invoice.vendor.name}' onboarding status is '{invoice.vendor.onboarding_status}' (not approved)."
            )

    # 6. Due date is after or on invoice date
    if invoice.invoice_date and invoice.due_date:
        if invoice.due_date < invoice.invoice_date:
            errors.append(
                f"Due date ({invoice.due_date}) cannot be earlier than invoice date ({invoice.invoice_date})."
            )

    passed = len(errors) == 0

    # Determine status transition
    new_status = invoice.status
    if passed and invoice.status in ['uploaded', 'extracted']:
        new_status = 'validated'

    # Update database record safely
    Invoice.objects.filter(pk=invoice.pk).update(
        validation_errors=errors,
        status=new_status,
        is_duplicate=is_dup,
        duplicate_of=dup_of
    )

    # Refresh in-memory instance attributes
    invoice.validation_errors = errors
    invoice.status = new_status
    invoice.is_duplicate = is_dup
    invoice.duplicate_of = dup_of

    return {
        'passed': passed,
        'errors': errors,
        'warnings': warnings
    }
