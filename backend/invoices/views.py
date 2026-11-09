import os
from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    Invoice,
    InvoiceLineItem,
    PurchaseOrder,
    GoodsReceiptNote,
    MatchResult,
    _find_vendor_by_gstin,
)
from .serializers import (
    InvoiceSerializer,
    InvoiceLineItemSerializer,
    PurchaseOrderSerializer,
    GoodsReceiptNoteSerializer,
    MatchResultSerializer,
)
from .ocr_service import extract_text_from_file, parse_invoice_fields, extract_line_items
from .validation import run_validation_pipeline
from .matching import run_two_way_match, run_three_way_match
from approvals.models import ApprovalMatrix, ApprovalRequest
from approvals.serializers import ApprovalRequestSerializer
from reports.audit import write_audit_log

class IsAPClerkOrAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user.is_superuser or user.role in ('admin', 'clerk')


class IsInvoiceValidator(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user.is_superuser or user.role in ('admin', 'clerk', 'approver')


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all().select_related(
        'vendor', 'purchase_order', 'match_result', 'uploaded_by'
    ).prefetch_related('line_items')
    serializer_class = InvoiceSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'vendor', 'purchase_order', 'is_duplicate', 'currency']
    search_fields = ['invoice_number', 'vendor_name', 'gstin', 'vendor__name']
    ordering_fields = ['created_at', 'invoice_date', 'total_amount', 'due_date']
    ordering = ['-created_at']

    def get_permissions(self):
        permissions = [IsAuthenticated()]
        write_actions = {
            'create', 'update', 'partial_update', 'destroy',
            'run_ocr', 'match_po', 'submit_for_approval', 'bulk_upload',
        }
        if self.action in write_actions:
            permissions.append(IsAPClerkOrAdmin())
        elif self.action == 'validate':
            permissions.append(IsInvoiceValidator())
        return permissions

    def perform_create(self, serializer):
        with transaction.atomic():
            invoice = serializer.save(uploaded_by=self.request.user)
            invoice.refresh_from_db()
            write_audit_log(
                self.request,
                action='upload',
                entity_type='invoice',
                entity_id=invoice.pk,
                description=f'Invoice #{invoice.pk} uploaded.',
            )

    def perform_update(self, serializer):
        with transaction.atomic():
            invoice = serializer.save()
            write_audit_log(
                self.request,
                action='update',
                entity_type='invoice',
                entity_id=invoice.pk,
                description=f'Invoice #{invoice.pk} updated.',
            )

    def perform_destroy(self, instance):
        with transaction.atomic():
            write_audit_log(
                self.request,
                action='delete',
                entity_type='invoice',
                entity_id=instance.pk,
                description=f'Invoice #{instance.pk} deleted.',
            )
            instance.delete()

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def validate(self, request, pk=None):
        invoice = self.get_object()
        result = run_validation_pipeline(invoice)
        invoice.refresh_from_db()
        write_audit_log(
            request,
            action='validate',
            entity_type='invoice',
            entity_id=invoice.pk,
            description='Invoice validation completed.',
            extra_data={'passed': result['passed'], 'errors': result['errors']},
        )
        return Response({
            'validation': result,
            'invoice': InvoiceSerializer(invoice).data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def run_ocr(self, request, pk=None):
        invoice = self.get_object()
        if not invoice.original_file:
            return Response(
                {'error': 'Invoice does not have an uploaded file.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        file_path = invoice.original_file.path
        if not os.path.exists(file_path):
            return Response(
                {'error': f'Uploaded file not found on disk at {file_path}.'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            raw_text = extract_text_from_file(file_path)
            parsed_fields = parse_invoice_fields(raw_text)
            extracted_items = extract_line_items(raw_text)

            update_data = {
                'ocr_raw_text': raw_text,
                'status': 'extracted',
            }

            if 'invoice_number' in parsed_fields:
                update_data['invoice_number'] = parsed_fields['invoice_number']
            if 'invoice_date' in parsed_fields:
                update_data['invoice_date'] = parsed_fields['invoice_date']
            if 'total_amount' in parsed_fields:
                update_data['total_amount'] = parsed_fields['total_amount']
            if 'tax_amount' in parsed_fields:
                update_data['tax_amount'] = parsed_fields['tax_amount']
            if 'gstin' in parsed_fields:
                update_data['gstin'] = parsed_fields['gstin']
                if not invoice.vendor_id:
                    vendor = _find_vendor_by_gstin(parsed_fields['gstin'])
                    if vendor:
                        update_data['vendor'] = vendor
            if 'vendor_name' in parsed_fields:
                update_data['vendor_name'] = parsed_fields['vendor_name']

            Invoice.objects.filter(pk=invoice.pk).update(**update_data)

            # Insert extracted line items if currently empty
            if extracted_items and not invoice.line_items.exists():
                for item in extracted_items:
                    InvoiceLineItem.objects.create(
                        invoice=invoice,
                        description=item.get('description', ''),
                        quantity=item.get('quantity'),
                        unit_price=item.get('unit_price'),
                        total=item.get('total')
                    )

            invoice.refresh_from_db()
            write_audit_log(
                request,
                action='run_ocr',
                entity_type='invoice',
                entity_id=invoice.pk,
                description='OCR processing completed.',
                extra_data={'line_items_extracted': len(extracted_items)},
            )
            return Response({
                'message': 'OCR processing completed successfully.',
                'parsed_fields': parsed_fields,
                'line_items_extracted': len(extracted_items),
                'invoice': InvoiceSerializer(invoice).data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'OCR processing failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def match_po(self, request, pk=None):
        invoice = self.get_object()
        match_type = str(request.data.get('match_type', '2way')).lower()
        if match_type not in {'2way', '3way'}:
            return Response(
                {'error': "match_type must be either '2way' or '3way'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if match_type == '3way':
            result = run_three_way_match(invoice, user=request.user)
        else:
            result = run_two_way_match(invoice, user=request.user)

        write_audit_log(
            request,
            action='match_po',
            entity_type='invoice',
            entity_id=invoice.pk,
            description=f'{match_type} PO matching completed.',
            extra_data={'match_result_id': result.pk, 'status': result.status},
        )
        return Response(MatchResultSerializer(result).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def submit_for_approval(self, request, pk=None):
        invoice = self.get_object()
        user = request.user
        if not user.is_authenticated:
            return Response({'error': 'Authentication is required.'}, status=status.HTTP_401_UNAUTHORIZED)
        if not (user.is_superuser or user.role in ('clerk', 'admin')):
            return Response({'error': 'Your role cannot submit invoices for approval.'}, status=status.HTTP_403_FORBIDDEN)
        if invoice.status != 'validated' or invoice.validation_errors or invoice.is_duplicate:
            return Response(
                {'error': 'Only invoices that passed validation and are not duplicates can be submitted.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        amount = invoice.total_amount or 0

        # Find best matching matrix
        matrix = ApprovalMatrix.objects.filter(
            is_active=True,
            min_amount__lte=amount
        ).filter(
            Q(max_amount__gte=amount) | Q(max_amount__isnull=True)
        ).order_by('-min_amount').first()
        if not matrix:
            return Response(
                {'error': 'No active approval matrix is configured for this invoice amount.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        first_step = matrix.steps.order_by('step_order').first()
        if first_step is None:
            return Response(
                {'error': 'The selected approval matrix has no configured steps.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        approval_req, created = ApprovalRequest.objects.update_or_create(
            invoice=invoice,
            defaults={
                'matrix': matrix,
                'status': 'pending',
                'current_step': first_step.step_order,
                'submitted_by': user,
                'submitted_at': timezone.now(),
                'completed_at': None
            }
        )

        Invoice.objects.filter(pk=invoice.pk).update(status='pending_approval')
        invoice.refresh_from_db()
        write_audit_log(
            request,
            action='submit_for_approval',
            entity_type='invoice',
            entity_id=invoice.pk,
            description='Invoice submitted for approval.',
            extra_data={'approval_request_id': approval_req.pk, 'approval_matrix_id': matrix.pk},
        )

        return Response({
            'message': 'Invoice submitted for approval successfully.',
            'approval_request': ApprovalRequestSerializer(approval_req).data
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def bulk_upload(self, request):
        uploaded_files = request.FILES.getlist('files')
        if not uploaded_files:
            # Check dictionary values if not sent under key 'files'
            uploaded_files = list(request.FILES.values())

        if not uploaded_files:
            return Response(
                {'error': 'No files provided in request.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        created_invoices = []
        user = request.user if request.user.is_authenticated else None

        for file_obj in uploaded_files:
            invoice = Invoice.objects.create(
                original_file=file_obj,
                uploaded_by=user,
                status='uploaded'
            )
            invoice.refresh_from_db()
            created_invoices.append(invoice)
            write_audit_log(
                request,
                action='bulk_upload',
                entity_type='invoice',
                entity_id=invoice.pk,
                description=f'Invoice #{invoice.pk} uploaded in bulk.',
            )

        serializer = InvoiceSerializer(created_invoices, many=True)
        return Response({
            'uploaded_count': len(created_invoices),
            'invoices': serializer.data
        }, status=status.HTTP_201_CREATED)


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.all().select_related('vendor').prefetch_related('line_items')
    serializer_class = PurchaseOrderSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'vendor', 'currency']
    search_fields = ['po_number', 'vendor__name', 'description']
    ordering_fields = ['po_date', 'total_amount', 'created_at']
    ordering = ['-created_at']

    def get_permissions(self):
        permissions = [IsAuthenticated()]
        if self.action in {'create', 'update', 'partial_update', 'destroy'}:
            permissions.append(IsAPClerkOrAdmin())
        return permissions


class GoodsReceiptNoteViewSet(viewsets.ModelViewSet):
    queryset = GoodsReceiptNote.objects.all().select_related('purchase_order', 'received_by').prefetch_related('line_items')
    serializer_class = GoodsReceiptNoteSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['purchase_order', 'received_date']
    search_fields = ['grn_number', 'purchase_order__po_number']
    ordering_fields = ['received_date', 'total_amount', 'created_at']
    ordering = ['-received_date']

    def get_permissions(self):
        permissions = [IsAuthenticated()]
        if self.action in {'create', 'update', 'partial_update', 'destroy'}:
            permissions.append(IsAPClerkOrAdmin())
        return permissions
