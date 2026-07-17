import os
from datetime import timedelta
from celery import Celery
from django.conf import settings

try:
    from myHomePage.models import SystemConfig
except Exception:
    SystemConfig = None

# 设置默认Django设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'HomePage.settings')

app = Celery('myHomePage')

# 使用Django的设置文件配置Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# 从所有已注册的Django应用中加载任务模块
app.autodiscover_tasks()

# 配置定期任务：固定高频触发，实际是否同步由任务内部根据配置判断
app.conf.beat_schedule = {
    'sync-publications': {
        'task': 'myHomePage.tasks.sync_publications_task',
        'schedule': timedelta(minutes=1),
    },
    'clear-expired-sessions': {
        'task': 'myHomePage.tasks.clear_expired_sessions_task',
        'schedule': timedelta(hours=1),
    },
} 
