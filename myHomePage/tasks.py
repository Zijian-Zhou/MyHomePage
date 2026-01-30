from celery import shared_task
from datetime import datetime, timedelta
from django.utils import timezone
from .models import Profile, SystemConfig
from .services import sync_publications
from django.db import models

@shared_task
def sync_publications_task():
    """定期同步出版物的Celery任务"""
    # 获取同步间隔
    sync_interval = SystemConfig.get_sync_interval_seconds()
    
    # 获取需要同步的用户配置
    profiles = Profile.objects.filter(
        # 启用了自动同步
        models.Q(auto_sync_orcid=True) | models.Q(auto_sync_google_scholar=True)
    ).filter(
        # 从未同步或上次同步时间超过间隔
        models.Q(last_sync_time__isnull=True) |
        models.Q(last_sync_time__lt=timezone.now() - timedelta(seconds=sync_interval))
    )
    
    total_imported = 0
    for profile in profiles:
        try:
            imported = sync_publications(profile)
            total_imported += imported
        except Exception as e:
            print(f"Error syncing publications for {profile}: {str(e)}")
            continue
    
    return total_imported

def get_sync_interval():
    """获取同步间隔时间（秒）"""
    return SystemConfig.get_sync_interval_seconds() 