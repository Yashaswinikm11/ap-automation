from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from invoices.models import Invoice
from payments.models import PaymentRequest
from reports.models import AuditLog
from vendors.models import Vendor

User = get_user_model()


class PaymentWorkflowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='payment-clerk', password='test-password', role='clerk')
        self.vendor = Vendor.objects.create(name='Payment Test Vendor', onboarding_status='approved')
        self.invoice = Invoice.objects.create(
            invoice_number='AP-PAY-1001',
            vendor=self.vendor,
            invoice_date=date(2026, 1, 1),
            total_amount=Decimal('125.50'),
            status='approved',
            original_file='payment-test-invoice.pdf',
        )
        self.client.force_authenticate(self.user)
        self.requests_url = '/api/payments/requests/'

    def create_payment(self):
        return self.client.post(
            self.requests_url,
            {
                'invoice': self.invoice.pk,
                'amount': '125.50',
                'payment_method': 'bank_transfer',
            },
            format='json',
        )

    def test_payment_request_requires_approved_invoice_and_matching_amount(self):
        self.invoice.status = 'validated'
        self.invoice.save(update_fields=['status', 'updated_at'])

        response = self.create_payment()

        self.assertEqual(response.status_code, 400)
        self.assertFalse(PaymentRequest.objects.exists())

    def test_payment_request_amount_must_match_invoice_total(self):
        response = self.client.post(
            self.requests_url,
            {
                'invoice': self.invoice.pk,
                'amount': '100.00',
                'payment_method': 'bank_transfer',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(PaymentRequest.objects.exists())

    def test_payment_request_and_paid_action_update_and_audit_records(self):
        created = self.create_payment()

        self.assertEqual(created.status_code, 201)
        payment = PaymentRequest.objects.get(invoice=self.invoice)
        self.assertTrue(AuditLog.objects.filter(entity_type='payment', entity_id=payment.pk, action='create').exists())
        duplicate = self.create_payment()
        self.assertEqual(duplicate.status_code, 400)

        paid = self.client.post(
            f'{self.requests_url}{payment.pk}/mark_paid/',
            {'reference': 'UTR-TEST-01', 'bank_reference': 'BANK-REF-01'},
            format='json',
        )

        self.assertEqual(paid.status_code, 200)
        payment.refresh_from_db()
        self.invoice.refresh_from_db()
        self.assertEqual(payment.status, 'paid')
        self.assertEqual(self.invoice.status, 'paid')
        self.assertTrue(AuditLog.objects.filter(entity_type='payment', entity_id=payment.pk, action='mark_paid').exists())

        repeated = self.client.post(f'{self.requests_url}{payment.pk}/mark_paid/', {}, format='json')
        self.assertEqual(repeated.status_code, 400)
