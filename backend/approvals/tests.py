from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from approvals.models import ApprovalAction, ApprovalMatrix, ApprovalRequest, ApprovalStep
from invoices.models import Invoice
from reports.models import AuditLog
from vendors.models import Vendor

User = get_user_model()


class ApprovalWorkflowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.vendor = Vendor.objects.create(
            name='Workflow Test Vendor',
            onboarding_status='approved',
        )
        self.invoice = Invoice.objects.create(
            invoice_number='AP-TEST-1001',
            vendor=self.vendor,
            invoice_date=date(2026, 1, 1),
            total_amount=Decimal('100.00'),
            status='pending_approval',
            original_file='test-invoice.pdf',
        )
        self.matrix = ApprovalMatrix.objects.create(
            name='Test approvals',
            min_amount=Decimal('0.00'),
            max_amount=None,
        )
        ApprovalStep.objects.create(
            matrix=self.matrix,
            step_order=5,
            approver_role='approver',
        )
        self.approval = ApprovalRequest.objects.create(
            invoice=self.invoice,
            matrix=self.matrix,
            current_step=5,
            status='pending',
        )
        self.approve_url = f'/api/approvals/requests/{self.approval.pk}/approve/'
        self.reject_url = f'/api/approvals/requests/{self.approval.pk}/reject/'

    def test_only_current_step_role_can_approve(self):
        clerk = User.objects.create_user(username='test-clerk', password='test-password', role='clerk')
        self.client.force_authenticate(clerk)

        response = self.client.post(self.approve_url, {}, format='json')

        self.assertEqual(response.status_code, 403)
        self.assertFalse(ApprovalAction.objects.filter(request=self.approval).exists())
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'pending_approval')

    def test_current_approver_approves_and_audits(self):
        approver = User.objects.create_user(username='test-approver', password='test-password', role='approver')
        self.client.force_authenticate(approver)

        response = self.client.post(self.approve_url, {'comments': 'Reviewed'}, format='json')

        self.assertEqual(response.status_code, 200)
        self.approval.refresh_from_db()
        self.invoice.refresh_from_db()
        self.assertEqual(self.approval.status, 'approved')
        self.assertEqual(self.invoice.status, 'approved')
        self.assertTrue(AuditLog.objects.filter(
            entity_type='approval_request',
            entity_id=self.approval.pk,
            action='approve',
            user=approver,
        ).exists())

    def test_parallel_step_waits_for_every_active_user_with_the_role(self):
        ApprovalStep.objects.filter(matrix=self.matrix, step_order=5).update(is_parallel=True)
        first_approver = User.objects.create_user(
            username='parallel-approver-one',
            password='test-password',
            role='approver',
        )
        second_approver = User.objects.create_user(
            username='parallel-approver-two',
            password='test-password',
            role='approver',
        )
        self.client.force_authenticate(first_approver)

        first_response = self.client.post(self.approve_url, {}, format='json')

        self.assertEqual(first_response.status_code, 200)
        self.assertIn('waiting for 1 more approver', first_response.data['message'])
        self.approval.refresh_from_db()
        self.assertEqual(self.approval.status, 'pending')
        self.assertEqual(ApprovalAction.objects.filter(request=self.approval).count(), 1)
        first_pending = self.client.get('/api/approvals/requests/pending_for_me/')
        self.assertEqual(first_pending.status_code, 200)
        self.assertEqual(first_pending.data, [])

        duplicate_response = self.client.post(self.approve_url, {}, format='json')
        self.assertEqual(duplicate_response.status_code, 409)

        self.client.force_authenticate(second_approver)
        second_pending = self.client.get('/api/approvals/requests/pending_for_me/')
        self.assertEqual(second_pending.status_code, 200)
        self.assertEqual(len(second_pending.data), 1)
        second_response = self.client.post(self.approve_url, {}, format='json')
        self.assertEqual(second_response.status_code, 200)
        self.approval.refresh_from_db()
        self.invoice.refresh_from_db()
        self.assertEqual(self.approval.status, 'approved')
        self.assertEqual(self.invoice.status, 'approved')

    def test_rejection_requires_a_reason(self):
        approver = User.objects.create_user(username='reject-approver', password='test-password', role='approver')
        self.client.force_authenticate(approver)

        response = self.client.post(self.reject_url, {'comments': '   '}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertFalse(ApprovalAction.objects.filter(request=self.approval).exists())
        self.approval.refresh_from_db()
        self.assertEqual(self.approval.status, 'pending')


class ApprovalSubmissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='submitter', password='test-password', role='clerk')
        self.vendor = Vendor.objects.create(name='Submission Test Vendor', onboarding_status='approved')
        self.invoice = Invoice.objects.create(
            invoice_number='AP-TEST-1002',
            vendor=self.vendor,
            invoice_date=date(2026, 1, 1),
            total_amount=Decimal('250.00'),
            status='validated',
            original_file='test-invoice.pdf',
        )
        self.client.force_authenticate(self.user)

    def test_submission_requires_an_active_matrix(self):
        response = self.client.post(
            f'/api/invoices/{self.invoice.pk}/submit_for_approval/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(ApprovalRequest.objects.filter(invoice=self.invoice).exists())
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'validated')

    def test_submission_starts_at_first_configured_step(self):
        matrix = ApprovalMatrix.objects.create(
            name='Non-one-based steps',
            min_amount=Decimal('0.00'),
            max_amount=None,
        )
        ApprovalStep.objects.create(matrix=matrix, step_order=4, approver_role='approver')
        ApprovalStep.objects.create(matrix=matrix, step_order=9, approver_role='admin')

        response = self.client.post(
            f'/api/invoices/{self.invoice.pk}/submit_for_approval/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        approval = ApprovalRequest.objects.get(invoice=self.invoice)
        self.assertEqual(approval.current_step, 4)
        self.assertEqual(approval.status, 'pending')
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'pending_approval')
        self.assertTrue(AuditLog.objects.filter(
            entity_type='invoice',
            entity_id=self.invoice.pk,
            action='submit_for_approval',
        ).exists())
