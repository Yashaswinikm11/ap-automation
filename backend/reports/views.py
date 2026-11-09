import csv
from datetime import date
from django.http import HttpResponse
from django.db.models import Q, Sum, Count
from django.contrib.auth import get_user_model
from rest_framework import permissions, status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from invoices.models import Invoice, MatchResult
from .models import AuditLog
from .serializers import AuditLogSerializer

User = get_user_model()


class StandardReportPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 500


class APAgingReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = date.today()
        invoices = Invoice.objects.exclude(
            status__in=['paid', 'rejected']
        ).select_related('vendor')

        report_data = []
        summary = {
            '0-30 days': {'count': 0, 'amount': 0.0},
            '31-60 days': {'count': 0, 'amount': 0.0},
            '61-90 days': {'count': 0, 'amount': 0.0},
            '90+ days': {'count': 0, 'amount': 0.0},
        }

        for inv in invoices:
            ref_date = inv.due_date or inv.invoice_date or inv.created_at.date()
            diff_days = max(0, (today - ref_date).days)
            amount = float(inv.total_amount or 0)

            if diff_days <= 30:
                bucket = '0-30 days'
            elif diff_days <= 60:
                bucket = '31-60 days'
            elif diff_days <= 90:
                bucket = '61-90 days'
            else:
                bucket = '90+ days'

            summary[bucket]['count'] += 1
            summary[bucket]['amount'] = round(summary[bucket]['amount'] + amount, 2)

            report_data.append({
                'invoice_id': inv.id,
                'invoice_number': inv.invoice_number or 'Draft',
                'vendor_name': inv.vendor.name if inv.vendor else (inv.vendor_name or 'Unknown'),
                'invoice_date': str(inv.invoice_date) if inv.invoice_date else '',
                'due_date': str(inv.due_date) if inv.due_date else '',
                'amount': amount,
                'status': inv.status,
                'days_past_due': diff_days,
                'aging_bucket': bucket,
            })

        if request.query_params.get('format') == 'csv':
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = 'attachment; filename="ap_aging_report.csv"'
            writer = csv.writer(response)
            writer.writerow([
                'Invoice ID', 'Invoice Number', 'Vendor Name', 'Invoice Date',
                'Due Date', 'Amount', 'Status', 'Days Past Due', 'Aging Bucket'
            ])
            for row in report_data:
                writer.writerow([
                    row['invoice_id'], row['invoice_number'], row['vendor_name'],
                    row['invoice_date'], row['due_date'], row['amount'],
                    row['status'], row['days_past_due'], row['aging_bucket']
                ])
            return response

        return Response({
            'as_of_date': str(today),
            'summary': summary,
            'details': report_data
        }, status=status.HTTP_200_OK)


class InvoiceStatusReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        invoices = Invoice.objects.all().select_related('vendor', 'purchase_order', 'uploaded_by')

        status_param = request.query_params.get('status')
        if status_param:
            invoices = invoices.filter(status=status_param)

        vendor_id = request.query_params.get('vendor_id')
        if vendor_id:
            invoices = invoices.filter(vendor_id=vendor_id)

        report_data = []
        for inv in invoices:
            report_data.append({
                'id': inv.id,
                'invoice_number': inv.invoice_number or 'Draft',
                'vendor_name': inv.vendor.name if inv.vendor else (inv.vendor_name or ''),
                'po_number': inv.purchase_order.po_number if inv.purchase_order else '',
                'invoice_date': str(inv.invoice_date) if inv.invoice_date else '',
                'due_date': str(inv.due_date) if inv.due_date else '',
                'total_amount': float(inv.total_amount or 0),
                'tax_amount': float(inv.tax_amount or 0),
                'currency': inv.currency,
                'status': inv.status,
                'is_duplicate': inv.is_duplicate,
                'uploaded_by': inv.uploaded_by.username if inv.uploaded_by else '',
                'created_at': inv.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            })

        if request.query_params.get('format') == 'csv':
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = 'attachment; filename="invoice_status_report.csv"'
            writer = csv.writer(response)
            writer.writerow([
                'ID', 'Invoice Number', 'Vendor Name', 'PO Number',
                'Invoice Date', 'Due Date', 'Total Amount', 'Tax Amount',
                'Currency', 'Status', 'Is Duplicate', 'Uploaded By', 'Created At'
            ])
            for r in report_data:
                writer.writerow([
                    r['id'], r['invoice_number'], r['vendor_name'], r['po_number'],
                    r['invoice_date'], r['due_date'], r['total_amount'], r['tax_amount'],
                    r['currency'], r['status'], r['is_duplicate'], r['uploaded_by'], r['created_at']
                ])
            return response

        return Response({
            'count': len(report_data),
            'invoices': report_data
        }, status=status.HTTP_200_OK)


class ExceptionReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Invoices with validation errors or matching exceptions
        invoices = Invoice.objects.filter(
            Q(is_duplicate=True) |
            ~Q(validation_errors=[]) |
            Q(match_result__status='exception')
        ).select_related('vendor', 'match_result').distinct()

        report_data = []
        for inv in invoices:
            has_match = hasattr(inv, 'match_result')
            match_status = inv.match_result.status if has_match else 'no_match_run'
            match_issues = inv.match_result.differences.get('issues', []) if has_match else []

            report_data.append({
                'invoice_id': inv.id,
                'invoice_number': inv.invoice_number or 'Draft',
                'vendor_name': inv.vendor.name if inv.vendor else (inv.vendor_name or ''),
                'total_amount': float(inv.total_amount or 0),
                'status': inv.status,
                'is_duplicate': inv.is_duplicate,
                'duplicate_of_id': inv.duplicate_of_id,
                'validation_errors': inv.validation_errors,
                'match_status': match_status,
                'match_issues': match_issues,
                'created_at': inv.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            })

        if request.query_params.get('format') == 'csv':
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = 'attachment; filename="exception_report.csv"'
            writer = csv.writer(response)
            writer.writerow([
                'Invoice ID', 'Invoice Number', 'Vendor Name', 'Total Amount',
                'Status', 'Is Duplicate', 'Validation Errors', 'Match Status',
                'Match Issues', 'Created At'
            ])
            for r in report_data:
                writer.writerow([
                    r['invoice_id'],
                    r['invoice_number'],
                    r['vendor_name'],
                    r['total_amount'],
                    r['status'],
                    r['is_duplicate'],
                    "; ".join(r['validation_errors']) if isinstance(r['validation_errors'], list) else str(r['validation_errors']),
                    r['match_status'],
                    "; ".join(r['match_issues']) if isinstance(r['match_issues'], list) else str(r['match_issues']),
                    r['created_at'],
                ])
            return response

        return Response({
            'total_exceptions': len(report_data),
            'exceptions': report_data
        }, status=status.HTTP_200_OK)


class AuditLogView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = AuditLog.objects.all().select_related('user')
    serializer_class = AuditLogSerializer
    pagination_class = StandardReportPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['entity_type', 'action', 'user']
    search_fields = ['description', 'action', 'entity_type', 'user__username']
    ordering_fields = ['created_at', 'action']
    ordering = ['-created_at']

    def get(self, request, *args, **kwargs):
        if request.query_params.get('format') == 'csv':
            queryset = self.filter_queryset(self.get_queryset())
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = 'attachment; filename="audit_log_report.csv"'
            writer = csv.writer(response)
            writer.writerow([
                'ID', 'Timestamp', 'User', 'Action', 'Entity Type',
                'Entity ID', 'Description', 'IP Address'
            ])
            for log in queryset:
                writer.writerow([
                    log.id,
                    log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    log.user.username if log.user else 'System',
                    log.action,
                    log.entity_type,
                    log.entity_id or '',
                    log.description,
                    log.ip_address,
                ])
            return response

        return super().get(request, *args, **kwargs)


class GSTReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        invoices = Invoice.objects.all().select_related('vendor')

        report_data = []
        total_taxable_sum = 0.0
        total_tax_sum = 0.0

        for inv in invoices:
            total_amt = float(inv.total_amount or 0)
            tax_amt = float(inv.tax_amount or 0)
            taxable_amt = max(0.0, total_amt - tax_amt)

            total_taxable_sum += taxable_amt
            total_tax_sum += tax_amt

            gstin = inv.gstin or (inv.vendor.gstin if inv.vendor else '')

            report_data.append({
                'invoice_id': inv.id,
                'invoice_number': inv.invoice_number or 'Draft',
                'vendor_name': inv.vendor.name if inv.vendor else (inv.vendor_name or ''),
                'gstin': gstin,
                'invoice_date': str(inv.invoice_date) if inv.invoice_date else '',
                'taxable_amount': round(taxable_amt, 2),
                'tax_amount': round(tax_amt, 2),
                'total_amount': round(total_amt, 2),
                'status': inv.status,
            })

        summary = {
            'total_invoices': len(report_data),
            'total_taxable_amount': round(total_taxable_sum, 2),
            'total_tax_amount': round(total_tax_sum, 2),
            'grand_total_amount': round(total_taxable_sum + total_tax_sum, 2),
        }

        if request.query_params.get('format') == 'csv':
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = 'attachment; filename="gst_report.csv"'
            writer = csv.writer(response)
            writer.writerow([
                'Invoice ID', 'Invoice Number', 'Vendor Name', 'GSTIN',
                'Invoice Date', 'Taxable Amount', 'Tax Amount', 'Total Amount', 'Status'
            ])
            for r in report_data:
                writer.writerow([
                    r['invoice_id'], r['invoice_number'], r['vendor_name'],
                    r['gstin'], r['invoice_date'], r['taxable_amount'],
                    r['tax_amount'], r['total_amount'], r['status']
                ])
            return response

        return Response({
            'summary': summary,
            'invoices': report_data
        }, status=status.HTTP_200_OK)
