from django.db import models
from core.models import TimeStampedModel


class Vendor(TimeStampedModel):
    name = models.CharField(max_length=255)
    gstin = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    bank_account = models.CharField(max_length=50, blank=True)
    bank_ifsc = models.CharField(max_length=15, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name