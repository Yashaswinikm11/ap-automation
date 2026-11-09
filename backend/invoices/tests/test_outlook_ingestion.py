import base64
import os
import tempfile
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from invoices.management.commands.ingest_outlook_invoices import Command
from invoices.models import EmailIngestion, Invoice
from reports.models import AuditLog


class OutlookInvoiceIngestionTests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.media_dir.cleanup)
        self.settings_override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.config = {
            'OUTLOOK_GRAPH_TENANT_ID': 'tenant-id',
            'OUTLOOK_GRAPH_CLIENT_ID': 'client-id',
            'OUTLOOK_GRAPH_CLIENT_SECRET': 'test-secret',
            'OUTLOOK_GRAPH_MAILBOX': 'ap@example.com',
        }
        self.message = {
            'id': 'graph-message-1',
            'subject': 'Invoice 1001',
            'from': {'emailAddress': {'address': 'vendor@example.com'}},
            'receivedDateTime': '2026-01-15T10:00:00Z',
            'attachments': [{
                '@odata.type': '#microsoft.graph.fileAttachment',
                'name': 'invoice.pdf',
                'contentType': 'application/pdf',
                'size': 8,
                'contentBytes': base64.b64encode(b'%PDF-1.4').decode('ascii'),
            }],
        }

    def run_ingestion(self, messages):
        error_output = StringIO()
        with patch.dict(os.environ, self.config):
            with patch.object(Command, '_get_access_token', return_value='test-token'), \
                    patch.object(Command, '_get_unread_messages', return_value=messages), \
                    patch.object(Command, '_mark_message_read') as mark_read, \
                    patch('invoices.ocr_service.extract_text_from_file', return_value=''), \
                    patch('invoices.ocr_service.parse_invoice_fields', return_value={}):
                try:
                    call_command('ingest_outlook_invoices', stdout=StringIO(), stderr=error_output)
                except Exception as error:
                    self.fail(f'{error_output.getvalue()}{error}')
        return mark_read

    def test_imports_supported_attachment_and_is_idempotent(self):
        first_mark_read = self.run_ingestion([self.message])

        self.assertEqual(Invoice.objects.count(), 1)
        ingestion = EmailIngestion.objects.get(mailbox='ap@example.com', message_id='graph-message-1')
        self.assertEqual(ingestion.status, 'processed')
        self.assertEqual(ingestion.invoices.count(), 1)
        self.assertTrue(AuditLog.objects.filter(action='email_ingest', entity_type='invoice').exists())
        first_mark_read.assert_called_once()

        second_mark_read = self.run_ingestion([self.message])

        self.assertEqual(Invoice.objects.count(), 1)
        self.assertEqual(EmailIngestion.objects.count(), 1)
        second_mark_read.assert_called_once()

    def test_unsupported_attachments_are_recorded_and_not_imported(self):
        unsupported_message = {
            **self.message,
            'id': 'graph-message-2',
            'attachments': [{
                '@odata.type': '#microsoft.graph.fileAttachment',
                'name': 'invoice.exe',
                'contentType': 'application/octet-stream',
                'size': 8,
                'contentBytes': base64.b64encode(b'not an invoice').decode('ascii'),
            }],
        }

        self.run_ingestion([unsupported_message])

        ingestion = EmailIngestion.objects.get(message_id='graph-message-2')
        self.assertEqual(ingestion.status, 'ignored')
        self.assertIn('Unsupported attachment type', ingestion.error_message)
        self.assertFalse(Invoice.objects.exists())
