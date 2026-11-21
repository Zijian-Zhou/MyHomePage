"""Anomaly / attack-traffic monitor feeding the audit log ("Anomaly" category).

What is recorded (one audit row per event type and source, merged - see below):

* probe          - requests for well-known attack targets (.env, .git, wp-admin, phpMyAdmin,
                   *.php, backups, ...). This site is Django, so none of them exist.
* attack         - attack payloads in the URL / User-Agent / Referer: SQL injection, XSS,
                   path traversal, command injection, Log4Shell, PHP code.
* scanner        - User-Agents of known scanning tools (sqlmap, nikto, nuclei, ...).
* flood          - one IP sending more than SECURITY_FLOOD_PER_MINUTE requests a minute.
* not_found_burst- one IP producing more than SECURITY_404_PER_MINUTE 404s a minute.
* suspicious     - requests Django itself rejects as suspicious (forged Host header,
                   CSRF failure, suspicious file operations), via the django.security logger.
* server_error   - unhandled exceptions (HTTP 500).

Nothing is blocked here; this only records. Signed-in staff are not monitored (admin
pages poll often and may legitimately search for odd strings).

Flood protection for the database itself: repeats of the same event from the same
source within SECURITY_MERGE_SECONDS update one row (hits + last seen) instead of adding
rows, and at most SECURITY_MAX_NEW_ROWS_PER_MINUTE new rows are written per minute.

Counters use Django's cache (per process with the default local-memory cache), so
thresholds are approximate per worker - fine for spotting abuse.
"""
import ipaddress
import logging
import re
import time
from urllib.parse import unquote_plus

from django.conf import settings
from django.core.cache import cache
from django.db.models import F
from django.utils import timezone

logger = logging.getLogger(__name__)


def _setting(name, default):
    return getattr(settings, name, default)


PROBE_RE = re.compile(
    r"(^|/)\.(env|git|svn|hg|bzr|ds_store|aws|ssh|htaccess|htpasswd|vscode|idea|docker)(/|$|\.)"
    r"|(^|/)(wp-admin|wp-login|wp-content|wp-includes|wp-json|xmlrpc\.php|wlwmanifest)"
    r"|(^|/)(phpmyadmin|pma|myadmin|mysqladmin|adminer|phpinfo)"
    r"|\.(php\d?|phtml|asp|aspx|ashx|jsp|jspx|cgi|pl|cfm|action|do)(/|$)"
    r"|(^|/)(cgi-bin|actuator|solr|jenkins|hudson|manager/html|jmx-console|console|_ignition|telescope"
    r"|vendor/phpunit|boaform|hnap1|server-status|server-info|owa|autodiscover|remote/login|ecp|geoserver"
    r"|druid|nacos|struts|axis2|setup\.cgi|shell|cmd|eval-stdin)(/|$|\.|\?)"
    r"|(^|/)[\w.-]*\.(sql|bak|old|orig|swp|backup|tar|tgz|7z|rar|db|sqlite3?|log|pem|key|ini|conf)$"
    r"|(^|/)(etc/passwd|etc/shadow|proc/self|win\.ini|boot\.ini|web\.config)",
    re.I,
)

ATTACK_RES = (
    ('SQL injection', re.compile(
        r"union(\s|/\*.*?\*/|\+)+(all(\s|\+)+)?select|\bselect\b.{1,80}\bfrom\b.{1,80}\b(information_schema|mysql\.|pg_|sysobjects)"
        r"|\b(or|and)\s+\d+\s*=\s*\d+|'\s*(or|and)\s*'?\d*'?\s*=|\bsleep\s*\(\s*\d+\s*\)|benchmark\s*\(|waitfor\s+delay"
        r"|\b(drop|truncate)\s+table\b|;\s*(drop|delete|insert|update)\s|extractvalue\s*\(|updatexml\s*\(", re.I)),
    ('XSS', re.compile(
        r"<\s*(script|svg|iframe|img|body|object|embed)\b[^>]*?(on\w+\s*=|src\s*=|>)|javascript\s*:|\bon(error|load|mouseover|focus)\s*="
        r"|document\.(cookie|domain)|alert\s*\(", re.I)),
    ('Path traversal', re.compile(r"(\.\.[/\\]){2,}|\.\.[/\\].*(etc|windows|proc)[/\\]|/etc/(passwd|shadow)|c:\\\\windows", re.I)),
    ('Command injection', re.compile(
        r"(;|\||&&|`|\$\()\s*(cat|wget|curl|bash|sh|nc|ncat|id|whoami|uname|chmod|python|perl|powershell)\b", re.I)),
    ('Log4Shell / JNDI', re.compile(r"\$\{\s*(jndi|lower|upper|env|sys|::-)", re.I)),
    ('PHP / template injection', re.compile(r"<\?php|\bphp://|\bdata://|\bexpect://|\{\{\s*[\w.]*(__class__|config|self|request)", re.I)),
)

SCANNER_UA_RE = re.compile(
    r"sqlmap|nikto|nmap|masscan|zgrab|zmap|nuclei|wpscan|dirbuster|dirb/|gobuster|ffuf|feroxbuster|wfuzz"
    r"|acunetix|nessus|openvas|netsparker|qualys|burp(suite)?|hydra|jaeles|whatweb|arachni|w3af|skipfish"
    r"|commix|xsstrike|morfeus|zmeu|censysinspect|expanse|internet-measurement|l9explore|leakix",
    re.I,
)


def _decoded(value):
    """URL-decode twice (attackers double-encode) and normalise whitespace."""
    text = value or ''
    for _ in range(2):
        try:
            decoded = unquote_plus(text)
        except Exception:
            break
        if decoded == text:
            break
        text = decoded
    return text


def _is_internal(ip):
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return addr.is_private or addr.is_loopback


def _minute():
    return int(time.time() // 60)


def _bump(key, ttl=120):
    try:
        if cache.add(key, 1, ttl):
            return 1
        return cache.incr(key)
    except Exception:
        return 0


def report(action, request=None, *, detail='', source='', message='', object_repr='', merge_key=None):
    """Record (or merge into) an anomaly row. Never raises."""
    from . import audit
    from .models import AuditLog
    try:
        if not _setting('SECURITY_MONITOR_ENABLED', True):
            return None
        ip = source or (audit._client_ip(request) if request is not None else '') or ''
        key = 'secmon:merge:{}:{}'.format(action, merge_key or ip or detail)
        row_id = cache.get(key)
        now = timezone.now()
        if row_id:
            updated = AuditLog.objects.filter(pk=row_id).update(hits=F('hits') + 1, last_seen_at=now)
            if updated:
                return row_id
        if _bump('secmon:new:{}'.format(_minute())) > _setting('SECURITY_MAX_NEW_ROWS_PER_MINUTE', 120):
            logger.warning('Security monitor: row cap reached, dropped %s from %s', action, ip)
            return None
        row = audit.record(
            action,
            status=AuditLog.STATUS_ALERT,
            category=AuditLog.CATEGORY_SECURITY,
            request=request if request is not None else False,
            user=False,
            object_repr=(object_repr or detail)[:200],
            message=message,
        )
        if row is not None:
            if request is None and source:
                AuditLog.objects.filter(pk=row.pk).update(ip_address=source)
            AuditLog.objects.filter(pk=row.pk).update(last_seen_at=now)
            cache.set(key, row.pk, _setting('SECURITY_MERGE_SECONDS', 600))
            return row.pk
    except Exception:
        logger.exception('Security monitor failed to record %s', action)
    return None


def inspect(request):
    """Return (action, detail) for the most serious finding in the request, or None."""
    path = request.path or ''
    query = request.META.get('QUERY_STRING', '') or ''
    target = _decoded(path + ('?' + query if query else ''))
    extras = ' '.join(_decoded(request.META.get(h, '')) for h in ('HTTP_USER_AGENT', 'HTTP_REFERER'))
    for label, pattern in ATTACK_RES:
        match = pattern.search(target) or pattern.search(extras)
        if match:
            return 'security_attack', '{}: {}'.format(label, match.group(0)[:80])
    match = PROBE_RE.search(_decoded(path))
    if match:
        return 'security_probe', match.group(0).strip('/')[:80]
    ua = request.META.get('HTTP_USER_AGENT', '') or ''
    match = SCANNER_UA_RE.search(ua)
    if match:
        return 'security_scanner', match.group(0)[:80]
    return None


def _monitored(request):
    user = getattr(request, 'user', None)
    return not (user is not None and getattr(user, 'is_authenticated', False) and user.is_staff)


class SecurityMonitorMiddleware:
    """Inspect every request/response and report anomalies to the audit log."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from . import audit

        enabled = _setting('SECURITY_MONITOR_ENABLED', True)
        finding = None
        ip = ''
        if enabled:
            try:
                ip = audit._client_ip(request) or ''
                finding = inspect(request)
            except Exception:
                logger.exception('Security monitor inspection failed')

        response = self.get_response(request)

        if not enabled:
            return response
        try:
            # request.user is available now (AuthenticationMiddleware ran inside get_response).
            if not _monitored(request):
                return response
            method = request.method
            status = getattr(response, 'status_code', 0)
            if finding:
                action, detail = finding
                # Attacks merge per source *and* attack type (SQLi vs XSS ...); probes and
                # scanners merge per source, since a scan touches hundreds of paths.
                merge = '{}:{}'.format(ip, detail.split(':', 1)[0]) if action == 'security_attack' else None
                report(action, request, detail=detail, merge_key=merge,
                       message='{} {} -> {} | {}'.format(method, request.get_full_path()[:200], status, detail))
            # Rate checks need a real client address: behind a proxy without
            # TRUST_X_FORWARDED_FOR every request would share the proxy's IP.
            rate_ok = ip and (_setting('TRUST_X_FORWARDED_FOR', False) or not _is_internal(ip)
                              or _setting('SECURITY_MONITOR_INTERNAL_IPS', False))
            if rate_ok:
                minute = _minute()
                count = _bump('secmon:rate:{}:{}'.format(ip, minute))
                limit = _setting('SECURITY_FLOOD_PER_MINUTE', 300)
                if count >= limit:
                    report('security_flood', request, detail='{}+ requests/min'.format(limit),
                           message='{} sent at least {} requests within one minute (last: {} {}).'.format(
                               ip, count, method, request.path[:150]))
                if status == 404:
                    misses = _bump('secmon:404:{}:{}'.format(ip, minute))
                    limit404 = _setting('SECURITY_404_PER_MINUTE', 30)
                    if misses >= limit404:
                        report('security_not_found_burst', request, detail='{}+ 404s/min'.format(limit404),
                               message='{} hit at least {} missing URLs within one minute (last: {}).'.format(
                                   ip, misses, request.path[:150]))
        except Exception:
            logger.exception('Security monitor post-processing failed')
        return response


class SecurityLogHandler(logging.Handler):
    """Logging handler for the ``django.security`` loggers (bad Host, CSRF failure, ...)."""

    def emit(self, record):
        try:
            if getattr(record, '_secmon', False):
                return
            request = getattr(record, 'request', None)
            if request is None:
                from . import audit
                request = audit.current_request()
            if request is not None and not _monitored(request):
                return
            kind = record.name.split('.', 2)[-1] if record.name.count('.') >= 2 else record.name
            text = record.getMessage()[:500]
            from . import audit
            ip = (audit._client_ip(request) if request is not None else '') or ''
            report('security_suspicious', request, detail=kind,
                   message='[{}] {}'.format(kind, text), merge_key='{}:{}'.format(ip, kind))
        except Exception:
            pass


def report_exception(request, exc):
    """Called for unhandled exceptions (HTTP 500)."""
    name = type(exc).__name__ if exc is not None else 'Exception'
    path = getattr(request, 'path', '') if request is not None else ''
    report('security_server_error', request, detail=name,
           message='{}: {}'.format(name, str(exc)[:400]),
           merge_key='{}:{}'.format(name, path))
