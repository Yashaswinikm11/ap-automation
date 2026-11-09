import base64
import binascii
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_datetime

from invoices.models import EmailIngestion, Invoice
from reports.models import AuditLog


GRAPH_ROOT = 'https://graph.microsoft.com/v1.0'
TOKEN_SCOPE = 'https://graph.microsoft.com/.default'
MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024
ALLOWED_MIME_TYPES = {
    '.pdf': {'application/pdf'},
    '.jpg': {'image/jpeg'},
    '.jpeg': {'image/jpeg'},
    '.png': {'image/png'},
    '.tif': {'image/tiff'},
    '.tiff': {'image/tiff'},
}


class Command(BaseCommand):
    help = 'Import unread invoice attachments from a Microsoft Outlook mailbox using Microsoft Graph.'

    def add_arguments(self, parser):
        parser.add_argument('--max-messages', type=int, default=25)

    def handle(self, *args, **options):
        if options['max_messages'] < 1:
            raise CommandError('--max-messages must be greater than zero.')

        config = {
            'tenant_id': os.environ.get('OUTLOOK_GRAPH_TENANT_ID'),
            'client_id': os.environ.get('OUTLOOK_GRAPH_CLIENT_ID'),
            'client_secret': os.environ.get('OUTLOOK_GRAPH_CLIENT_SECRET'),
            'mailbox': os.environ.get('OUTLOOK_GRAPH_MAILBOX'),
            'folder': os.environ.get('OUTLOOK_GRAPH_FOLDER', 'inbox'),
        }
        missing = [key for key, value in config.items() if key != 'folder' and not value]
        if missing:
            variable_names = {
                'tenant_id': 'OUTLOOK_GRAPH_TENANT_ID',
                'client_id': 'OUTLOOK_GRAPH_CLIENT_ID',
                'client_secret': 'OUTLOOK_GRAPH_CLIENT_SECRET',
                'mailbox': 'OUTLOOK_GRAPH_MAILBOX',
            }
            raise CommandError(
                'Missing Outlook Graph configuration: '
                + ', '.join(variable_names[key] for key in missing)
            )

        token = self._get_access_token(config)
        messages = self._get_unread_messages(token, config, options['max_messages'])
        imported = 0
        ignored = 0
        failed = 0

        for message in messages:
            try:
                status_value = self._process_message(message, token, config)
                imported += status_value == 'processed'
                ignored += status_value == 'ignored'
            except Exception as error:
                failed += 1
                self.stderr.write(self.style.ERROR(
                    f"Failed to ingest Outlook message {message.get('id', '<unknown>')}: {error}"
                ))

        self.stdout.write(
            self.style.SUCCESS(
                f'Outlook ingestion finished: {imported} message(s) processed, '
                f'{ignored} ignored, {failed} failed.'
            )
        )
        if failed:
            raise CommandError(f'{failed} Outlook message(s) could not be processed; see errors above.')

    def _get_access_token(self, config):
        token_url = (
            f"https://login.microsoftonline.com/{quote(config['tenant_id'], safe='')}"
            '/oauth2/v2.0/token'
        )
        body = urlencode({
            'client_id': config['client_id'],
            'client_secret': config['client_secret'],
            'scope': TOKEN_SCOPE,
            'grant_type': 'client_credentials',
        }).encode('utf-8')
        request = Request(
            token_url,
            data=body,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            method='POST',
        )
        try:
            with urlopen(request, timeout=30) as response:
                token_data = json.loads(response.read().decode('utf-8'))
        except HTTPError as error:
            details = error.read().decode('utf-8', errors='replace')[:500]
            raise CommandError(f'Microsoft identity token request failed ({error.code}): {details}') from error
        except URLError as error:
            raise CommandError(f'Could not connect to Microsoft identity service: {error.reason}') from error
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise CommandError('Microsoft identity service returned an invalid response.') from error

        access_token = token_data.get('access_token')
        if not access_token:
            raise CommandError('Microsoft identity response did not contain an access token.')
        return access_token

    def _graph_request(self, token, url, method='GET', payload=None):
        body = json.dumps(payload).encode('utf-8') if payload is not None else None
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
        }
        if body is not None:
            headers['Content-Type'] = 'application/json'
        request = Request(url, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=60) as response:
                response_body = response.read()
        except HTTPError as error:
            details = error.read().decode('utf-8', errors='replace')[:500]
            raise CommandError(f'Microsoft Graph request failed ({error.code}): {details}') from error
        except URLError as error:
            raise CommandError(f'Could not connect to Microsoft Graph: {error.reason}') from error

        if not response_body:
            return {}
        try:
            return json.loads(response_body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise CommandError('Microsoft Graph returned an invalid response.') from error

    def _get_unread_messages(self, token, config, limit):
        mailbox = quote(config['mailbox'], safe='')
        folder = quote(config['folder'], safe='')
        query = urlencode({
            '$filter': 'isRead eq false and hasAttachments eq true',
            '$select': 'id,subject,from,receivedDateTime',
            '$expand': 'attachments($select=id,name,contentType,size,isInline,contentBytes)',
            '$top': min(limit, 25),
        })
        next_url = (
            f'{GRAPH_ROOT}/users/{mailbox}/mailFolders/{folder}/messages?{query}'
        )
        messages = []
        while next_url and len(messages) < limit:
            page = self._graph_request(token, next_url)
            remaining = limit - len(messages)
            messages.extend(page.get('value', [])[:remaining])
            next_url = page.get('@odata.nextLink')
        return messages

    def _process_message(self, message, token, config):
        message_id = message.get('id')
        if not message_id:
            raise CommandError('Message response did not include an ID.')

        mailbox = config['mailbox']
        ingestion, created = EmailIngestion.objects.get_or_create(
            mailbox=mailbox,
            message_id=message_id,
            defaults={
                'subject': message.get('subject', '') or '',
                'sender': (
                    message.get('from', {}).get('emailAddress', {}).get('address', '') or ''
                ),
                'received_at': parse_datetime(message.get('receivedDateTime', '') or ''),
                'status': 'processing',
            },
        )
        if not created and ingestion.status in {'processed', 'ignored'}:
            self._mark_message_read(token, mailbox, message_id)
            return ingestion.status

        imported_count = 0
        errors = []
        sender = ingestion.sender
        safe_mailbox = mailbox.replace('\r', ' ').replace('\n', ' ')
        notes = f'Imported from Outlook mailbox {safe_mailbox}; message ID {message_id}.'

        try:
            with transaction.atomic():
                ingestion.subject = message.get('subject', '') or ''
                ingestion.sender = sender
                ingestion.received_at = parse_datetime(message.get('receivedDateTime', '') or '')
                ingestion.status = 'processing'
                ingestion.error_message = ''
                ingestion.save()

                for attachment in message.get('attachments', []):
                    if attachment.get('@odata.type') != '#microsoft.graph.fileAttachment':
                        continue
                    if attachment.get('isInline'):
                        continue

                    file_bytes, filename, validation_error = self._decode_attachment(attachment)
                    if validation_error:
                        errors.append(validation_error)
                        continue

                    invoice = Invoice.objects.create(
                        original_file=ContentFile(file_bytes, name=filename),
                        notes=notes,
                        status='uploaded',
                    )
                    ingestion.invoices.add(invoice)
                    imported_count += 1
                    AuditLog.objects.create(
                        action='email_ingest',
                        entity_type='invoice',
                        entity_id=invoice.pk,
                        description=f'Invoice imported from Outlook attachment {filename}.',
                        extra_data={
                            'mailbox': mailbox,
                            'message_id': message_id,
                            'email_ingestion_id': ingestion.pk,
                        },
                    )

                ingestion.status = 'processed' if imported_count else 'ignored'
                ingestion.error_message = '; '.join(errors)
                ingestion.save(update_fields=['status', 'error_message', 'updated_at'])
        except Exception as error:
            ingestion.status = 'failed'
            ingestion.error_message = str(error)[:2000]
            ingestion.save(update_fields=['status', 'error_message', 'updated_at'])
            raise

        self._mark_message_read(token, mailbox, message_id)
        if errors:
            self.stderr.write(self.style.WARNING(
                f'Outlook message {message_id}: ' + '; '.join(errors)
            ))
        self.stdout.write(f'Outlook message {message_id}: {imported_count} invoice attachment(s) imported.')
        return ingestion.status

    def _decode_attachment(self, attachment):
        filename = os.path.basename((attachment.get('name') or '').replace('\\', '/'))
        extension = os.path.splitext(filename)[1].lower()
        if not filename or extension not in ALLOWED_MIME_TYPES:
            return None, None, f"Unsupported attachment type: {attachment.get('name', '<unnamed>')}."

        content_type = (attachment.get('contentType') or '').split(';', 1)[0].strip().lower()
        if content_type and content_type not in ALLOWED_MIME_TYPES[extension]:
            return None, None, f'Attachment content type does not match {filename}.'
        if attachment.get('size', 0) > MAX_ATTACHMENT_BYTES:
            return None, None, f'Attachment exceeds the 25 MB limit: {filename}.'

        encoded_content = attachment.get('contentBytes')
        if not encoded_content:
            return None, None, f'Attachment content was not available: {filename}.'
        try:
            file_bytes = base64.b64decode(encoded_content, validate=True)
        except (binascii.Error, ValueError):
            return None, None, f'Attachment content was invalid base64: {filename}.'
        if len(file_bytes) > MAX_ATTACHMENT_BYTES:
            return None, None, f'Attachment exceeds the 25 MB limit: {filename}.'
        return file_bytes, filename, None

    def _mark_message_read(self, token, mailbox, message_id):
        encoded_mailbox = quote(mailbox, safe='')
        encoded_message_id = quote(message_id, safe='')
        self._graph_request(
            token,
            f'{GRAPH_ROOT}/users/{encoded_mailbox}/messages/{encoded_message_id}',
            method='PATCH',
            payload={'isRead': True},
        )
