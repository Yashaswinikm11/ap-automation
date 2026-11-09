from pathlib import Path
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from invoices.models import Invoice
from invoices.ocr_service import parse_invoice_fields
from vendors.models import Vendor


class ParseInvoiceFieldsTests(SimpleTestCase):
    def test_extracts_invoice_number_date_and_indian_currency_total(self):
        fields = parse_invoice_fields(
            'Example Supplier\n'
            'Invoice No: INV-2026/001\n'
            'Invoice Date: 09/11/2026\n'
            'Grand Total: ₹ 12,345.67\n'
        )

        self.assertEqual(fields['invoice_number'], 'INV-2026/001')
        self.assertEqual(fields['invoice_date'], '2026-11-09')
        self.assertEqual(fields['total_amount'], 12345.67)

    def test_does_not_treat_invoice_date_as_the_invoice_number(self):
        fields = parse_invoice_fields(
            'Example Supplier\n'
            'Invoice Date: 2026-11-09\n'
            'Total Amount: INR 500.00\n'
        )

        self.assertNotIn('invoice_number', fields)
        self.assertEqual(fields['invoice_date'], '2026-11-09')
        self.assertEqual(fields['total_amount'], 500.0)


class RunOCRActionTests(TestCase):
    def test_saves_extracted_date_and_links_vendor_by_unique_gstin(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                invoice = Invoice.objects.create(original_file='invoices/ocr-test.pdf')
                file_path = Path(media_root) / invoice.original_file.name
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text('test document', encoding='utf-8')

                gstin = '27ABCDE1234F1Z5'
                vendor = Vendor.objects.create(name='Example Supplier', gstin=gstin)
                user = get_user_model().objects.create_user(
                    username='ocr-clerk',
                    password='test-password',
                    role='clerk',
                )
                client = APIClient()
                client.force_authenticate(user=user)

                with patch(
                    'invoices.views.extract_text_from_file',
                    return_value=(
                        'Example Supplier\n'
                        'Invoice No: INV-2026-001\n'
                        'Invoice Date: 09/11/2026\n'
                        f'GSTIN: {gstin}\n'
                        'Grand Total: ₹ 500.00\n'
                    ),
                ):
                    response = client.post(f'/api/invoices/{invoice.pk}/run_ocr/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['invoice']['invoice_date'], '2026-11-09')
        self.assertEqual(response.data['invoice']['vendor'], vendor.pk)
