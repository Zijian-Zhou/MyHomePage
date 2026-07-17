from django.utils import translation
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import logout
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.shortcuts import render
from django.http import HttpResponseRedirect
import requests
import time

from .security import decrypt_identity, decrypt_login_field, identity_digest, sign_identity, verify_signed_identity


def get_client_ip(request):
    if getattr(settings, 'TRUST_X_FORWARDED_FOR', False):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
    return (request.META.get('REMOTE_ADDR', '') or '').strip()


class IPBasedLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Keep request path fast unless geo language detection is explicitly enabled.
        if not getattr(settings, 'ENABLE_IP_GEO_LANGUAGE', False):
            return self.get_response(request)

        if 'django_language' in request.session:
            return self.get_response(request)

        ip = get_client_ip(request)

        if ip in ['127.0.0.1', 'localhost', '::1']:
            return self.get_response(request)

        try:
            response = requests.get(f'http://ip-api.com/json/{ip}', timeout=2.5)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    country_code = data.get('countryCode')
                    translation.activate('zh-hans' if country_code == 'CN' else 'en')
        except requests.RequestException:
            translation.activate(settings.LANGUAGE_CODE)

        return self.get_response(request)


class ChineseModeUrlMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Keep i18n language-post endpoint working as-is.
        if request.path.startswith('/i18n/setlang'):
            return self.get_response(request)

        try:
            from .models import SystemConfig
            chinese_enabled = SystemConfig.is_chinese_enabled()
        except Exception:
            chinese_enabled = True

        if not chinese_enabled:
            path = request.path
            lowered = path.lower()
            if lowered.startswith('/zh-hans/'):
                target = '/en/' + path[len('/zh-hans/'):]
                if request.META.get('QUERY_STRING'):
                    target += '?' + request.META['QUERY_STRING']
                return HttpResponseRedirect(target)
            if lowered == '/zh-hans':
                return HttpResponseRedirect('/en/')
            if lowered.startswith('/zh-cn/'):
                target = '/en/' + path[len('/zh-cn/'):]
                if request.META.get('QUERY_STRING'):
                    target += '?' + request.META['QUERY_STRING']
                return HttpResponseRedirect(target)
            if lowered == '/zh-cn':
                return HttpResponseRedirect('/en/')

        return self.get_response(request)


class SessionSecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self._clear_expired_sessions_hourly()
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            sig = request.session.get("auth_sig")
            ts = request.session.get("auth_ts")
            if not sig or not ts:
                logout(request)
                request.session.flush()
                return self.get_response(request)

            max_age = getattr(settings, "SESSION_COOKIE_AGE", 1800)
            now_ts = int(timezone.now().timestamp())
            if now_ts - int(ts) > max_age:
                logout(request)
                request.session.flush()
                return self.get_response(request)

            digest = identity_digest(user)
            decrypted = verify_signed_identity(sig)
            if decrypted is None:
                # Backward compatibility for sessions created before auth signatures
                # were moved away from in-memory RSA keys.
                decrypted = decrypt_identity(sig)
            if decrypted != digest:
                logout(request)
                request.session.flush()
                return self.get_response(request)
            if verify_signed_identity(sig) is None:
                request.session["auth_sig"] = sign_identity(digest)

            # Refresh session timestamp to enforce rolling 30-minute window
            request.session["auth_ts"] = now_ts

        return self.get_response(request)

    def _clear_expired_sessions_hourly(self):
        cache_key = "session_cleanup_last_run"
        now_ts = int(timezone.now().timestamp())
        last_run = cache.get(cache_key)
        if last_run and now_ts - int(last_run) < 3600:
            return
        cache.set(cache_key, now_ts, timeout=3600)
        Session.objects.filter(expire_date__lt=timezone.now()).delete()


class LoginEncryptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "POST" and request.path.endswith("/admin/login/"):
            if request.POST.get("rsa_encrypted") == "1":
                data = request.POST.copy()
                username = data.get("username")
                password = data.get("password")
                if username:
                    decrypted = decrypt_login_field(username)
                    if decrypted:
                        data["username"] = decrypted
                if password:
                    decrypted = decrypt_login_field(password)
                    if decrypted:
                        data["password"] = decrypted
                # Ensure Django uses decrypted data for auth
                request._post = data
                request.POST = data
        return self.get_response(request)


class AdminLoginRateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.endswith('/admin/login/'):
            return self.get_response(request)

        identifier = self._build_identifier(request)
        lock_remaining = self._lock_remaining_seconds(identifier)
        if lock_remaining > 0:
            return self._locked_response(request, lock_remaining)

        if request.method != 'POST':
            return self.get_response(request)

        response = self.get_response(request)

        if self._is_login_success(response):
            self._clear_attempts(identifier)
        else:
            self._register_failure(identifier)
            lock_remaining = self._lock_remaining_seconds(identifier)
            if lock_remaining > 0:
                return self._locked_response(request, lock_remaining)

        return response

    def _build_identifier(self, request):
        ip = get_client_ip(request)
        return ip or 'unknown'

    def _attempt_key(self, identifier):
        return 'admin_login_attempt:{}'.format(identifier)

    def _lock_key(self, identifier):
        return 'admin_login_lock:{}'.format(identifier)

    def _max_attempts(self):
        try:
            return int(getattr(settings, 'LOGIN_MAX_ATTEMPTS', 5))
        except (TypeError, ValueError):
            return 5

    def _window_seconds(self):
        try:
            return int(getattr(settings, 'LOGIN_ATTEMPT_WINDOW_SECONDS', 600))
        except (TypeError, ValueError):
            return 600

    def _lockout_seconds(self):
        try:
            return int(getattr(settings, 'LOGIN_LOCKOUT_SECONDS', 900))
        except (TypeError, ValueError):
            return 900

    def _lock_remaining_seconds(self, identifier):
        lock_data = cache.get(self._lock_key(identifier))
        if not lock_data:
            return 0
        until_ts = int(lock_data.get('until', 0))
        if until_ts <= 0:
            return 0
        return max(until_ts - int(time.time()), 0)

    def _clear_attempts(self, identifier):
        cache.delete(self._attempt_key(identifier))
        cache.delete(self._lock_key(identifier))

    def _register_failure(self, identifier):
        attempt_key = self._attempt_key(identifier)
        attempts = cache.get(attempt_key, 0)
        attempts = int(attempts) + 1
        cache.set(attempt_key, attempts, timeout=self._window_seconds())
        if attempts >= self._max_attempts():
            lockout_seconds = self._lockout_seconds()
            cache.set(
                self._lock_key(identifier),
                {'until': int(time.time()) + lockout_seconds},
                timeout=lockout_seconds + 5
            )

    def _is_login_success(self, response):
        if response.status_code not in (301, 302):
            return False
        location = response.get('Location', '') or ''
        return '/admin/login/' not in location

    def _locked_response(self, request, remaining_seconds):
        minutes = max(1, (remaining_seconds + 59) // 60)
        response = render(
            request,
            'admin/login_locked.html',
            {
                'remaining_seconds': remaining_seconds,
                'remaining_minutes': minutes,
            },
            status=429
        )
        response['Retry-After'] = str(remaining_seconds)
        return response


class MediaFileAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        media_url = getattr(settings, 'MEDIA_URL', '/media/')
        if request.path.startswith(media_url + 'markdown_assets/'):
            rel_name = request.path[len(media_url):]
            from .models import MediaFile
            media_file = MediaFile.objects.filter(file=rel_name).first()
            if media_file and not media_file.is_active:
                user = getattr(request, 'user', None)
                if not (user and user.is_authenticated and user.is_staff):
                    return render(request, '404.html', status=404)
        return self.get_response(request)
