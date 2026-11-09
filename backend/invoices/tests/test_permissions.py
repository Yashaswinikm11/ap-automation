from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from invoices.models import Invoice


class InvoiceActionPermissionTests(TestCase):
    def setUp(self):
        self.invoice = Invoice.objects.create(
            invoice_number='AP-PERMISSION-1001',
            invoice_date=date(2026, 1, 15),
            total_amount=Decimal('118.00'),
            tax_amount=Decimal('18.00'),
            original_file='permission-test-invoice.pdf',
        )
        self.client = APIClient()

    def authenticate_as(self, role):
        user = get_user_model().objects.create_user(
            username=f'{role}-user',
            password='test-password',
            role=role,
        )
        self.client.force_authenticate(user=user)

    def test_clerk_admin_and_approver_can_validate(self):
        for role in ('clerk', 'admin', 'approver'):
            with self.subTest(role=role):
                self.authenticate_as(role)
                response = self.client.post(
                    f'/api/invoices/{self.invoice.pk}/validate/'
                )
                self.assertEqual(response.status_code, 200)

    def test_viewer_cannot_validate(self):
        self.authenticate_as('viewer')

        response = self.client.post(
            f'/api/invoices/{self.invoice.pk}/validate/'
        )

        self.assertEqual(response.status_code, 403)

    def test_approver_cannot_run_ocr(self):
        self.authenticate_as('approver')

        response = self.client.post(
            f'/api/invoices/{self.invoice.pk}/run_ocr/'
        )

        self.assertEqual(response.status_code, 403)
