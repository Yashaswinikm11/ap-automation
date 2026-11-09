from datetime import date
from django.db.models import Avg, Count, Sum, fields
from django.db.models.functions import TruncMonth, Coalesce
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from invoices.models import Invoice
from approvals.models import ApprovalRequest
from payments.models import PaymentRequest
from vendors.models import Vendor


class DashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = date.today()

        # 1. Invoice Counts
        total_invoices = Invoice.objects.count()
        status_counts = {
            'total': total_invoices,
            'uploaded': Invoice.objects.filter(status='uploaded').count(),
            'extracted': Invoice.objects.filter(status='extracted').count(),
            'validated': Invoice.objects.filter(status='validated').count(),
            'pending_approval': Invoice.objects.filter(status='pending_approval').count(),
            'approved': Invoice.objects.filter(status='approved').count(),
            'rejected': Invoice.objects.filter(status='rejected').count(),
            'paid': Invoice.objects.filter(status='paid').count(),
        }

        # 2. Invoice Aging (unpaid invoices)
        unpaid_invoices = Invoice.objects.exclude(status__in=['paid', 'rejected'])
        aging_buckets = {
            '0-30 days': {'count': 0, 'amount': 0.0},
            '31-60 days': {'count': 0, 'amount': 0.0},
            '61-90 days': {'count': 0, 'amount': 0.0},
            '90+ days': {'count': 0, 'amount': 0.0},
        }

        for inv in unpaid_invoices:
            ref_date = inv.due_date or inv.invoice_date or inv.created_at.date()
            diff_days = (today - ref_date).days
            amount = float(inv.total_amount or 0)

            if diff_days <= 30:
                bucket_key = '0-30 days'
            elif diff_days <= 60:
                bucket_key = '31-60 days'
            elif diff_days <= 90:
                bucket_key = '61-90 days'
            else:
                bucket_key = '90+ days'

            aging_buckets[bucket_key]['count'] += 1
            aging_buckets[bucket_key]['amount'] = round(
                aging_buckets[bucket_key]['amount'] + amount, 2
            )

        invoice_aging = [
            {'bucket': k, 'count': v['count'], 'amount': round(v['amount'], 2)}
            for k, v in aging_buckets.items()
        ]

        # 3. Pending Approvals Count
        pending_approvals_count = ApprovalRequest.objects.filter(status='pending').count()

        # 4. OCR Accuracy
        conf_agg = Invoice.objects.filter(ocr_confidence__isnull=False).aggregate(
            avg_conf=Avg('ocr_confidence')
        )
        if conf_agg['avg_conf'] is not None:
            ocr_accuracy = round(float(conf_agg['avg_conf']), 2)
        else:
            ocr_accuracy = None

        # 5. Average Processing Days
        completed_approvals = ApprovalRequest.objects.filter(
            status='approved',
            completed_at__isnull=False
        ).select_related('invoice')
        processing_days = [
            (approval.completed_at - approval.invoice.created_at).total_seconds() / 86400.0
            for approval in completed_approvals
            if approval.completed_at >= approval.invoice.created_at
        ]
        avg_processing_days = round(sum(processing_days) / len(processing_days), 2) if processing_days else 0.0

        # 6. Payment Summary
        pending_pay_agg = PaymentRequest.objects.filter(status='pending').aggregate(
            total=Coalesce(Sum('amount'), 0, output_field=fields.DecimalField())
        )
        paid_pay_agg = PaymentRequest.objects.filter(status='paid').aggregate(
            total=Coalesce(Sum('amount'), 0, output_field=fields.DecimalField())
        )
        overdue_pay_count = PaymentRequest.objects.filter(
            status='pending',
            due_date__lt=today
        ).count()

        payment_summary = {
            'pending_amount': float(pending_pay_agg['total']),
            'paid_amount': float(paid_pay_agg['total']),
            'overdue_count': overdue_pay_count,
        }

        # 7. Vendor Analytics
        vendor_qs = Invoice.objects.values('vendor__name', 'vendor_name').annotate(
            invoice_count=Count('id'),
            total_amount=Coalesce(Sum('total_amount'), 0, output_field=fields.DecimalField())
        ).order_by('-total_amount')[:10]

        vendor_analytics = []
        for v in vendor_qs:
            name = v['vendor__name'] or v['vendor_name'] or 'Unknown'
            vendor_analytics.append({
                'vendor_name': name,
                'invoice_count': v['invoice_count'],
                'total_amount': float(v['total_amount']),
            })

        # 8. Monthly Invoice Trend
        monthly_qs = Invoice.objects.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id'),
            amount=Coalesce(Sum('total_amount'), 0, output_field=fields.DecimalField())
        ).order_by('month')

        monthly_invoice_trend = []
        for m in monthly_qs:
            if m['month']:
                monthly_invoice_trend.append({
                    'month': m['month'].strftime('%Y-%m'),
                    'count': m['count'],
                    'amount': float(m['amount']),
                })

        data = {
            'invoice_counts': status_counts,
            'invoice_aging': invoice_aging,
            'pending_approvals_count': pending_approvals_count,
            'ocr_accuracy': ocr_accuracy,
            'avg_processing_days': avg_processing_days,
            'payment_summary': payment_summary,
            'vendor_analytics': vendor_analytics,
            'monthly_invoice_trend': monthly_invoice_trend,
        }

        return Response(data, status=status.HTTP_200_OK)
