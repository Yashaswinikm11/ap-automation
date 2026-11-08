from django.db import models
from core.models import TimeStampedModel
from invoices.models import Invoice


class PaymentRequest(TimeStampedModel):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payment_requests')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reference = models.CharField(max_length=100, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)


class PaymentAdvice(TimeStampedModel):
    payment_request = models.OneToOneField(PaymentRequest, on_delete=models.CASCADE, related_name='advice')
    advice_pdf = models.FileField(upload_to='payment_advices/', blank=True, null=True)
    notes = models.TextField(blank=True)