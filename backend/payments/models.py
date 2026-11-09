from django.db import models
from django.conf import settings
from core.models import TimeStampedModel
from invoices.models import Invoice


class PaymentRequest(TimeStampedModel):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('upi', 'UPI'),
        ('neft', 'NEFT'),
        ('rtgs', 'RTGS'),
        ('imps', 'IMPS'),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payment_requests')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='bank_transfer')
    reference = models.CharField(max_length=100, blank=True)
    bank_reference = models.CharField(max_length=100, blank=True)
    due_date = models.DateField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment #{self.id} for Invoice #{self.invoice_id} ({self.status})"


class PaymentAdvice(TimeStampedModel):
    payment_request = models.OneToOneField(PaymentRequest, on_delete=models.CASCADE, related_name='advice')
    advice_number = models.CharField(max_length=50, blank=True)
    advice_pdf = models.FileField(upload_to='payment_advices/', blank=True, null=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Advice {self.advice_number} for Payment #{self.payment_request_id}"
