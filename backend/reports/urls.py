from django.urls import path
from .views import (
    APAgingReportView,
    InvoiceStatusReportView,
    ExceptionReportView,
    AuditLogView,
    GSTReportView,
)

app_name = 'reports'

urlpatterns = [
    path('aging/', APAgingReportView.as_view(), name='report-aging'),
    path('invoice-status/', InvoiceStatusReportView.as_view(), name='report-invoice-status'),
    path('exceptions/', ExceptionReportView.as_view(), name='report-exceptions'),
    path('audit-log/', AuditLogView.as_view(), name='report-audit-log'),
    path('gst/', GSTReportView.as_view(), name='report-gst'),
]
