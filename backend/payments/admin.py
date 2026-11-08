from django.contrib import admin
from .models import PaymentRequest, PaymentAdvice


@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'amount', 'status', 'created_at')
    list_filter = ('status',)


admin.site.register(PaymentAdvice)