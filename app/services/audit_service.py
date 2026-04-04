from app.models import AuditLog


def log_action(session, action: str, entity_type: str, entity_id=None, admin_id=None, details=None, actor_type="admin", ip_address=None):
    session.add(
        AuditLog(
            admin_id=admin_id,
            actor_type=actor_type,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address,
        )
    )
