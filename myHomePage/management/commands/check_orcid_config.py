from django.core.management.base import BaseCommand
from myHomePage.models import SystemConfig
from myHomePage.services import ORCIDService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '检查并配置ORCID设置'

    def add_arguments(self, parser):
        parser.add_argument('--token', type=str, help='ORCID访问令牌')
        parser.add_argument('--check', action='store_true', help='仅检查当前配置')

    def handle(self, *args, **options):
        if options['check']:
            self.check_config()
        elif options['token']:
            self.set_token(options['token'])
        else:
            self.stdout.write(self.style.ERROR('请提供--token或--check参数'))
            return

    def check_config(self):
        """检查ORCID配置"""
        token = SystemConfig.get_orcid_token()
        if not token:
            self.stdout.write(self.style.ERROR('未找到ORCID访问令牌'))
            return

        self.stdout.write('正在检查ORCID配置...')
        try:
            # 尝试使用测试ORCID ID
            test_orcid = '0000-0000-0000-0000'
            service = ORCIDService(test_orcid)
            works = service.get_works()
            self.stdout.write(self.style.SUCCESS('ORCID配置有效'))
            self.stdout.write(f'API响应: {works}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'ORCID配置无效: {str(e)}'))

    def set_token(self, token):
        """设置ORCID访问令牌"""
        try:
            SystemConfig.set_value(
                'orcid_access_token',
                token,
                'ORCID访问令牌'
            )
            self.stdout.write(self.style.SUCCESS('成功设置ORCID访问令牌'))
            self.check_config()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'设置ORCID访问令牌失败: {str(e)}')) 