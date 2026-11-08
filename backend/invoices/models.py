from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import TimeStampedModel
from vendors.models import Vendor


class PurchaseOrder(TimeStampedModel):
    po_number = models.CharField(max_length=100, unique=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='purchase_orders')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, default='open')

    def __str__(self):
        return self.po_number


class GoodsReceiptNote(TimeStampedModel):
    grn_number = models.CharField(max_length=100, unique=True)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='grns')
    received_date = models.DateField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return self.grn_number


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
    uploaded_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)
    validation_errors = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.invoice_number or 'Draft'} - {self.vendor}"


class InvoiceLineItem(TimeStampedModel):
    invoice = models.ForeignKey(Invoice, related_name='line_items', on_delete=models.CASCADE)
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)


class MatchResult(TimeStampedModel):
    MATCH_TYPES = [('2way', '2-Way'), ('3way', '3-Way')]
    MATCH_STATUS = [('matched', 'Matched'), ('exception', 'Exception'), ('unmatched', 'Unmatched')]

    invoice = models.OneToOneField(Invoice, on_delete=models.CASCADE, related_name='match_result')
    match_type = models.CharField(max_length=10, choices=MATCH_TYPES, default='2way')
    status = models.CharField(max_length=15, choices=MATCH_STATUS, default='unmatched')
    differences = models.JSONField(default=dict, blank=True)
    matched_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True)


# ==========================================================
# OCR AUTO-TRIGGER SIGNAL
# ==========================================================
@receiver(post_save, sender=Invoice)
def trigger_ocr_on_upload(sender, instance, created, **kwargs):
    # Only run OCR if the invoice was just created, has a file, but no extracted text yet
    if created and instance.original_file and not instance.ocr_raw_text:
        # Import here to avoid circular imports
        from .ocr_service import extract_text_from_file, parse_invoice_fields
        
        try:
            # Run OCR
            raw_text = extract_text_from_file(instance.original_file.path)
            fields = parse_invoice_fields(raw_text)
            
            # Update instance fields
            instance.ocr_raw_text = raw_text
            
            if 'invoice_number' in fields:
                instance.invoice_number = fields['invoice_number']
            if 'total_amount' in fields:
                instance.total_amount = fields['total_amount']
                
            instance.status = 'extracted'
            
            # Save again without triggering the signal recursively
            instance.save()
            print(f"\n✅ OCR Success: {instance.invoice_number} | Amount: {instance.total_amount}\n")
            
        except Exception as e:
            print(f"\n❌ OCR Failed: {str(e)}\n")