from django.utils import translation
from django.conf import settings
import requests

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