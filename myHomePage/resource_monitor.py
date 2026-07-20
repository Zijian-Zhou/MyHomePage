import os
import shutil
import sys
import threading
import time
from datetime import timedelta

from django.conf import settings
from django.db import OperationalError, ProgrammingError, close_old_connections
from django.utils import timezone


SAMPLE_INTERVAL_SECONDS = 5
CLEANUP_INTERVAL_SECONDS = 3600

_thread = None
_stop_event = threading.Event()
_last_network = None
_last_cleanup_at = 0


def _fallback_memory_data():
    if os.name == 'nt':
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ('dwLength', ctypes.c_ulong),
                    ('dwMemoryLoad', ctypes.c_ulong),
                    ('ullTotalPhys', ctypes.c_ulonglong),
                    ('ullAvailPhys', ctypes.c_ulonglong),
                    ('ullTotalPageFile', ctypes.c_ulonglong),
                    ('ullAvailPageFile', ctypes.c_ulonglong),
                    ('ullTotalVirtual', ctypes.c_ulonglong),
                    ('ullAvailVirtual', ctypes.c_ulonglong),
                    ('sullAvailExtendedVirtual', ctypes.c_ulonglong),
                ]

            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(status)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            used = status.ullTotalPhys - status.ullAvailPhys
            return {
                'memory_percent': float(status.dwMemoryLoad),
                'memory_total': status.ullTotalPhys,
                'memory_used': used,
                'memory_available': status.ullAvailPhys,
            }
        except Exception:
            return {}
    try:
        values = {}
        with open('/proc/meminfo', 'r') as handle:
            for line in handle:
                key, raw_value = line.split(':', 1)
                values[key] = int(raw_value.strip().split()[0]) * 1024
        total = values.get('MemTotal')
        available = values.get('MemAvailable')
        if total and available is not None:
            used = total - available
            return {
                'memory_percent': round((used / total) * 100, 1),
                'memory_total': total,
                'memory_used': used,
                'memory_available': available,
            }
    except Exception:
        return {}
    return {}


def collect_sample():
    """Collect one resource sample. psutil gives the full sample; stdlib is a safe fallback."""
    global _last_network

    now = timezone.now()
    sample = {'created_at': now}
    try:
        import psutil

        vm = psutil.virtual_memory()
        disk = psutil.disk_usage(str(settings.BASE_DIR))
        net = psutil.net_io_counters()
        proc = psutil.Process(os.getpid())
        upload_speed = None
        download_speed = None
        if _last_network:
            seconds = max(1.0, (time.time() - _last_network['time']))
            upload_speed = max(0.0, (net.bytes_sent - _last_network['sent']) / seconds)
            download_speed = max(0.0, (net.bytes_recv - _last_network['received']) / seconds)
        _last_network = {'sent': net.bytes_sent, 'received': net.bytes_recv, 'time': time.time()}

        sample.update({
            'cpu_percent': round(psutil.cpu_percent(interval=0.1), 1),
            'memory_percent': round(vm.percent, 1),
            'memory_total': vm.total,
            'memory_used': vm.used,
            'memory_available': vm.available,
            'disk_percent': round(disk.percent, 1),
            'disk_total': disk.total,
            'disk_used': disk.used,
            'disk_free': disk.free,
            'network_sent': net.bytes_sent,
            'network_received': net.bytes_recv,
            'upload_speed': upload_speed,
            'download_speed': download_speed,
            'process_memory_rss': proc.memory_info().rss,
            'process_threads': proc.num_threads(),
        })
        return sample
    except Exception:
        disk = shutil.disk_usage(str(settings.BASE_DIR))
        sample.update(_fallback_memory_data())
        sample.update({
            'disk_percent': round((disk.used / disk.total) * 100, 1) if disk.total else None,
            'disk_total': disk.total,
            'disk_used': disk.used,
            'disk_free': disk.free,
        })
        return sample


def save_sample():
    from .models import ResourceMetricLog

    sample = collect_sample()
    return ResourceMetricLog.objects.create(**sample)


def cleanup_old_logs():
    from .models import ResourceMetricLog, SystemConfig

    cutoff = timezone.now() - timedelta(hours=SystemConfig.get_resource_log_retention_hours())
    ResourceMetricLog.objects.filter(created_at__lt=cutoff).delete()


def _loop():
    global _last_cleanup_at

    while not _stop_event.wait(SAMPLE_INTERVAL_SECONDS):
        try:
            close_old_connections()
            save_sample()
            now = time.time()
            if now - _last_cleanup_at >= CLEANUP_INTERVAL_SECONDS:
                cleanup_old_logs()
                _last_cleanup_at = now
        except (OperationalError, ProgrammingError):
            # Migrations or startup may run before the metric table exists.
            time.sleep(SAMPLE_INTERVAL_SECONDS)
        except Exception:
            time.sleep(SAMPLE_INTERVAL_SECONDS)
        finally:
            close_old_connections()


def start_monitor_thread():
    global _thread
    if _thread and _thread.is_alive():
        return
    if sys.argv and sys.argv[0].endswith('manage.py') and len(sys.argv) > 1 and sys.argv[1] != 'runserver':
        return
    if os.environ.get('RUN_MAIN') not in (None, 'true'):
        return
    _stop_event.clear()
    _thread = threading.Thread(target=_loop, name='resource-monitor', daemon=True)
    _thread.start()
