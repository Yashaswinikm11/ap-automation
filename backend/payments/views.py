from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status, filters, serializers
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import PaymentRequest, PaymentAdvice
from .serializers import PaymentRequestSerializer, PaymentAdviceSerializer
from invoices.models import Invoice
from reports.audit import write_audit_log

class IsAPFinanceRole(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user.is_superuser or user.role in ('admin', 'clerk')


class PaymentRequestViewSet(viewsets.ModelViewSet):
    queryset = PaymentRequest.objects.all().select_related(
        'invoice', 'invoice__vendor', 'initiated_by'
    )
    serializer_class = PaymentRequestSerializer
    http_method_names = ['get', 'post', 'head', 'options']
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_method', 'invoice']
    search_fields = [
        'reference',
        'bank_reference',
        'invoice__invoice_number',
        'invoice__vendor__name',
    ]
    ordering_fields = ['created_at', 'due_date', 'amount', 'paid_at']
    ordering = ['-created_at']

    def get_permissions(self):
        permissions = [IsAuthenticated()]
        if self.action in {'create', 'mark_paid', 'generate_advice', 'cancel'}:
            permissions.append(IsAPFinanceRole())
        return permissions

    def perform_create(self, serializer):
        with transaction.atomic():
            payment = serializer.save(initiated_by=self.request.user)
            write_audit_log(
                self.request,
                action='create',
                entity_type='payment',
                entity_id=payment.pk,
                description=f'Payment request created for invoice #{payment.invoice_id}.',
                extra_data={'amount': str(payment.amount), 'payment_method': payment.payment_method},
            )

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def mark_paid(self, request, pk=None):
        payment = self.get_object()
        if payment.status not in ('pending', 'processing'):
            return Response(
                {'error': f'Only pending or processing payments can be marked paid; current status is {payment.status}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reference = str(request.data.get('reference', payment.reference)).strip()
        if not reference:
            return Response(
                {'error': 'A bank transaction reference is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        bank_reference = str(request.data.get('bank_reference', payment.bank_reference) or '').strip()
        try:
            paid_at = serializers.DateTimeField().run_validation(
                request.data.get('paid_at') or timezone.now()
            )
        except serializers.ValidationError as error:
            return Response({'error': error.detail}, status=status.HTTP_400_BAD_REQUEST)

        payment.status = 'paid'
        payment.reference = reference
        payment.bank_reference = bank_reference
        payment.paid_at = paid_at
        payment.save()

        # Update corresponding invoice status
        Invoice.objects.filter(pk=payment.invoice_id).update(status='paid')
        write_audit_log(
            request,
            action='mark_paid',
            entity_type='payment',
            entity_id=payment.pk,
            description=f'Payment #{payment.pk} marked as paid.',
            extra_data={'invoice_id': payment.invoice_id, 'bank_reference': bank_reference},
        )

        payment.refresh_from_db()
        return Response({
            'message': f'Payment #{payment.id} marked as paid successfully.',
            'payment': PaymentRequestSerializer(payment).data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def generate_advice(self, request, pk=None):
        payment = self.get_object()
        notes = request.data.get('notes', f'Generated payment advice for Payment #{payment.id}')

        now_str = timezone.now().strftime('%Y%m%d%H%M%S')
        advice_number = f"ADV-{payment.id}-{now_str}"

        advice, created = PaymentAdvice.objects.get_or_create(
            payment_request=payment,
            defaults={
                'advice_number': advice_number,
                'notes': notes,
            }
        )
        if created:
            write_audit_log(
                request,
                action='generate_advice',
                entity_type='payment_advice',
                entity_id=advice.pk,
                description=f'Payment advice generated for payment #{payment.pk}.',
            )

        return Response({
            'message': 'Payment advice generated successfully.',
            'advice': PaymentAdviceSerializer(advice).data
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def cancel(self, request, pk=None):
        payment = self.get_object()
        if payment.status not in ('pending', 'processing'):
            return Response(
                {'error': f'Cannot cancel a payment with status {payment.status}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason', '')
        payment.status = 'cancelled'
        if reason:
            payment.failure_reason = reason
        payment.save()
        write_audit_log(
            request,
            action='cancel',
            entity_type='payment',
            entity_id=payment.pk,
            description=f'Payment #{payment.pk} cancelled.',
            extra_data={'reason': reason, 'invoice_id': payment.invoice_id},
        )

        payment.refresh_from_db()
        return Response({
            'message': f'Payment #{payment.id} has been cancelled.',
            'payment': PaymentRequestSerializer(payment).data
        }, status=status.HTTP_200_OK)


class PaymentAdviceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PaymentAdvice.objects.all().select_related('payment_request')
    serializer_class = PaymentAdviceSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['advice_number', 'payment_request__reference']
