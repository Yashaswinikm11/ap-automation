from django.db import models
from core.models import TimeStampedModel
from invoices.models import Invoice


class ApprovalMatrix(TimeStampedModel):
    name = models.CharField(max_length=100)
    min_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    max_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ApprovalStep(TimeStampedModel):
    matrix = models.ForeignKey(ApprovalMatrix, on_delete=models.CASCADE, related_name='steps')
    step_order = models.PositiveIntegerField()
    approver_role = models.CharField(max_length=50)
    is_parallel = models.BooleanField(default=False)

    class Meta:
        ordering = ['matrix', 'step_order']
        unique_together = ('matrix', 'step_order')


class ApprovalRequest(TimeStampedModel):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    invoice = models.OneToOneField(Invoice, on_delete=models.CASCADE, related_name='approval_request')
    matrix = models.ForeignKey(ApprovalMatrix, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    current_step = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"Approval for {self.invoice}"


class ApprovalAction(TimeStampedModel):
    DECISION_CHOICES = [('approve', 'Approve'), ('reject', 'Reject')]
    request = models.ForeignKey(ApprovalRequest, on_delete=models.CASCADE, related_name='actions')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    decision = models.CharField(max_length=10, choices=DECISION_CHOICES)
    comments = models.TextField(blank=True)