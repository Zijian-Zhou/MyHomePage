"""Audit trail helpers.

``record()`` is the single entry point used by signals, middleware, admin views and
Celery tasks. It never raises: failing to write an audit row must not break the
operation being audited.

``AuditContextMiddleware`` remembers the current request (client IP, user agent, path,
user) in a context variable so callers that have no request at hand - e.g. the
``LogEntry`` signal fired by the Django admin - still get request details.
"""
import contextvars
import logging
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)

_current_request = contextvars.ContextVar('audit_current_request', default=None)

ACTION_CATEGORY = {
    'login_success': 'login',
    'login_failed': 'login',
    'login_locked': 'login',
    'logout': 'login',
    'object_add': 'operation',
    'object_change': 'operation',
    'object_delete': 'operation',
    'sync': 'operation',
    'backup_create': 'operation',
    'backup_import': 'operation',
    'backup_restore': 'operation',
    'backup_delete': 'operation',
    'audit_export': 'operation',
    'audit_prune': 'system',
    'security_attack': 'security',
    'security_probe': 'security',
    'security_scanner': 'security',
    'security_flood': 'security',
    'security_not_found_burst': 'security',
    'security_suspicious': 'security',
    'security_server_error': 'security',
}


class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = _current_request.set(request)
        try:
            return self.get_response(request)
        finally:
            _current_request.reset(token)


def current_request():
    return _current_request.get()


def _client_ip(request):
    from .middleware import get_client_ip
    ip = (get_client_ip(request) or '').strip()
    return ip or None


def record(action, *, status='success', user=None, username='', object_repr='', message='',
           request=None, category=None):
    """Write one audit row. Request details default to the request being handled."""
    from .models import AuditLog
    try:
        # request=False means "explicitly no request" (background jobs); None means
        # "use the request currently being handled, if any".
        if request is False:
            request = None
        elif request is None:
            request = current_request()
        if user is None and request is not None and not username:
            candidate = getattr(request, 'user', None)
            if candidate is not None and getattr(candidate, 'is_authenticated', False):
                user = candidate
        if user is False:  # explicitly "no user link" (e.g. after a restore)
            user = None
        if user is not None and not username:
            username = user.get_username()
        if user is not None and getattr(user, 'pk', None):
            from django.contrib.auth import get_user_model
            if not get_user_model().objects.filter(pk=user.pk).exists():
                user = None  # e.g. the session user vanished with a database restore
        ip = user_agent = path = ''
        if request is not None:
            ip = _client_ip(request)
            user_agent = (request.META.get('HTTP_USER_AGENT') or '')[:300]
            path = (request.get_full_path() or '')[:300]
        return AuditLog.objects.create(
            category=category or ACTION_CATEGORY.get(action, 'operation'),
            action=action,
            status=status,
            user=user if (user is not None and getattr(user, 'pk', None)) else None,
            username=(username or '')[:150],
            ip_address=ip or None,
            user_agent=user_agent,
            path=path,
            object_repr=(object_repr or '')[:200],
            message=message or '',
        )
    except Exception:
        logger.exception('Failed to write audit log entry (%s).', action)
        return None


def prune(retention_days=None):
    """Delete audit rows older than the configured retention. Returns the count."""
    from .models import AuditLog, SystemConfig
    try:
        days = retention_days or SystemConfig.get_audit_log_retention_days()
        cutoff = timezone.now() - timedelta(days=days)
        deleted, _ = AuditLog.objects.filter(created_at__lt=cutoff).delete()
        if deleted:
            record('audit_prune', category='system', username='system', request=False,
                   message='Removed {} entries older than {} days.'.format(deleted, days))
        return deleted
    except Exception:
        logger.exception('Failed to prune audit log.')
        return 0
