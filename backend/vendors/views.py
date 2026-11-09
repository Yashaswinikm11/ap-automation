import re
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, IsAuthenticated
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from .models import Vendor
from .serializers import VendorSerializer
from reports.audit import write_audit_log

GSTIN_REGEX = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'


class IsAPClerkOrAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user.is_superuser or user.role in ('admin', 'clerk')


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user.is_superuser or user.role == 'admin'


class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.all().order_by('name')
    serializer_class = VendorSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ('name', 'gstin', 'pan_number', 'email')
    filterset_fields = ('is_active', 'onboarding_status')
    ordering_fields = ('name', 'created_at', 'payment_terms')

    def get_permissions(self):
        permissions = [IsAuthenticated()]
        if self.action in {'create', 'update', 'partial_update', 'destroy', 'validate_gstin'}:
            permissions.append(IsAPClerkOrAdmin())
        if self.action in {'approve_onboarding', 'reject_onboarding'}:
            permissions.append(IsAdminRole())
        return permissions

    def perform_create(self, serializer):
        with transaction.atomic():
            vendor = serializer.save()
            write_audit_log(
                self.request,
                action='create',
                entity_type='vendor',
                entity_id=vendor.pk,
                description=f'Vendor {vendor.name} created.',
            )

    def perform_update(self, serializer):
        with transaction.atomic():
            vendor = serializer.save()
            write_audit_log(
                self.request,
                action='update',
                entity_type='vendor',
                entity_id=vendor.pk,
                description=f'Vendor {vendor.name} updated.',
            )

    def perform_destroy(self, instance):
        with transaction.atomic():
            write_audit_log(
                self.request,
                action='delete',
                entity_type='vendor',
                entity_id=instance.pk,
                description=f'Vendor {instance.name} deleted.',
            )
            instance.delete()

    @action(detail=True, methods=['post'])
    def validate_gstin(self, request, pk=None):
        vendor = self.get_object()
        gstin = request.data.get('gstin', vendor.gstin)
        if not gstin:
            return Response(
                {
                    'valid': False,
                    'gstin': '',
                    'message': 'No GSTIN provided for validation.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        gstin_clean = gstin.strip().upper()
        if len(gstin_clean) != 15:
            return Response(
                {
                    'valid': False,
                    'gstin': gstin_clean,
                    'message': 'GSTIN must be exactly 15 characters long.'
                },
                status=status.HTTP_200_OK
            )

        if not re.match(GSTIN_REGEX, gstin_clean):
            return Response(
                {
                    'valid': False,
                    'gstin': gstin_clean,
                    'message': 'Invalid GSTIN format structure.'
                },
                status=status.HTTP_200_OK
            )

        try:
            state_code = int(gstin_clean[:2])
            if state_code < 1 or state_code > 37:
                return Response(
                    {
                        'valid': False,
                        'gstin': gstin_clean,
                        'message': f'Invalid GSTIN state code: {state_code}. Must be between 01 and 37.'
                    },
                    status=status.HTTP_200_OK
                )
        except ValueError:
            return Response(
                {
                    'valid': False,
                    'gstin': gstin_clean,
                    'message': 'GSTIN state code must be numeric.'
                },
                status=status.HTTP_200_OK
            )

        return Response(
            {
                'valid': True,
                'gstin': gstin_clean,
                'state_code': state_code,
                'message': 'GSTIN format is valid; government registry status was not checked.'
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def approve_onboarding(self, request, pk=None):
        if not (request.user.is_superuser or request.user.role == 'admin'):
            return Response(
                {'error': 'Only an administrator can approve vendor onboarding.'},
                status=status.HTTP_403_FORBIDDEN
            )
        vendor = self.get_object()
        with transaction.atomic():
            vendor.onboarding_status = 'approved'
            vendor.save(update_fields=['onboarding_status', 'updated_at'])
            write_audit_log(
                request,
                action='approve_onboarding',
                entity_type='vendor',
                entity_id=vendor.pk,
                description=f'Vendor {vendor.name} onboarding approved.',
            )
        return Response(
            {
                'status': 'success',
                'message': f'Vendor {vendor.name} has been approved.',
                'vendor': VendorSerializer(vendor).data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def reject_onboarding(self, request, pk=None):
        if not (request.user.is_superuser or request.user.role == 'admin'):
            return Response(
                {'error': 'Only an administrator can reject vendor onboarding.'},
                status=status.HTTP_403_FORBIDDEN
            )
        vendor = self.get_object()
        with transaction.atomic():
            vendor.onboarding_status = 'rejected'
            vendor.save(update_fields=['onboarding_status', 'updated_at'])
            write_audit_log(
                request,
                action='reject_onboarding',
                entity_type='vendor',
                entity_id=vendor.pk,
                description=f'Vendor {vendor.name} onboarding rejected.',
            )
        return Response(
            {
                'status': 'success',
                'message': f'Vendor {vendor.name} has been rejected.',
                'vendor': VendorSerializer(vendor).data
            },
            status=status.HTTP_200_OK
        )
