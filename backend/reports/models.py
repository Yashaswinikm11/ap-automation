from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=50, help_text="e.g. invoice, vendor, payment")
    entity_id = models.IntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    ip_address = models.CharField(max_length=45, blank=True)
    extra_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        user_str = self.user.username if self.user else 'System'
        return f"[{self.created_at.strftime('%Y-%m-%d %H:%M')}] {user_str}: {self.action} on {self.entity_type} #{self.entity_id}"
