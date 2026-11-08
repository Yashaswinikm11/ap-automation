from django.contrib import admin
from .models import Vendor


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('name', 'gstin', 'email', 'is_active')
    search_fields = ('name', 'gstin')
    list_filter = ('is_active',)