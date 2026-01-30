from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from myHomePage.models import Profile, SystemConfig
from myHomePage.services import sync_publications
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '同步ORCID和Google Scholar的出版物'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='强制同步所有出版物，忽略同步间隔')
        parser.add_argument('--profile', type=int, help='指定要同步的用户ID')

    def handle(self, *args, **options):
        # 获取同步间隔
        sync_interval = timedelta(hours=SystemConfig.get_sync_interval_hours())
        
        # 构建查询
        query = Profile.objects.filter(
            # 启用了自动同步
            models.Q(auto_sync_orcid=True) | models.Q(auto_sync_google_scholar=True)
        )
        
        # 如果指定了用户ID
        if options['profile']:
            query = query.filter(id=options['profile'])
        
        # 如果不是强制同步，添加时间过滤
        if not options['force']:
            query = query.filter(
                # 从未同步或上次同步时间超过间隔
                models.Q(last_sync_time__isnull=True) |
                models.Q(last_sync_time__lt=timezone.now() - sync_interval)
            )
        
        profiles = query.distinct()
        
        if not profiles:
            self.stdout.write(self.style.WARNING('没有需要同步的用户'))
            return
        
        total_imported = 0
        for profile in profiles:
            try:
                self.stdout.write(f'正在同步用户 {profile.user.get_full_name()} 的出版物...')
                imported = sync_publications(profile)
                total_imported += imported
                self.stdout.write(
                    self.style.SUCCESS(
                        f'成功同步 {imported} 篇出版物'
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'同步失败: {str(e)}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'同步完成，共导入 {total_imported} 篇出版物'
            )
        ) 