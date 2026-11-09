from django.db import models
from django.conf import settings
from core.models import TimeStampedModel
from invoices.models import Invoice


class ApprovalMatrix(TimeStampedModel):
    name = models.CharField(max_length=100)
    min_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    max_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['min_amount']

    def __str__(self):
        max_str = str(self.max_amount) if self.max_amount is not None else 'Unlimited'
        return f"{self.name} ({self.min_amount} - {max_str})"


class ApprovalStep(TimeStampedModel):
    matrix = models.ForeignKey(ApprovalMatrix, on_delete=models.CASCADE, related_name='steps')
    step_order = models.PositiveIntegerField()
    approver_role = models.CharField(max_length=50)
    is_parallel = models.BooleanField(default=False)
    escalate_after_days = models.PositiveIntegerField(default=3)

    class Meta:
        ordering = ['matrix', 'step_order']
        unique_together = ('matrix', 'step_order')

    def __str__(self):
        return f"{self.matrix.name} - Step {self.step_order} ({self.approver_role})"


class ApprovalRequest(TimeStampedModel):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    invoice = models.OneToOneField(Invoice, on_delete=models.CASCADE, related_name='approval_request')
    matrix = models.ForeignKey(
        ApprovalMatrix,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approval_requests'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    current_step = models.PositiveIntegerField(default=1)
    submitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submitted_approvals'
    )

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"Approval for Invoice #{self.invoice_id} ({self.status})"


class ApprovalAction(TimeStampedModel):
    DECISION_CHOICES = [
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('escalate', 'Escalate'),
    ]

    request = models.ForeignKey(ApprovalRequest, on_delete=models.CASCADE, related_name='actions')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approval_actions'
    )
    decision = models.CharField(max_length=15, choices=DECISION_CHOICES)
    comments = models.TextField(blank=True)
    step_number = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        user_name = self.user.username if self.user else 'System'
        return f"{user_name} - {self.decision} (Step {self.step_number})"
