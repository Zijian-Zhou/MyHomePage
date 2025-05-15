from django.core.management.base import BaseCommand
from myHomePage.models import SystemConfig
import requests
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '配置Google Scholar代理设置'

    def add_arguments(self, parser):
        parser.add_argument('--proxy', type=str, help='代理服务器地址 (例如: http://proxy.example.com:8080)')
        parser.add_argument('--test', action='store_true', help='测试当前代理配置')

    def handle(self, *args, **options):
        if options['test']:
            self.test_proxy()
        elif options['proxy']:
            self.set_proxy(options['proxy'])
        else:
            self.stdout.write(self.style.ERROR('请提供--proxy或--test参数'))
            return

    def test_proxy(self):
        """测试当前代理配置"""
        proxy = SystemConfig.get_scholar_proxy()
        if not proxy:
            self.stdout.write(self.style.ERROR('未配置代理服务器'))
            return

        self.stdout.write('正在测试代理配置...')
        try:
            proxies = {'https': proxy}
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(
                'https://scholar.google.com',
                proxies=proxies,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            if 'Please show you&#39;re not a robot' in response.text:
                self.stdout.write(self.style.WARNING('代理配置有效，但Google Scholar可能仍然会阻止请求'))
            else:
                self.stdout.write(self.style.SUCCESS('代理配置有效'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'代理配置无效: {str(e)}'))

    def set_proxy(self, proxy):
        """设置代理服务器"""
        try:
            SystemConfig.set_value(
                'scholar_proxy',
                proxy,
                'Google Scholar代理服务器'
            )
            self.stdout.write(self.style.SUCCESS('成功设置代理服务器'))
            self.test_proxy()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'设置代理服务器失败: {str(e)}')) 