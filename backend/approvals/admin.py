from django.contrib import admin
from .models import ApprovalMatrix, ApprovalStep, ApprovalRequest, ApprovalAction


@admin.register(ApprovalMatrix)
class ApprovalMatrixAdmin(admin.ModelAdmin):
    list_display = ('name', 'min_amount', 'max_amount', 'is_active')


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'status', 'current_step', 'created_at')
    list_filter = ('status',)


admin.site.register(ApprovalStep)
admin.site.register(ApprovalAction)