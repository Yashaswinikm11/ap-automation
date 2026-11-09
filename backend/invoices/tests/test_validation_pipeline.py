from datetime import date
from decimal import Decimal

from django.test import TestCase

from invoices.models import Invoice
from invoices.validation import run_validation_pipeline
from vendors.models import Vendor


class InvoiceValidationTests(TestCase):
    def setUp(self):
        self.vendor = Vendor.objects.create(
            name='Validation Test Vendor',
            onboarding_status='approved',
        )

    def make_invoice(self, **overrides):
        values = {
            'invoice_number': 'AP-VALID-1001',
            'vendor': self.vendor,
            'invoice_date': date(2026, 1, 15),
            'total_amount': Decimal('118.00'),
            'tax_amount': Decimal('18.00'),
            'status': 'uploaded',
            'original_file': 'validation-test-invoice.pdf',
        }
        values.update(overrides)
        return Invoice.objects.create(**values)

    def test_tax_cannot_be_negative_or_exceed_the_invoice_total(self):
        negative_tax_invoice = self.make_invoice(tax_amount=Decimal('-1.00'))
        negative_tax_result = run_validation_pipeline(negative_tax_invoice)
        self.assertFalse(negative_tax_result['passed'])
        self.assertIn('Tax amount cannot be negative.', negative_tax_result['errors'])

        excessive_tax_invoice = self.make_invoice(
            invoice_number='AP-VALID-1002',
            tax_amount=Decimal('119.00'),
        )
        excessive_tax_result = run_validation_pipeline(excessive_tax_invoice)
        self.assertFalse(excessive_tax_result['passed'])
        self.assertIn('Tax amount cannot exceed the invoice total.', excessive_tax_result['errors'])

    def test_valid_invoice_advances_to_validated_status(self):
        invoice = self.make_invoice()

        result = run_validation_pipeline(invoice)

        self.assertTrue(result['passed'])
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, 'validated')
