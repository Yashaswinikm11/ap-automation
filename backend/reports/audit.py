from .models import AuditLog


def write_audit_log(request, *, action, entity_type, entity_id=None, description='', extra_data=None):
    user = request.user if request.user.is_authenticated else None
    return AuditLog.objects.create(
        user=user,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        ip_address=request.META.get('REMOTE_ADDR', ''),
        extra_data=extra_data or {},
    )