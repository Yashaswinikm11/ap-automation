import logging
import os
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from core.models import TimeStampedModel
from vendors.models import Vendor

logger = logging.getLogger(__name__)


class PurchaseOrder(TimeStampedModel):
    po_number = models.CharField(max_length=100, unique=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='purchase_orders')
    po_date = models.DateField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    ordered_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='INR')
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='open')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.po_number


class PurchaseOrderLineItem(TimeStampedModel):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='line_items')
    item_description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.purchase_order.po_number} - {self.item_description}"


class GoodsReceiptNote(TimeStampedModel):
    grn_number = models.CharField(max_length=100, unique=True)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='grns')
    received_date = models.DateField()
    grn_date = models.DateField(null=True, blank=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_grns'
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ['-received_date']

    def __str__(self):
        return self.grn_number


class GRNLineItem(TimeStampedModel):
    grn = models.ForeignKey(GoodsReceiptNote, on_delete=models.CASCADE, related_name='line_items')
    item_description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    received_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.grn.grn_number} - {self.item_description}"


class Invoice(TimeStampedModel):
    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('extracted', 'OCR Extracted'),
        ('validated', 'Validated'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
    ]

    invoice_number = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    invoice_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='INR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    original_file = models.FileField(upload_to='invoices/%Y/%m/')
    ocr_raw_text = models.TextField(blank=True)
    ocr_confidence = models.FloatField(null=True, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_invoices'
    )
    validation_errors = models.JSONField(default=list, blank=True)

    gstin = models.CharField(max_length=15, blank=True)
    vendor_name = models.CharField(max_length=255, blank=True)
    vendor_address = models.TextField(blank=True)
    payment_terms = models.IntegerField(default=30, help_text='Payment terms in days')
    notes = models.TextField(blank=True)
    is_duplicate = models.BooleanField(default=False)
    duplicate_of = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='duplicates'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.invoice_number or 'Draft'} - {self.vendor or self.vendor_name or 'Unknown Vendor'}"


class EmailIngestion(TimeStampedModel):
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('processed', 'Processed'),
        ('ignored', 'Ignored'),
        ('failed', 'Failed'),
    ]

    mailbox = models.EmailField()
    message_id = models.CharField(max_length=255)
    subject = models.CharField(max_length=998, blank=True)
    sender = models.CharField(max_length=255, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')
    error_message = models.TextField(blank=True)
    invoices = models.ManyToManyField(Invoice, blank=True, related_name='email_ingestions')

    class Meta:
        unique_together = ('mailbox', 'message_id')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.mailbox}: {self.subject or self.message_id} ({self.status})'


class InvoiceLineItem(TimeStampedModel):
    invoice = models.ForeignKey(Invoice, related_name='line_items', on_delete=models.CASCADE)
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    hsn_code = models.CharField(max_length=20, blank=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.invoice.invoice_number or 'Invoice'} - {self.description}"


class MatchResult(TimeStampedModel):
    MATCH_TYPES = [('2way', '2-Way'), ('3way', '3-Way')]
    MATCH_STATUS = [('matched', 'Matched'), ('exception', 'Exception'), ('unmatched', 'Unmatched')]

    invoice = models.OneToOneField(Invoice, on_delete=models.CASCADE, related_name='match_result')
    match_type = models.CharField(max_length=10, choices=MATCH_TYPES, default='2way')
    status = models.CharField(max_length=15, choices=MATCH_STATUS, default='unmatched')
    tolerance_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=2.0)
    po_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    invoice_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    grn_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    differences = models.JSONField(default=dict, blank=True)
    matched_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='matches_performed'
    )
    matched_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.match_type.upper()} Match for {self.invoice}: {self.status}"


# ==========================================================
# OCR AUTO-TRIGGER SIGNAL
# ==========================================================
def _find_vendor_by_gstin(gstin):
    if not gstin:
        return None

    vendors = Vendor.objects.filter(gstin__iexact=gstin.strip()).exclude(gstin='')
    if vendors.count() == 1:
        return vendors.first()
    return None


@receiver(post_save, sender=Invoice)
def trigger_ocr_on_upload(sender, instance, created, **kwargs):
    if created and instance.original_file and not instance.ocr_raw_text:
        from .ocr_service import extract_text_from_file, parse_invoice_fields

        try:
            if hasattr(instance.original_file, 'path') and os.path.exists(instance.original_file.path):
                raw_text = extract_text_from_file(instance.original_file.path)
                fields = parse_invoice_fields(raw_text)

                update_fields = {
                    'ocr_raw_text': raw_text,
                    'status': 'extracted',
                }
                if 'invoice_number' in fields and not instance.invoice_number:
                    update_fields['invoice_number'] = fields['invoice_number']
                if 'invoice_date' in fields and not instance.invoice_date:
                    update_fields['invoice_date'] = fields['invoice_date']
                if 'total_amount' in fields and instance.total_amount is None:
                    update_fields['total_amount'] = fields['total_amount']
                if 'tax_amount' in fields and instance.tax_amount is None:
                    update_fields['tax_amount'] = fields['tax_amount']
                if 'gstin' in fields and not instance.gstin:
                    update_fields['gstin'] = fields['gstin']
                if 'gstin' in fields and not instance.vendor_id:
                    vendor = _find_vendor_by_gstin(fields['gstin'])
                    if vendor:
                        update_fields['vendor'] = vendor
                if 'vendor_name' in fields and not instance.vendor_name:
                    update_fields['vendor_name'] = fields['vendor_name']

                # Use update() instead of save() to avoid recursive post_save signal
                Invoice.objects.filter(pk=instance.pk).update(**update_fields)
                logger.info('OCR processing succeeded for invoice #%s.', instance.pk)
        except Exception:
            logger.exception('OCR processing failed for invoice #%s.', instance.pk)
