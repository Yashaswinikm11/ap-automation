from django.contrib.auth import get_user_model
from django.db import models
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import ApprovalMatrix, ApprovalStep, ApprovalRequest, ApprovalAction
from .serializers import (
    ApprovalMatrixSerializer,
    ApprovalStepSerializer,
    ApprovalRequestSerializer,
    ApprovalActionSerializer,
)
from invoices.models import Invoice
from reports.audit import write_audit_log

User = get_user_model()


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user.is_superuser or user.role == 'admin'


class ApprovalMatrixViewSet(viewsets.ModelViewSet):
    queryset = ApprovalMatrix.objects.all().prefetch_related('steps')
    serializer_class = ApprovalMatrixSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name']
    ordering_fields = ['min_amount', 'max_amount', 'name']
    ordering = ['min_amount']

    def get_permissions(self):
        permissions = [IsAuthenticated()]
        if self.action not in {'list', 'retrieve'}:
            permissions.append(IsAdminRole())
        return permissions


class ApprovalRequestViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ApprovalRequest.objects.all().select_related(
        'invoice', 'matrix', 'submitted_by'
    ).prefetch_related('actions', 'matrix__steps')
    serializer_class = ApprovalRequestSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'matrix', 'current_step']
    search_fields = ['invoice__invoice_number', 'invoice__vendor__name', 'matrix__name']
    ordering_fields = ['submitted_at', 'status', 'current_step']
    ordering = ['-submitted_at']

    def _current_step(self, approval_req):
        if not approval_req.matrix_id:
            return None
        return approval_req.matrix.steps.filter(
            step_order=approval_req.current_step
        ).first()

    def _authorize_current_step(self, request, approval_req, step):
        user = request.user
        if step is None:
            return Response(
                {'error': 'The current approval step is not configured.'},
                status=status.HTTP_409_CONFLICT
            )
        if step.is_parallel:
            if user.role != step.approver_role:
                return Response(
                    {'error': 'Every active user with the configured role must decide this parallel approval step.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            return None
        if user.is_superuser or user.role == 'admin':
            return None
        if user.role != step.approver_role:
            return Response(
                {'error': 'Your role is not authorized to decide this approval step.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return None

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def approve(self, request, pk=None):
        approval_req = self.get_object()

        if approval_req.status != 'pending':
            return Response(
                {'error': f'Request is already {approval_req.status}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        step = self._current_step(approval_req)
        authorization_error = self._authorize_current_step(request, approval_req, step)
        if authorization_error:
            return authorization_error

        action_step = approval_req.current_step
        if ApprovalAction.objects.filter(
            request=approval_req,
            step_number=action_step,
            user=request.user,
            decision__in=['approve', 'reject'],
        ).exists():
            return Response(
                {'error': 'You have already submitted a decision for this approval step.'},
                status=status.HTTP_409_CONFLICT
            )

        comments = request.data.get('comments', '')
        user = request.user

        # Log action
        ApprovalAction.objects.create(
            request=approval_req,
            user=user,
            decision='approve',
            comments=comments,
            step_number=action_step
        )

        if step.is_parallel:
            active_approvers = User.objects.filter(
                role=step.approver_role,
                is_active=True,
            ).count()
            completed_approvers = ApprovalAction.objects.filter(
                request=approval_req,
                step_number=action_step,
                decision='approve',
                user__role=step.approver_role,
                user__is_active=True,
            ).values('user_id').distinct().count()
            if completed_approvers < active_approvers:
                msg = f'Approval recorded; waiting for {active_approvers - completed_approvers} more approver(s).'
                write_audit_log(
                    request,
                    action='approve',
                    entity_type='approval_request',
                    entity_id=approval_req.pk,
                    description=msg,
                    extra_data={'invoice_id': approval_req.invoice_id, 'step': action_step},
                )
                approval_req.refresh_from_db()
                return Response({
                    'message': msg,
                    'approval_request': ApprovalRequestSerializer(approval_req).data
                }, status=status.HTTP_200_OK)

        # Determine next step
        next_step = None
        if approval_req.matrix:
            next_step = approval_req.matrix.steps.filter(
                step_order__gt=approval_req.current_step
            ).order_by('step_order').first()

        if next_step:
            approval_req.current_step = next_step.step_order
            approval_req.save()
            msg = f"Step approved. Advanced to step {approval_req.current_step} ({next_step.approver_role})."
        else:
            approval_req.status = 'approved'
            approval_req.completed_at = timezone.now()
            approval_req.save()
            Invoice.objects.filter(pk=approval_req.invoice_id).update(status='approved')
            msg = "Approval process completed. Invoice approved."

        write_audit_log(
            request,
            action='approve',
            entity_type='approval_request',
            entity_id=approval_req.pk,
            description=msg,
            extra_data={'invoice_id': approval_req.invoice_id, 'step': action_step},
        )
        approval_req.refresh_from_db()
        return Response({
            'message': msg,
            'approval_request': ApprovalRequestSerializer(approval_req).data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def reject(self, request, pk=None):
        approval_req = self.get_object()

        if approval_req.status != 'pending':
            return Response(
                {'error': f'Request is already {approval_req.status}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        step = self._current_step(approval_req)
        authorization_error = self._authorize_current_step(request, approval_req, step)
        if authorization_error:
            return authorization_error

        action_step = approval_req.current_step
        if ApprovalAction.objects.filter(
            request=approval_req,
            step_number=action_step,
            user=request.user,
            decision__in=['approve', 'reject'],
        ).exists():
            return Response(
                {'error': 'You have already submitted a decision for this approval step.'},
                status=status.HTTP_409_CONFLICT
            )

        comments = str(request.data.get('comments', '')).strip()
        if not comments:
            return Response(
                {'error': 'A rejection reason is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user = request.user

        ApprovalAction.objects.create(
            request=approval_req,
            user=user,
            decision='reject',
            comments=comments,
            step_number=action_step
        )

        approval_req.status = 'rejected'
        approval_req.completed_at = timezone.now()
        approval_req.save()
        Invoice.objects.filter(pk=approval_req.invoice_id).update(status='rejected')

        write_audit_log(
            request,
            action='reject',
            entity_type='approval_request',
            entity_id=approval_req.pk,
            description='Invoice approval rejected.',
            extra_data={'invoice_id': approval_req.invoice_id, 'step': action_step},
        )
        approval_req.refresh_from_db()
        return Response({
            'message': 'Invoice approval rejected.',
            'approval_request': ApprovalRequestSerializer(approval_req).data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def pending_for_me(self, request):
        user = request.user
        role = getattr(user, 'role', None) if user.is_authenticated else None

        qs = ApprovalRequest.objects.filter(status='pending').select_related(
            'invoice', 'matrix', 'submitted_by'
        ).prefetch_related('actions', 'matrix__steps')

        current_role_step = models.Q(
            matrix__steps__step_order=models.F('current_step'),
            matrix__steps__approver_role=role,
        )
        if user.is_superuser or role == 'admin':
            current_role_step |= models.Q(
                matrix__steps__step_order=models.F('current_step'),
                matrix__steps__is_parallel=False,
            )
        qs = qs.filter(current_role_step).exclude(
            actions__user=user,
            actions__step_number=models.F('current_step'),
            actions__decision__in=['approve', 'reject'],
        ).distinct()

        serializer = ApprovalRequestSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
