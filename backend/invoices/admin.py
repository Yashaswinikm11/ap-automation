from django.contrib import admin
from .models import EmailIngestion, Invoice, InvoiceLineItem, PurchaseOrder, GoodsReceiptNote, MatchResult

class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 1

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'invoice_number', 'vendor', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'vendor')
    search_fields = ('invoice_number', 'vendor__name')
    inlines = [InvoiceLineItemInline]

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('po_number', 'vendor', 'total_amount', 'status')
    search_fields = ('po_number',)

@admin.register(GoodsReceiptNote)
class GoodsReceiptNoteAdmin(admin.ModelAdmin):
    list_display = ('grn_number', 'purchase_order', 'received_date', 'total_amount')

admin.site.register(MatchResult)


@admin.register(EmailIngestion)
class EmailIngestionAdmin(admin.ModelAdmin):
    list_display = ('mailbox', 'subject', 'sender', 'status', 'received_at', 'created_at')
    list_filter = ('status', 'mailbox')
    search_fields = ('subject', 'sender', 'message_id')
    readonly_fields = ('mailbox', 'message_id', 'subject', 'sender', 'received_at', 'status', 'error_message', 'invoices')