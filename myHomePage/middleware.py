from django.utils import translation
from django.conf import settings
import requests
from django.contrib.auth import logout
from django.utils import timezone

from .security import decrypt_identity, decrypt_login_field, identity_digest

class IPBasedLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 如果用户已经选择了语言，则尊重用户的选择
        if 'django_language' in request.session:
            return self.get_response(request)

        # 获取客户端IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')

        # 如果是本地访问，使用默认语言
        if ip in ['127.0.0.1', 'localhost', '::1']:
            return self.get_response(request)

        try:
            # 使用 ip-api.com 的免费服务获取IP地理位置信息
            response = requests.get(f'http://ip-api.com/json/{ip}')
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    country_code = data.get('countryCode')
                    # 如果IP来自中国，设置为中文
                    if country_code == 'CN':
                        translation.activate('zh-hans')
                    else:
                        translation.activate('en')
        except:
            # 如果API调用失败，使用默认语言
            translation.activate(settings.LANGUAGE_CODE)

        response = self.get_response(request)
        return response 


class SessionSecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
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
            decrypted = decrypt_identity(sig)
            if decrypted != digest:
                logout(request)
                request.session.flush()
                return self.get_response(request)

            # Refresh session timestamp to enforce rolling 30-minute window
            request.session["auth_ts"] = now_ts

        return self.get_response(request)


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
