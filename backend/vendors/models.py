from django.db import models
from core.models import TimeStampedModel


class Vendor(TimeStampedModel):
    ONBOARDING_STATUS = [
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    name = models.CharField(max_length=255)
    gstin = models.CharField(max_length=15, blank=True)
    pan_number = models.CharField(max_length=10, blank=True)
    tin_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    bank_account = models.CharField(max_length=50, blank=True)
    bank_ifsc = models.CharField(max_length=15, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    bank_branch = models.CharField(max_length=100, blank=True)
    payment_terms = models.IntegerField(default=30, help_text='Payment terms in days')
    onboarding_status = models.CharField(max_length=20, choices=ONBOARDING_STATUS, default='pending')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
