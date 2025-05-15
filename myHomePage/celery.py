import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings

# 设置默认Django设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myHomePage.settings')

app = Celery('myHomePage')

# 使用Django的设置文件配置Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# 从所有已注册的Django应用中加载任务模块
app.autodiscover_tasks()

# 配置定期任务
app.conf.beat_schedule = {
    'sync-publications': {
        'task': 'myHomePage.tasks.sync_publications_task',
        'schedule': crontab(minute='0', hour='*/1'),  # 每小时执行一次
    },
} 