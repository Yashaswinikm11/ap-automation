from decimal import Decimal
from django.utils import timezone
from .models import Invoice, MatchResult, GoodsReceiptNote


def run_two_way_match(invoice, user=None):
    """
    Perform 2-way match: Compare Invoice vs Purchase Order (amounts, vendor).
    Tolerance of 2% for amount differences.
    """
    po = invoice.purchase_order
    po_amount = po.total_amount if po else None
    invoice_amount = invoice.total_amount
    tolerance_pct = Decimal('2.0')

    if not po:
        match_result, _ = MatchResult.objects.update_or_create(
            invoice=invoice,
            defaults={
                'match_type': '2way',
                'status': 'unmatched',
                'tolerance_percentage': tolerance_pct,
                'po_amount': None,
                'invoice_amount': invoice_amount,
                'grn_amount': None,
                'differences': {
                    'error': 'No Purchase Order linked to this invoice.',
                    'vendor_matched': False,
                    'amount_matched': False,
                },
                'matched_by': user if user and user.is_authenticated else None,
                'matched_at': timezone.now(),
            }
        )
        return match_result

    diff_list = []

    # 1. Vendor Match Check
    vendor_matched = False
    if invoice.vendor_id and po.vendor_id:
        vendor_matched = (invoice.vendor_id == po.vendor_id)
        if not vendor_matched:
            diff_list.append(
                f"Vendor mismatch: Invoice vendor #{invoice.vendor_id} ({invoice.vendor}) "
                f"does not match PO vendor #{po.vendor_id} ({po.vendor})."
            )
    else:
        diff_list.append("Vendor missing on invoice or purchase order.")

    # 2. Amount Match Check with 2% tolerance
    amount_matched = False
    pct_diff = Decimal('0.0')
    diff_val = Decimal('0.0')

    if invoice_amount is not None and po_amount is not None:
        diff_val = abs(Decimal(str(invoice_amount)) - Decimal(str(po_amount)))
        dec_po = Decimal(str(po_amount))
        if dec_po > Decimal('0'):
            pct_diff = (diff_val / dec_po) * Decimal('100.0')
        else:
            pct_diff = Decimal('100.0') if diff_val > 0 else Decimal('0.0')

        if pct_diff <= tolerance_pct:
            amount_matched = True
        else:
            diff_list.append(
                f"Amount mismatch: Invoice ({invoice_amount}) vs PO ({po_amount}), "
                f"difference {diff_val} ({pct_diff:.2f}%) exceeds tolerance of {tolerance_pct}%."
            )
    else:
        diff_list.append("Total amount missing on invoice or purchase order.")

    status = 'matched' if (vendor_matched and amount_matched) else 'exception'

    differences = {
        'vendor_matched': vendor_matched,
        'amount_matched': amount_matched,
        'difference_amount': float(diff_val),
        'percentage_difference': round(float(pct_diff), 2),
        'issues': diff_list,
    }

    match_result, _ = MatchResult.objects.update_or_create(
        invoice=invoice,
        defaults={
            'match_type': '2way',
            'status': status,
            'tolerance_percentage': tolerance_pct,
            'po_amount': po_amount,
            'invoice_amount': invoice_amount,
            'grn_amount': None,
            'differences': differences,
            'matched_by': user if user and user.is_authenticated else None,
            'matched_at': timezone.now(),
        }
    )
    return match_result


def run_three_way_match(invoice, user=None):
    """
    Perform 3-way match: Compare Invoice vs Purchase Order vs Goods Receipt Note (GRN).
    Tolerance of 2% for amount differences.
    """
    po = invoice.purchase_order
    po_amount = po.total_amount if po else None
    invoice_amount = invoice.total_amount
    tolerance_pct = Decimal('2.0')
    diff_list = []

    if not po:
        match_result, _ = MatchResult.objects.update_or_create(
            invoice=invoice,
            defaults={
                'match_type': '3way',
                'status': 'unmatched',
                'tolerance_percentage': tolerance_pct,
                'po_amount': None,
                'invoice_amount': invoice_amount,
                'grn_amount': None,
                'differences': {
                    'error': 'No Purchase Order linked to this invoice.',
                    'vendor_matched': False,
                    'po_amount_matched': False,
                    'grn_amount_matched': False,
                },
                'matched_by': user if user and user.is_authenticated else None,
                'matched_at': timezone.now(),
            }
        )
        return match_result

    # 1. Vendor Match Check
    vendor_matched = False
    if invoice.vendor_id and po.vendor_id:
        vendor_matched = (invoice.vendor_id == po.vendor_id)
        if not vendor_matched:
            diff_list.append(
                f"Vendor mismatch: Invoice vendor #{invoice.vendor_id} ({invoice.vendor}) "
                f"does not match PO vendor #{po.vendor_id} ({po.vendor})."
            )
    else:
        diff_list.append("Vendor missing on invoice or purchase order.")

    # 2. PO Amount Match Check
    po_amount_matched = False
    po_diff_val = Decimal('0.0')
    po_pct_diff = Decimal('0.0')
    if invoice_amount is not None and po_amount is not None:
        po_diff_val = abs(Decimal(str(invoice_amount)) - Decimal(str(po_amount)))
        dec_po = Decimal(str(po_amount))
        if dec_po > Decimal('0'):
            po_pct_diff = (po_diff_val / dec_po) * Decimal('100.0')
        else:
            po_pct_diff = Decimal('100.0') if po_diff_val > 0 else Decimal('0.0')

        if po_pct_diff <= tolerance_pct:
            po_amount_matched = True
        else:
            diff_list.append(
                f"PO amount mismatch: Invoice ({invoice_amount}) vs PO ({po_amount}), "
                f"difference {po_diff_val} ({po_pct_diff:.2f}%) exceeds tolerance of {tolerance_pct}%."
            )
    else:
        diff_list.append("Total amount missing on invoice or purchase order.")

    # 3. GRN Match Check
    grns = GoodsReceiptNote.objects.filter(purchase_order=po)
    grn_amount = None
    grn_amount_matched = False
    grn_diff_val = Decimal('0.0')
    grn_pct_diff = Decimal('0.0')

    if not grns.exists():
        diff_list.append(f"No Goods Receipt Note found for PO #{po.po_number}.")
    else:
        grn_amount = sum(Decimal(str(g.total_amount)) for g in grns)
        if invoice_amount is not None and grn_amount is not None:
            grn_diff_val = abs(Decimal(str(invoice_amount)) - grn_amount)
            if grn_amount > Decimal('0'):
                grn_pct_diff = (grn_diff_val / grn_amount) * Decimal('100.0')
            else:
                grn_pct_diff = Decimal('100.0') if grn_diff_val > 0 else Decimal('0.0')

            if grn_pct_diff <= tolerance_pct:
                grn_amount_matched = True
            else:
                diff_list.append(
                    f"GRN amount mismatch: Invoice ({invoice_amount}) vs GRN total ({grn_amount}), "
                    f"difference {grn_diff_val} ({grn_pct_diff:.2f}%) exceeds tolerance of {tolerance_pct}%."
                )
        else:
            diff_list.append("Invoice amount or GRN total is missing.")

    status = 'matched' if (vendor_matched and po_amount_matched and grn_amount_matched) else 'exception'

    differences = {
        'vendor_matched': vendor_matched,
        'po_amount_matched': po_amount_matched,
        'grn_amount_matched': grn_amount_matched,
        'po_difference_amount': float(po_diff_val),
        'po_percentage_difference': round(float(po_pct_diff), 2),
        'grn_total_amount': float(grn_amount) if grn_amount is not None else None,
        'grn_difference_amount': float(grn_diff_val),
        'grn_percentage_difference': round(float(grn_pct_diff), 2),
        'issues': diff_list,
    }

    match_result, _ = MatchResult.objects.update_or_create(
        invoice=invoice,
        defaults={
            'match_type': '3way',
            'status': status,
            'tolerance_percentage': tolerance_pct,
            'po_amount': po_amount,
            'invoice_amount': invoice_amount,
            'grn_amount': grn_amount,
            'differences': differences,
            'matched_by': user if user and user.is_authenticated else None,
            'matched_at': timezone.now(),
        }
    )
    return match_result
