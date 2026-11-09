"""
Management command: seed_sample_data
Creates realistic sample invoices, POs, approval requests, and payment data
so the dashboard and reports show meaningful data.
"""
import random
import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


INVOICE_NUMBERS = [
    'INV-TCS-2026-001', 'INV-TCS-2026-002', 'INV-TCS-2026-003',
    'INV-INF-2026-001', 'INV-INF-2026-002',
    'INV-WIP-2026-001', 'INV-WIP-2026-002', 'INV-WIP-2026-003',
    'INV-HCL-2026-001',
    'INV-TCS-2025-091', 'INV-TCS-2025-092', 'INV-INF-2025-045',
    'INV-WIP-2025-078', 'INV-WIP-2025-079',
]

PO_NUMBERS = [
    'PO-2026-IT-0001', 'PO-2026-IT-0002', 'PO-2026-OPS-0001',
    'PO-2026-OPS-0002', 'PO-2025-IT-0045',
]


class Command(BaseCommand):
    help = 'Seeds realistic sample invoices, POs, payments, and approvals for demo.'

    def handle(self, *args, **options):
        self.stdout.write('\n=== AP Automation Sample Data Seeder ===\n')

        try:
            from vendors.models import Vendor
            from invoices.models import Invoice, PurchaseOrder, InvoiceLineItem
            from approvals.models import ApprovalMatrix, ApprovalRequest
            from payments.models import PaymentRequest

            vendors = list(Vendor.objects.filter(is_active=True))
            if not vendors:
                self.stdout.write(self.style.ERROR('No vendors found. Run seed_demo_data first.'))
                return

            admin_user = User.objects.filter(is_superuser=True).first()
            clerk_user = User.objects.filter(role='clerk').first() or admin_user

            # 1. Create Purchase Orders
            self.stdout.write('Creating Purchase Orders...')
            pos = []
            for i, po_num in enumerate(PO_NUMBERS):
                vendor = vendors[i % len(vendors)]
                po, created = PurchaseOrder.objects.get_or_create(
                    po_number=po_num,
                    defaults={
                        'vendor': vendor,
                        'status': 'open',
                        'po_date': datetime.date(2026, 1, min(28, 10 + i * 4)),
                        'total_amount': Decimal(str(random.randint(100000, 2000000))),
                        'currency': 'INR',
                        'description': f'IT Services and Consulting - Q1 2026 - {vendor.name}',
                    }
                )
                pos.append(po)
                status_sym = 'Created' if created else 'Exists'
                self.stdout.write(f'  [{status_sym}]: {po.po_number}')

            # 2. Create Invoices
            self.stdout.write('\nCreating Invoices...')
            invoice_statuses = [
                'uploaded', 'uploaded', 'extracted', 'extracted', 'extracted',
                'validated', 'validated',
                'pending_approval', 'pending_approval', 'pending_approval',
                'approved', 'approved', 'approved',
                'paid',
            ]

            line_item_data = [
                ('Cloud Infrastructure Services - Monthly Subscription', 1, 125000),
                ('Application Development - Phase 1 Milestone', 1, 350000),
                ('Data Analytics Platform License', 12, 25000),
                ('Security Audit and Penetration Testing', 1, 180000),
                ('SAP ERP Support - Annual Contract', 1, 480000),
                ('Network Infrastructure Upgrade', 1, 275000),
                ('DevOps Consulting Services - 50 days', 50, 15000),
                ('Cybersecurity Training - 25 seats', 25, 8000),
                ('Digital Transformation Advisory', 1, 650000),
                ('Managed IT Support - Q4 2026', 1, 220000),
                ('Mobile App Development - Milestone 2', 1, 390000),
                ('Data Center Migration Services', 1, 520000),
                ('Business Process Outsourcing - 3 months', 3, 145000),
                ('Software Testing and QA', 1, 165000),
            ]

            invoices_created = []
            for i, inv_num in enumerate(INVOICE_NUMBERS):
                if Invoice.objects.filter(invoice_number=inv_num).exists():
                    self.stdout.write(f'  [Exists]: {inv_num}')
                    invoices_created.append(Invoice.objects.get(invoice_number=inv_num))
                    continue

                vendor = vendors[i % len(vendors)]
                po = pos[i % len(pos)] if pos else None
                stat = invoice_statuses[i % len(invoice_statuses)]

                days_ago = random.randint(1, 90)
                inv_date = datetime.date.today() - datetime.timedelta(days=days_ago)
                due_date = inv_date + datetime.timedelta(days=vendor.payment_terms or 30)

                desc, qty, unit_price = line_item_data[i % len(line_item_data)]
                line_total = Decimal(str(qty * unit_price))
                tax = round(line_total * Decimal('0.18'), 2)
                total = line_total + tax

                inv = Invoice.objects.create(
                    invoice_number=inv_num,
                    vendor=vendor,
                    vendor_name=vendor.name,
                    gstin=vendor.gstin or '',
                    purchase_order=po,
                    invoice_date=inv_date,
                    due_date=due_date,
                    total_amount=total,
                    tax_amount=tax,
                    currency='INR',
                    status=stat,
                    uploaded_by=clerk_user,
                    is_duplicate=False,
                    validation_errors=[],
                )

                InvoiceLineItem.objects.create(
                    invoice=inv,
                    description=desc,
                    quantity=Decimal(str(qty)),
                    unit_price=Decimal(str(unit_price)),
                    total=line_total,
                )

                invoices_created.append(inv)
                self.stdout.write(f'  [Created]: {inv.invoice_number} - INR {total:,.2f} ({stat})')

            # 3. Create Approval Requests for pending/approved invoices
            self.stdout.write('\nCreating Approval Requests...')
            matrix = ApprovalMatrix.objects.filter(is_active=True).first()
            if matrix:
                approval_invoices = Invoice.objects.filter(
                    status__in=['pending_approval', 'approved']
                )
                for inv in approval_invoices:
                    req, created = ApprovalRequest.objects.get_or_create(
                        invoice=inv,
                        defaults={
                            'matrix': matrix,
                            'status': 'pending' if inv.status == 'pending_approval' else 'approved',
                            'current_step': 1,
                            'submitted_by': clerk_user,
                            'submitted_at': timezone.now() - datetime.timedelta(days=random.randint(1, 10)),
                            'completed_at': timezone.now() - datetime.timedelta(days=random.randint(0, 5)) if inv.status == 'approved' else None,
                        }
                    )
                    if created:
                        self.stdout.write(f'  [Created] Approval for: {inv.invoice_number}')

            # 4. Create Payment Requests for paid invoices
            self.stdout.write('\nCreating Payment Requests...')
            paid_invoices = Invoice.objects.filter(status='paid')
            for inv in paid_invoices:
                PaymentRequest.objects.get_or_create(
                    invoice=inv,
                    defaults={
                        'amount': inv.total_amount,
                        'status': 'paid',
                        'payment_method': 'bank_transfer',
                        'due_date': inv.due_date or datetime.date.today(),
                        'paid_at': timezone.now() - datetime.timedelta(days=random.randint(1, 15)),
                        'initiated_by': admin_user,
                        'notes': f'Payment for invoice {inv.invoice_number}',
                    }
                )
                self.stdout.write(f'  [Payment] Paid: {inv.invoice_number}')

            # 5. Create pending payment requests for approved invoices
            approved_invoices = Invoice.objects.filter(status='approved')
            for inv in approved_invoices:
                PaymentRequest.objects.get_or_create(
                    invoice=inv,
                    defaults={
                        'amount': inv.total_amount,
                        'status': 'pending',
                        'payment_method': 'bank_transfer',
                        'due_date': inv.due_date or datetime.date.today() + datetime.timedelta(days=15),
                    }
                )

            self.stdout.write(self.style.SUCCESS('\n=== Sample Data Seeding Complete ==='))
            self.stdout.write(f'Invoices: {Invoice.objects.count()}')
            self.stdout.write(f'POs: {PurchaseOrder.objects.count()}')
            self.stdout.write(f'Approval Requests: {ApprovalRequest.objects.count()}')
            self.stdout.write(f'Payment Requests: {PaymentRequest.objects.count()}')

        except Exception as e:
            import traceback
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
            self.stdout.write(traceback.format_exc())
