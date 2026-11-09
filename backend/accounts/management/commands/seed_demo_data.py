"""
Management command: seed_demo_data

Creates demo users (admin, approver, clerk) and sample master data
(vendors, approval matrix) so the app works out of the box without
any manual setup.

Usage:
    python manage.py seed_demo_data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


DEMO_USERS = [
    {
        'username': 'admin',
        'password': 'admin123',
        'email': 'admin@apautomation.com',
        'first_name': 'Admin',
        'last_name': 'User',
        'role': 'admin',
        'department': 'Finance',
        'is_staff': True,
        'is_superuser': True,
    },
    {
        'username': 'clerk1',
        'password': 'clerk123',
        'email': 'clerk@apautomation.com',
        'first_name': 'John',
        'last_name': 'Clerk',
        'role': 'clerk',
        'department': 'Accounts Payable',
        'is_staff': False,
        'is_superuser': False,
    },
    {
        'username': 'approver1',
        'password': 'approver123',
        'email': 'approver@apautomation.com',
        'first_name': 'Sarah',
        'last_name': 'Manager',
        'role': 'approver',
        'department': 'Finance',
        'is_staff': False,
        'is_superuser': False,
    },
    {
        'username': 'viewer1',
        'password': 'viewer123',
        'email': 'viewer@apautomation.com',
        'first_name': 'View',
        'last_name': 'Only',
        'role': 'viewer',
        'department': 'Audit',
        'is_staff': False,
        'is_superuser': False,
    },
]


class Command(BaseCommand):
    help = 'Seeds the database with demo users, vendors, and approval matrix for local development'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== AP Automation Demo Data Seeder ===\n'))

        # ── 1. Demo Users ──────────────────────────────────────────────────────
        self.stdout.write('Creating demo users...')
        for u in DEMO_USERS:
            is_staff = u.pop('is_staff')
            is_superuser = u.pop('is_superuser')
            password = u.pop('password')

            user, created = User.objects.get_or_create(
                username=u['username'],
                defaults={**u, 'is_staff': is_staff, 'is_superuser': is_superuser},
            )
            if created:
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ Created user: {user.username} (password: {password})"
                ))
            else:
                # Ensure password is set even for existing users
                user.set_password(password)
                user.is_staff = is_staff
                user.is_superuser = is_superuser
                user.save()
                self.stdout.write(f"  → User exists, password reset: {user.username} (password: {password})")

        # ── 2. Sample Vendors ──────────────────────────────────────────────────
        self.stdout.write('\nCreating sample vendors...')
        try:
            from vendors.models import Vendor
            sample_vendors = [
                {
                    'name': 'Tata Consultancy Services Ltd',
                    'gstin': '27AAACT2727Q1Z6',
                    'pan_number': 'AAACT2727Q',
                    'email': 'billing@tcs.com',
                    'phone': '+91-22-6778-9999',
                    'address': 'TCS House, Raveline Street, Fort, Mumbai 400001',
                    'bank_account': '1234567890',
                    'bank_ifsc': 'HDFC0001234',
                    'bank_name': 'HDFC Bank',
                    'bank_branch': 'Fort Branch, Mumbai',
                    'payment_terms': 30,
                    'onboarding_status': 'approved',
                    'is_active': True,
                },
                {
                    'name': 'Infosys Limited',
                    'gstin': '29AABCI1681G1ZJ',
                    'pan_number': 'AABCI1681G',
                    'email': 'accounts@infosys.com',
                    'phone': '+91-80-2852-0261',
                    'address': 'Electronics City, Hosur Road, Bengaluru 560100',
                    'bank_account': '9876543210',
                    'bank_ifsc': 'ICIC0009876',
                    'bank_name': 'ICICI Bank',
                    'bank_branch': 'Koramangala Branch, Bengaluru',
                    'payment_terms': 45,
                    'onboarding_status': 'approved',
                    'is_active': True,
                },
                {
                    'name': 'Wipro Technologies',
                    'gstin': '29AAACW0638G1ZK',
                    'pan_number': 'AAACW0638G',
                    'email': 'finance@wipro.com',
                    'phone': '+91-80-2844-0011',
                    'address': 'Doddakannelli, Sarjapur Road, Bengaluru 560035',
                    'bank_account': '1122334455',
                    'bank_ifsc': 'SBIN0012345',
                    'bank_name': 'State Bank of India',
                    'bank_branch': 'Sarjapur Branch',
                    'payment_terms': 60,
                    'onboarding_status': 'approved',
                    'is_active': True,
                },
                {
                    'name': 'HCL Technologies',
                    'gstin': '09AAACH6481H1ZG',
                    'pan_number': 'AAACH6481H',
                    'email': 'billing@hcl.com',
                    'phone': '+91-120-476-4000',
                    'address': 'Plot No. 3A, Sector 126, Noida 201301',
                    'bank_account': '5544332211',
                    'bank_ifsc': 'AXIS0005544',
                    'bank_name': 'Axis Bank',
                    'bank_branch': 'Noida Sector 18 Branch',
                    'payment_terms': 30,
                    'onboarding_status': 'pending',
                    'is_active': True,
                },
            ]
            for v in sample_vendors:
                vendor, created = Vendor.objects.get_or_create(
                    name=v['name'], defaults=v
                )
                status = '✓ Created' if created else '→ Exists'
                self.stdout.write(f"  {status}: {vendor.name}")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  Vendor seeding skipped: {e}'))

        # ── 3. Approval Matrix ─────────────────────────────────────────────────
        self.stdout.write('\nCreating approval matrix...')
        try:
            from approvals.models import ApprovalMatrix, ApprovalStep
            matrices = [
                {'name': 'Small Invoice (< ₹50,000)', 'min_amount': 0, 'max_amount': 49999.99},
                {'name': 'Medium Invoice (₹50K–₹5L)', 'min_amount': 50000, 'max_amount': 499999.99},
                {'name': 'Large Invoice (> ₹5L)', 'min_amount': 500000, 'max_amount': None},
            ]
            roles = [
                {'min': 0,       'max': 49999.99,  'steps': [('approver', 1)]},
                {'min': 50000,   'max': 499999.99, 'steps': [('approver', 1), ('admin', 2)]},
                {'min': 500000,  'max': None,      'steps': [('approver', 1), ('admin', 2)]},
            ]
            for m, r in zip(matrices, roles):
                matrix, created = ApprovalMatrix.objects.get_or_create(
                    name=m['name'],
                    defaults={
                        'min_amount': m['min_amount'],
                        'max_amount': m['max_amount'],
                        'is_active': True,
                    }
                )
                status = '✓ Created' if created else '→ Exists'
                self.stdout.write(f"  {status}: {matrix.name}")
                for role, order in r['steps']:
                    ApprovalStep.objects.get_or_create(
                        matrix=matrix, step_order=order,
                        defaults={'approver_role': role, 'escalate_after_days': 3}
                    )
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  Approval matrix seeding skipped: {e}'))

        # ── Summary ────────────────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS('\n=== Seeding Complete ==='))
        self.stdout.write('\nDemo login credentials:')
        self.stdout.write(self.style.SUCCESS('  Admin    → username: admin      password: admin123'))
        self.stdout.write(self.style.SUCCESS('  Clerk    → username: clerk1     password: clerk123'))
        self.stdout.write(self.style.SUCCESS('  Approver → username: approver1  password: approver123'))
        self.stdout.write(self.style.SUCCESS('  Viewer   → username: viewer1    password: viewer123'))
        self.stdout.write('')
