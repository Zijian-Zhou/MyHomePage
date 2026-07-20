from django.contrib import admin
from django.conf import settings
from django.urls import path
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils.translation import get_language
from django.utils.html import escape, format_html
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta, datetime
from .models import Profile, Publication, PublicationFile, Research, SystemConfig, ResourceMetricLog, News, Section, SectionItem, MediaFile, AIConfig
from .services import sync_publications, ORCIDService, GoogleScholarService, ORCIDOAuth, deduplicate_publications
from django.contrib.auth.decorators import user_passes_test
from django.contrib.admin.sites import AdminSite
from django.template.response import TemplateResponse
from django import forms
from django.contrib.auth.models import User, Group
import bibtexparser
import json
import logging
import os
import platform
import shutil
import markdown
from contextlib import contextmanager
from django.shortcuts import redirect

logger = logging.getLogger(__name__)


@contextmanager
def _without_env_proxies():
    proxy_keys = (
        'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY',
        'http_proxy', 'https_proxy', 'all_proxy',
        'NO_PROXY', 'no_proxy',
    )
    old_values = {key: os.environ.get(key) for key in proxy_keys}
    for key in proxy_keys:
        os.environ.pop(key, None)
    os.environ['NO_PROXY'] = '*'
    os.environ['no_proxy'] = '*'
    try:
        yield
    finally:
        for key in proxy_keys:
            if old_values[key] is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_values[key]


def _is_zh_mode():
    return (get_language() or '').lower().startswith('zh')


def _category_label_map():
    if _is_zh_mode():
        return {
            'enable_chinese': '启用中文',
            'cards_per_page': '每页卡片数',
            'orcid_client_id': 'ORCID Client ID',
            'orcid_client_secret': 'ORCID Client Secret',
            'orcid_access_token': 'ORCID Access Token',
            'scholar_proxy': 'Google Scholar 代理',
            'sync_interval': '同步间隔',
            'github_token': 'GitHub 令牌',
            'researchgate_token': 'ResearchGate 令牌',
            'linkedin_token': 'LinkedIn 令牌',
            'highlighted_authors': '高亮作者',
            'footer_items': '页脚显示项',
            'resource_log_retention_hours': '\u8d44\u6e90\u76d1\u63a7\u65e5\u5fd7\u4fdd\u7559\u65f6\u957f',
        }
    return {
        'enable_chinese': _('Enable Chinese'),
        'cards_per_page': _('Cards Per Page'),
        'orcid_client_id': _('ORCID Client ID'),
        'orcid_client_secret': _('ORCID Client Secret'),
        'orcid_access_token': _('ORCID Access Token'),
        'scholar_proxy': _('Google Scholar Proxy'),
        'sync_interval': _('Sync Interval'),
        'github_token': _('GitHub Token'),
        'researchgate_token': _('ResearchGate Token'),
        'linkedin_token': _('LinkedIn Token'),
        'highlighted_authors': _('Highlighted Authors'),
        'footer_items': _('Footer Items'),
        'resource_log_retention_hours': _('Resource Log Retention Hours'),
    }


def _validate_footer_items_json(value):
    value = (value or '').strip()
    if not value:
        return value
    try:
        payload = json.loads(value)
    except (ValueError, TypeError):
        raise forms.ValidationError(_('Footer Items value must be valid JSON.'))

    item_data = payload.get('item')
    if isinstance(item_data, dict):
        item_data = [item_data]
    if not isinstance(item_data, list) or not item_data:
        raise forms.ValidationError(_('Footer Items must contain "item" as an object or list.'))

    for entry in item_data:
        if not isinstance(entry, dict) or not str(entry.get('content', '')).strip():
            raise forms.ValidationError(_('Each footer item must include a non-empty "content".'))
    return value



def _validate_ai_config_json(value):
    value = (value or '').strip()
    if not value:
        return value
    try:
        payload = json.loads(value)
    except (ValueError, TypeError):
        raise forms.ValidationError(
            '\u0041\u0049 \u914d\u7f6e\u5fc5\u987b\u662f\u5408\u6cd5 \u004a\u0053\u004f\u004e\u3002'
            if _is_zh_mode()
            else _('AI Configuration value must be valid JSON.')
        )

    if not isinstance(payload, dict):
        raise forms.ValidationError(
            '\u0041\u0049 \u914d\u7f6e\u5fc5\u987b\u662f \u004a\u0053\u004f\u004e \u5bf9\u8c61\u3002'
            if _is_zh_mode()
            else _('AI Configuration must be a JSON object.')
        )

    providers = payload.get('providers')
    if providers is not None:
        if not isinstance(providers, list):
            raise forms.ValidationError(
                '\u0041\u0049 \u914d\u7f6e\u4e2d\u7684 \u0070\u0072\u006f\u0076\u0069\u0064\u0065\u0072\u0073 \u5fc5\u987b\u662f\u6570\u7ec4\u3002'
                if _is_zh_mode()
                else _('AI Configuration providers must be a list.')
            )
        for provider in providers:
            if not isinstance(provider, dict) or not str(provider.get('name', '')).strip():
                raise forms.ValidationError(
                    '\u6bcf\u4e2a \u0041\u0049 \u0070\u0072\u006f\u0076\u0069\u0064\u0065\u0072 \u5fc5\u987b\u5305\u542b\u975e\u7a7a \u006e\u0061\u006d\u0065\u3002'
                    if _is_zh_mode()
                    else _('Each AI provider must include a non-empty name.')
                )
    return value

def _strip_zh_fields(fieldsets):
    cleaned = []
    for title, opts in fieldsets:
        fields = tuple(f for f in opts.get('fields', ()) if not str(f).endswith('_zh'))
        if not fields:
            continue
        copied = dict(opts)
        copied['fields'] = fields
        cleaned.append((title, copied))
    return tuple(cleaned)


def _apply_zh_field_labels(form, label_map):
    if not _is_zh_mode():
        return form
    for field_name, label in label_map.items():
        if field_name in form.base_fields:
            form.base_fields[field_name].label = label
    return form


class SystemConfigAdminForm(forms.ModelForm):
    class Meta:
        model = SystemConfig
        fields = '__all__'

    def clean_value(self):
        value = self.cleaned_data.get('value', '')
        category = self.cleaned_data.get('category') or getattr(self.instance, 'category', '')
        if category == 'enable_chinese':
            normalized = str(value).strip().lower()
            if normalized in ('1', 'true', 'on', 'yes'):
                return '1'
            if normalized in ('0', 'false', 'off', 'no'):
                return '0'
            raise forms.ValidationError(
                '启用中文配置必须是 "1"（启用）或 "0"（禁用）。'
                if _is_zh_mode()
                else _('Enable Chinese must be "1" (enabled) or "0" (disabled).')
            )
        if category == 'cards_per_page':
            try:
                parsed = int(float(str(value).strip() or '6'))
            except (ValueError, TypeError):
                raise forms.ValidationError(
                    '每页卡片数必须是正整数。'
                    if _is_zh_mode()
                    else _('Cards Per Page must be a positive integer.')
                )
            if parsed < 1:
                raise forms.ValidationError(
                    '每页卡片数必须是正整数。'
                    if _is_zh_mode()
                    else _('Cards Per Page must be a positive integer.')
                )
            return str(parsed)
        if category == 'resource_log_retention_hours':
            try:
                parsed = float(str(value).strip() or '168')
            except (ValueError, TypeError):
                raise forms.ValidationError(
                    '\u8d44\u6e90\u76d1\u63a7\u65e5\u5fd7\u4fdd\u7559\u65f6\u957f\u5fc5\u987b\u662f\u6b63\u6570\u3002'
                    if _is_zh_mode()
                    else _('Resource Log Retention Hours must be a positive number.')
                )
            if parsed <= 0:
                raise forms.ValidationError(
                    '\u8d44\u6e90\u76d1\u63a7\u65e5\u5fd7\u4fdd\u7559\u65f6\u957f\u5fc5\u987b\u662f\u6b63\u6570\u3002'
                    if _is_zh_mode()
                    else _('Resource Log Retention Hours must be a positive number.')
                )
            return str(parsed)
        if category == 'footer_items':
            return _validate_footer_items_json(value)
        return (value or '').strip()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'category' in self.fields:
            labels = _category_label_map()
            self.fields['category'].choices = [
                (key, labels.get(key, label))
                for key, label in self.fields['category'].choices
            ]


class SystemConfigCategoryFilter(admin.SimpleListFilter):
    title = _('Category')
    parameter_name = 'category'

    def lookups(self, request, model_admin):
        labels = _category_label_map()
        keys = [choice[0] for choice in SystemConfig.CATEGORY_CHOICES]
        return [(key, labels.get(key, key)) for key in keys]

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset
        return queryset.filter(category=value)


def is_staff_user(user):
    return user.is_authenticated and user.is_staff

class CustomAdminSite(AdminSite):
    index_template = 'admin/custom_index.html'
    app_index_template = 'admin/custom_app_index.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('', self.admin_view(self.index), name='index'),
            path('toggle-dark-mode/', self.admin_view(self.toggle_dark_mode), name='toggle-dark-mode'),
            path('auto-translate-field/', self.admin_view(self.auto_translate_field), name='auto-translate-field'),
            path('system-resources/', self.admin_view(self.system_resources), name='system-resources'),
            path('system-resources/data/', self.admin_view(self.system_resources_data), name='system-resources-data'),
        ]
        return custom_urls + urls

    def has_permission(self, request):
        return is_staff_user(request.user)

    def toggle_dark_mode(self, request):
        if 'dark_mode' in request.session:
            request.session['dark_mode'] = not request.session['dark_mode']
        else:
            request.session['dark_mode'] = True
        return JsonResponse({'dark_mode': request.session['dark_mode']})

    def auto_translate_field(self, request):
        if request.method != 'POST':
            return JsonResponse({'error': _('Unsupported request method')}, status=405)

        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except (ValueError, TypeError):
            return JsonResponse({'error': _('Invalid JSON payload.')}, status=400)

        text = str(payload.get('text') or '').strip()
        source_lang = str(payload.get('source_lang') or 'auto').strip() or 'auto'
        target_lang = str(payload.get('target_lang') or '').strip()
        if not text:
            return JsonResponse({'error': _('Text is empty.')}, status=400)
        if target_lang not in ('en', 'zh'):
            return JsonResponse({'error': _('Unsupported target language.')}, status=400)

        try:
            with _without_env_proxies():
                import translators as ts
        except ModuleNotFoundError:
            return JsonResponse(
                {'error': _('The translators package is not installed in this environment.')},
                status=500
            )
        except Exception as exc:
            logger.warning('The translators package failed to initialize: %s', exc)
            return JsonResponse(
                {'error': _('The translators package is installed but failed to initialize.')},
                status=500
            )

        from_language = 'auto' if source_lang == 'auto' else source_lang
        to_language = 'zh' if target_lang == 'zh' else 'en'

        errors = []
        for translator in ('alibaba', 'sogou', 'google', 'bing'):
            try:
                with _without_env_proxies():
                    translated = ts.translate_text(
                        query_text=text,
                        translator=translator,
                        from_language=from_language,
                        to_language=to_language,
                    )
                return JsonResponse({'translated_text': translated, 'translator': translator})
            except Exception as exc:
                errors.append(f'{translator}: {exc.__class__.__name__}')
                logger.warning('Auto translation failed with %s: %s', translator, exc)

        return JsonResponse(
            {'error': _('Auto translation failed.') + ' ' + '; '.join(errors)},
            status=502
        )

    def each_context(self, request):
        context = super().each_context(request)
        context['dark_mode'] = request.session.get('dark_mode', False)
        context['site_title'] = _('HomePage Administration')
        context['site_header'] = _('HomePage Administration')
        context['index_title'] = _('HomePage Administration')
        context['footer_items'] = SystemConfig.get_footer_items()
        context['show_language_switcher'] = SystemConfig.is_chinese_enabled()
        context['is_zh_mode'] = _is_zh_mode()
        return context

    def _resource_labels(self):
        if _is_zh_mode():
            return {
                'title': '\u7cfb\u7edf\u8d44\u6e90\u76d1\u63a7',
                'subtitle': '\u67e5\u770b\u670d\u52a1\u5668 CPU\u3001\u5185\u5b58\u3001\u78c1\u76d8\u548c\u7f51\u7edc\u8d44\u6e90\u4f7f\u7528\u60c5\u51b5\u3002',
                'refresh': '\u5237\u65b0',
                'auto_refresh': '\u81ea\u52a8\u5237\u65b0',
                'last_updated': '\u4e0a\u6b21\u66f4\u65b0',
                'cpu': 'CPU',
                'memory': '\u5185\u5b58',
                'disk': '\u78c1\u76d8',
                'network': '\u7f51\u7edc',
                'process': '\u8fdb\u7a0b',
                'system': '\u7cfb\u7edf',
                'usage': '\u4f7f\u7528\u7387',
                'used': '\u5df2\u7528',
                'free': '\u53ef\u7528',
                'total': '\u603b\u91cf',
                'sent': '\u5df2\u53d1\u9001',
                'received': '\u5df2\u63a5\u6536',
                'upload_speed': '\u4e0a\u884c\u901f\u5ea6',
                'download_speed': '\u4e0b\u884c\u901f\u5ea6',
                'load': '\u8d1f\u8f7d',
                'uptime': '\u8fd0\u884c\u65f6\u957f',
                'python': 'Python',
                'platform': '\u5e73\u53f0',
                'process_memory': '\u5f53\u524d\u8fdb\u7a0b\u5185\u5b58',
                'process_threads': '\u7ebf\u7a0b\u6570',
                'process_start': '\u542f\u52a8\u65f6\u95f4',
                'chart_title': '\u8fd1\u671f\u4f7f\u7528\u7387\u62a5\u8868',
                'chart_hint': '\u6570\u636e\u7531\u540e\u7aef\u76d1\u63a7\u7ebf\u7a0b\u6301\u7eed\u91c7\u6837\uff0c\u53ef\u67e5\u770b\u5b9e\u65f6\u548c\u5386\u53f2\u6570\u636e\u3002',
                'history_range': '\u5386\u53f2\u8303\u56f4',
                'realtime_data': '\u5b9e\u65f6\u6570\u636e',
                'history_data': '\u5386\u53f2\u6570\u636e',
                'unavailable': '\u4e0d\u53ef\u7528',
                'error': '\u8d44\u6e90\u6570\u636e\u83b7\u53d6\u5931\u8d25',
            }
        return {
            'title': 'System Resource Monitor',
            'subtitle': 'Inspect server CPU, memory, disk, and network usage.',
            'refresh': 'Refresh',
            'auto_refresh': 'Auto refresh',
            'last_updated': 'Last updated',
            'cpu': 'CPU',
            'memory': 'Memory',
            'disk': 'Disk',
            'network': 'Network',
            'process': 'Process',
            'system': 'System',
            'usage': 'Usage',
            'used': 'Used',
            'free': 'Free',
            'total': 'Total',
            'sent': 'Sent',
            'received': 'Received',
            'upload_speed': 'Upload speed',
            'download_speed': 'Download speed',
            'load': 'Load',
            'uptime': 'Uptime',
            'python': 'Python',
            'platform': 'Platform',
            'process_memory': 'Current process memory',
            'process_threads': 'Threads',
            'process_start': 'Start time',
            'chart_title': 'Recent Usage Report',
            'chart_hint': 'Data is continuously sampled by the backend monitor thread for realtime and historical views.',
            'history_range': 'History range',
            'realtime_data': 'Realtime data',
            'history_data': 'History data',
            'unavailable': 'Unavailable',
            'error': 'Failed to load resource data',
        }

    def _format_bytes(self, value):
        try:
            value = float(value)
        except (TypeError, ValueError):
            return None
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        for unit in units:
            if value < 1024 or unit == units[-1]:
                return f'{value:.1f} {unit}' if unit != 'B' else f'{int(value)} {unit}'
            value /= 1024
        return None

    def _collect_resource_data(self):
        now = timezone.localtime()
        data = {
            'timestamp': now.isoformat(),
            'timestamp_display': now.strftime('%Y-%m-%d %H:%M:%S'),
            'system': {
                'platform': platform.platform(),
                'python': platform.python_version(),
                'processor': platform.processor() or platform.machine(),
            },
            'cpu': {'percent': None, 'count': os.cpu_count()},
            'memory': {},
            'disk': {},
            'network': {},
            'process': {'pid': os.getpid()},
            'available': False,
        }
        try:
            import psutil
        except Exception as exc:
            disk = shutil.disk_usage(str(settings.BASE_DIR))
            data['available'] = True
            data['warning'] = str(exc)
            data['disk'] = {
                'percent': round((disk.used / disk.total) * 100, 1) if disk.total else None,
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'total_display': self._format_bytes(disk.total),
                'used_display': self._format_bytes(disk.used),
                'free_display': self._format_bytes(disk.free),
            }
            data['memory'] = self._fallback_memory_data()
            return data

        data['available'] = True
        cpu_percent = psutil.cpu_percent(interval=0.1)
        vm = psutil.virtual_memory()
        disk = psutil.disk_usage(str(settings.BASE_DIR))
        net = psutil.net_io_counters()
        proc = psutil.Process(os.getpid())
        boot_time = datetime.fromtimestamp(psutil.boot_time(), tz=timezone.get_current_timezone())
        uptime = now - boot_time

        data.update({
            'cpu': {
                'percent': round(cpu_percent, 1),
                'count': psutil.cpu_count(logical=True),
                'physical_count': psutil.cpu_count(logical=False),
            },
            'memory': {
                'percent': round(vm.percent, 1),
                'total': vm.total,
                'used': vm.used,
                'available': vm.available,
                'total_display': self._format_bytes(vm.total),
                'used_display': self._format_bytes(vm.used),
                'available_display': self._format_bytes(vm.available),
            },
            'disk': {
                'percent': round(disk.percent, 1),
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'total_display': self._format_bytes(disk.total),
                'used_display': self._format_bytes(disk.used),
                'free_display': self._format_bytes(disk.free),
            },
            'network': {
                'sent': net.bytes_sent,
                'received': net.bytes_recv,
                'sent_display': self._format_bytes(net.bytes_sent),
                'received_display': self._format_bytes(net.bytes_recv),
            },
            'process': {
                'pid': proc.pid,
                'memory_rss': proc.memory_info().rss,
                'memory_rss_display': self._format_bytes(proc.memory_info().rss),
                'threads': proc.num_threads(),
                'create_time': datetime.fromtimestamp(proc.create_time(), tz=timezone.get_current_timezone()).strftime('%Y-%m-%d %H:%M:%S'),
            },
            'system': {
                'platform': platform.platform(),
                'python': platform.python_version(),
                'processor': platform.processor() or platform.machine(),
                'boot_time': boot_time.strftime('%Y-%m-%d %H:%M:%S'),
                'uptime': str(uptime).split('.')[0],
            }
        })
        if hasattr(os, 'getloadavg'):
            try:
                data['system']['load_avg'] = ', '.join(f'{item:.2f}' for item in os.getloadavg())
            except OSError:
                data['system']['load_avg'] = None
        return data

    def _fallback_memory_data(self):
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
                    'percent': round(float(status.dwMemoryLoad), 1),
                    'total': status.ullTotalPhys,
                    'used': used,
                    'available': status.ullAvailPhys,
                    'total_display': self._format_bytes(status.ullTotalPhys),
                    'used_display': self._format_bytes(used),
                    'available_display': self._format_bytes(status.ullAvailPhys),
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
                    'percent': round((used / total) * 100, 1),
                    'total': total,
                    'used': used,
                    'available': available,
                    'total_display': self._format_bytes(total),
                    'used_display': self._format_bytes(used),
                    'available_display': self._format_bytes(available),
                }
        except Exception:
            return {}
        return {}

    def system_resources(self, request):
        labels = self._resource_labels()
        context = {
            **self.each_context(request),
            'title': labels['title'],
            'labels': labels,
            'resource_data_url': reverse('admin:system-resources-data'),
        }
        request.current_app = self.name
        return TemplateResponse(request, 'admin/system_resources.html', context)

    def system_resources_data(self, request):
        try:
            history_minutes = int(request.GET.get('history_minutes', '60'))
        except (TypeError, ValueError):
            history_minutes = 60
        history_minutes = max(5, min(history_minutes, 24 * 60))

        latest = ResourceMetricLog.objects.order_by('-created_at').first()
        if latest is None:
            try:
                from .resource_monitor import save_sample
                latest = save_sample()
            except Exception:
                return JsonResponse(self._collect_resource_data())

        payload = self._metric_log_to_resource_payload(latest)
        payload['history_minutes'] = history_minutes
        payload['history'] = self._resource_history(history_minutes)
        return JsonResponse(payload)

    def _metric_log_to_resource_payload(self, log):
        now = timezone.localtime(log.created_at)
        data = {
            'timestamp': now.isoformat(),
            'timestamp_display': now.strftime('%Y-%m-%d %H:%M:%S'),
            'available': True,
            'cpu': {
                'percent': log.cpu_percent,
                'count': os.cpu_count(),
            },
            'memory': {
                'percent': log.memory_percent,
                'total': log.memory_total,
                'used': log.memory_used,
                'available': log.memory_available,
                'total_display': self._format_bytes(log.memory_total),
                'used_display': self._format_bytes(log.memory_used),
                'available_display': self._format_bytes(log.memory_available),
            },
            'disk': {
                'percent': log.disk_percent,
                'total': log.disk_total,
                'used': log.disk_used,
                'free': log.disk_free,
                'total_display': self._format_bytes(log.disk_total),
                'used_display': self._format_bytes(log.disk_used),
                'free_display': self._format_bytes(log.disk_free),
            },
            'network': {
                'sent': log.network_sent,
                'received': log.network_received,
                'upload_speed': log.upload_speed,
                'download_speed': log.download_speed,
                'sent_display': self._format_bytes(log.network_sent),
                'received_display': self._format_bytes(log.network_received),
                'upload_speed_display': self._format_speed(log.upload_speed),
                'download_speed_display': self._format_speed(log.download_speed),
            },
            'process': {
                'pid': os.getpid(),
                'memory_rss': log.process_memory_rss,
                'memory_rss_display': self._format_bytes(log.process_memory_rss),
                'threads': log.process_threads,
            },
            'system': {
                'platform': platform.platform(),
                'python': platform.python_version(),
                'processor': platform.processor() or platform.machine(),
            },
        }
        try:
            import psutil
            boot_time = datetime.fromtimestamp(psutil.boot_time(), tz=timezone.get_current_timezone())
            data['system']['boot_time'] = boot_time.strftime('%Y-%m-%d %H:%M:%S')
            data['system']['uptime'] = str(timezone.localtime() - boot_time).split('.')[0]
            proc = psutil.Process(os.getpid())
            data['process']['create_time'] = datetime.fromtimestamp(
                proc.create_time(),
                tz=timezone.get_current_timezone(),
            ).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            pass
        if hasattr(os, 'getloadavg'):
            try:
                data['system']['load_avg'] = ', '.join(f'{item:.2f}' for item in os.getloadavg())
            except OSError:
                data['system']['load_avg'] = None
        return data

    def _format_speed(self, value):
        formatted = self._format_bytes(value)
        return '{} /s'.format(formatted) if formatted else None

    def _resource_history(self, minutes):
        cutoff = timezone.now() - timedelta(minutes=minutes)
        logs = list(ResourceMetricLog.objects.filter(created_at__gte=cutoff).order_by('created_at'))
        if len(logs) > 360:
            step = max(1, len(logs) // 360)
            logs = logs[::step]
        return [
            {
                'timestamp': timezone.localtime(log.created_at).isoformat(),
                'timestamp_display': timezone.localtime(log.created_at).strftime('%H:%M:%S'),
                'cpu': log.cpu_percent or 0,
                'memory': log.memory_percent or 0,
                'disk': log.disk_percent or 0,
                'upload_speed': log.upload_speed or 0,
                'download_speed': log.download_speed or 0,
            }
            for log in logs
        ]

    def index(self, request, extra_context=None):
        app_list = self.get_app_list(request)
        context = {
            **self.each_context(request),
            'title': self.index_title,
            'app_list': app_list,
            **(extra_context or {}),
        }
        request.current_app = self.name
        return TemplateResponse(request, self.index_template or 'admin/index.html', context)

    def get_app_list(self, request):
        model_name_map = {
            'profile': _('Profiles'),
            'publication': _('Publications'),
            'research': _('Research Projects'),
            'systemconfig': _('System Configurations'),
            'aiconfig': _('AI Configurations'),
            'news': _('News'),
            'section': _('Custom Sections'),
            'mediafile': _('Media Files'),
        }

        app_list = super().get_app_list(request)
        for app in app_list:
            if app.get('app_label') == 'myHomePage':
                app['name'] = _('Homepage Content')
                app['models'].append({
                    'name': self._resource_labels()['title'],
                    'object_name': 'SystemResourceMonitor',
                    'perms': {'view': True, 'add': False, 'change': False, 'delete': False},
                    'admin_url': reverse('admin:system-resources'),
                    'add_url': None,
                    'view_only': True,
                })
            for model in app['models']:
                info = (app['app_label'], model['object_name'].lower())
                try:
                    model['admin_url'] = reverse(f'admin:{info[0]}_{info[1]}_changelist')
                except Exception:
                    continue
                model_name = model_name_map.get(model['object_name'].lower())
                if model_name:
                    model['name'] = model_name
        return app_list


admin_site = CustomAdminSite(name='admin')

class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_active', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

class GroupAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)
    filter_horizontal = ('permissions',)

# Register models
admin_site.register(User, UserAdmin)
admin_site.register(Group, GroupAdmin)

# Add dark mode support to all admin classes


class DraftSaveMixin:
    def _save_as_draft(self, request, obj):
        if '_saveasdraft' not in request.POST:
            return False
        if hasattr(obj, 'is_draft'):
            obj.is_draft = True
            obj.save(update_fields=['is_draft'])
            self.message_user(request, _('Saved as draft.'))
        return True

    def response_change(self, request, obj):
        if self._save_as_draft(request, obj):
            url = reverse('admin:%s_%s_change' % (obj._meta.app_label, obj._meta.model_name), args=[obj.pk])
            return HttpResponseRedirect(url)
        return super().response_change(request, obj)

    def response_add(self, request, obj, post_url_continue=None):
        if self._save_as_draft(request, obj):
            url = reverse('admin:%s_%s_change' % (obj._meta.app_label, obj._meta.model_name), args=[obj.pk])
            return HttpResponseRedirect(url)
        return super().response_add(request, obj, post_url_continue)


class BaseAdmin(admin.ModelAdmin):
    class Media:
        css = {
            'all': ('css/admin/custom.css', 'css/admin/dark_mode.css')
        }
        js = ('js/admin/dark_mode.js',)

@admin.register(Profile)
class ProfileAdmin(DraftSaveMixin, BaseAdmin):
    list_display = ('get_admin_display_name', 'orcid_link', 'google_scholar_link', 'sync_status', 'actions_column')
    list_filter = ('auto_sync_orcid', 'auto_sync_google_scholar', 'is_draft')
    search_fields = ('user__username', 'orcid_id', 'google_scholar_id')
    actions = ['sync_selected']
    
    class Media:
        css = {
            'all': ('css/admin.css',)
        }
        js = ('js/admin/sync_overlay.js',)

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if SystemConfig.is_chinese_enabled():
            return fields
        return tuple(f for f in fields if f not in ('bio_zh', 'address_zh'))

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        return _apply_zh_field_labels(form, {
            'display_name': '显示名称',
            'title': '职称',
            'institution': '机构',
            'bio': '简介',
            'bio_zh': '简介（中文）',
            'profile_image': '头像',
            'address': '地址',
            'address_zh': '地址（中文）',
            'email': '邮箱',
            'phone': '电话',
            'orcid_id': 'ORCID ID',
            'google_scholar_id': 'Google Scholar ID',
            'github_username': 'GitHub 用户名',
            'researchgate_url': 'ResearchGate 链接',
            'linkedin_url': 'LinkedIn 链接',
            'auto_sync_orcid': '自动同步 ORCID',
            'auto_sync_google_scholar': '自动同步 Google Scholar',
            'is_active': '启用',
            'is_draft': '草稿',
            'order': '排序',
        })
    
    def get_admin_display_name(self, obj):
        """获取管理界面显示名称"""
        return obj.display_name or obj.user.get_full_name() or obj.user.username
    get_admin_display_name.short_description = _('Display Name')
    get_admin_display_name.admin_order_field = 'display_name'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('sync/<int:profile_id>/', self.admin_site.admin_view(self.sync_publications), name='sync-publications'),
        ]
        return custom_urls + urls
    
    def sync_publications(self, request, profile_id):
        try:
            profile = Profile.objects.get(id=profile_id)
            imported_count = 0
            errors = []
            before_count = Publication.objects.count()
            
            # 获取同步间隔设置
            sync_interval = SystemConfig.objects.filter(
                category='sync_interval',
                is_active=True
            ).first()
            
            # 检查是否需要同步（仅当启用了自动同步时）
            if (profile.auto_sync_orcid or profile.auto_sync_google_scholar) and \
               sync_interval and profile.last_sync_time and \
               (timezone.now() - profile.last_sync_time).total_seconds() <= float(sync_interval.value) * 3600:
                messages.info(request, _('Time since last sync is less than the configured interval, but forced sync'))
            
            # 同步 ORCID 出版物
            if profile.orcid_id:
                try:
                    orcid_service = ORCIDService(profile.orcid_id)
                    imported_count += orcid_service.sync_publications(profile)
                except Exception as e:
                    error_msg = _('ORCID sync failed: %(error)s') % {'error': str(e)}
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            # 同步 Google Scholar 出版物
            if profile.google_scholar_id:
                try:
                    scholar_service = GoogleScholarService(profile.google_scholar_id)
                    imported_count += scholar_service.sync_publications(profile)
                except Exception as e:
                    error_msg = _('Google Scholar sync failed: %(error)s') % {'error': str(e)}
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            # 更新最后同步时间
            profile.last_sync_time = timezone.now()
            profile.save()
            
            # 显示所有错误信息
            for error in errors:
                messages.error(request, error)
            
            # Ensure duplicates are merged after sync
            dedupe_stats = deduplicate_publications()
            after_count = Publication.objects.count()
            net_new = max(after_count - before_count, 0)

            if net_new > 0:
                messages.success(
                    request,
                    _('Successfully synchronized %(count)d publications') % {'count': net_new}
                )
                if dedupe_stats.get("removed"):
                    messages.info(
                        request,
                        _('Deduplicated %(count)d entries') % {'count': dedupe_stats.get("removed", 0)}
                    )
            elif not errors:
                messages.info(request, _('No new publications to sync'))
                
        except Exception as e:
            logger.error(f"Sync failed: {str(e)}")
            messages.error(request, _('Sync failed: %(error)s') % {'error': str(e)})
        
        return HttpResponseRedirect(reverse('admin:myHomePage_profile_changelist'))
    
    def sync_status(self, obj):
        if not obj.last_sync_time:
            return format_html('<span class="sync-status never">{}</span>', _('Never synced'))
        
        now = timezone.now()
        time_diff = now - obj.last_sync_time
        
        # 获取同步间隔设置
        sync_interval = SystemConfig.objects.filter(
            category='sync_interval',
            is_active=True
        ).first()
        
        if sync_interval:
            try:
                interval_hours = float(sync_interval.value)
            except (ValueError, TypeError):
                interval_hours = 1.0
            if time_diff < timedelta(hours=interval_hours):
                status = _('Recently synced')
                status_class = 'recent'
            elif time_diff < timedelta(days=1):
                status = _('Synced today')
                status_class = 'today'
            else:
                status = _('Synced %(days)d days ago') % {'days': time_diff.days}
                status_class = 'old'
        else:
            if time_diff < timedelta(hours=1):
                status = _('Recently synced')
                status_class = 'recent'
            elif time_diff < timedelta(days=1):
                status = _('Synced today')
                status_class = 'today'
            else:
                status = _('Synced %(days)d days ago') % {'days': time_diff.days}
                status_class = 'old'

        last_time = timezone.localtime(obj.last_sync_time).strftime('%Y-%m-%d %H:%M')
        return format_html(
            '<span class="sync-status {}">{}</span> <span class="sync-time">({})</span>',
            status_class,
            status,
            last_time
        )
    
    sync_status.short_description = _('Sync Status')
    
    def actions_column(self, obj):
        if not (obj.orcid_id or obj.google_scholar_id):
            return format_html('<span class="sync-button disabled">{}</span>', _('Not configured'))
        
        return format_html(
            '<a href="{}" class="sync-button">{}</a>',
            reverse('admin:sync-publications', args=[obj.id]),
            _('Sync now')
        )
    
    actions_column.short_description = _('操作')
    
    def sync_selected(self, request, queryset):
        total_imported = 0
        before_count = Publication.objects.count()
        sync_interval = SystemConfig.objects.filter(
            category='sync_interval',
            is_active=True
        ).first()
        
        for profile in queryset:
            try:
                # 检查是否需要同步（仅当启用了自动同步时）
                if (profile.auto_sync_orcid or profile.auto_sync_google_scholar) and \
                   sync_interval and profile.last_sync_time and \
                   (timezone.now() - profile.last_sync_time).total_seconds() <= float(sync_interval.value) * 3600:
                    messages.info(request, _('Profile %(id)d: Time since last sync is less than the configured interval, but forced sync') % {'id': profile.id})
                
                imported_count = 0
                
                # 同步 ORCID 出版物
                if profile.orcid_id:
                    orcid_service = ORCIDService(profile.orcid_id)
                    imported_count += orcid_service.sync_publications(profile)
                
                # 同步 Google Scholar 出版物
                if profile.google_scholar_id:
                    scholar_service = GoogleScholarService(profile.google_scholar_id)
                    imported_count += scholar_service.sync_publications(profile)
                
                # 更新最后同步时间
                profile.last_sync_time = timezone.now()
                profile.save()
                
                total_imported += imported_count
            except Exception as e:
                logger.error(f"Sync failed (Profile {profile.id}): {str(e)}")
                messages.error(request, _('Sync failed (Profile %(id)d): %(error)s') % {'id': profile.id, 'error': str(e)})
        
        # Ensure duplicates are merged after batch sync
        dedupe_stats = deduplicate_publications()
        after_count = Publication.objects.count()
        net_new = max(after_count - before_count, 0)

        if net_new > 0:
            messages.success(
                request,
                _('Successfully synchronized %(count)d publications') % {'count': net_new}
            )
            if dedupe_stats.get("removed"):
                messages.info(
                    request,
                    _('Deduplicated %(count)d entries') % {'count': dedupe_stats.get("removed", 0)}
                )
    
    sync_selected.short_description = _('Sync selected profiles')

    def orcid_link(self, obj):
        if obj.orcid_id:
            return format_html(
                '<a href="https://orcid.org/{}" target="_blank" rel="noopener noreferrer">{}</a>',
                obj.orcid_id,
                obj.orcid_id
            )
        return '-'
    orcid_link.short_description = _('ORCID ID')
    
    def google_scholar_link(self, obj):
        if obj.google_scholar_id:
            return format_html(
                '<a href="https://scholar.google.com/citations?user={}" target="_blank" rel="noopener noreferrer">{}</a>',
                obj.google_scholar_id,
                obj.google_scholar_id
            )
        return '-'
    google_scholar_link.short_description = _('Google Scholar ID')

class PublicationAdminForm(forms.ModelForm):
    bibtex_input = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 10, 'class': 'vLargeTextField'}),
        required=False,
        label=_('BibTeX Input')
    )
    bibtex_file = forms.FileField(
        required=False,
        label=_('BibTeX File')
    )

    class Meta:
        model = Publication
        fields = '__all__'


class PublicationFileInline(admin.TabularInline):
    model = PublicationFile
    extra = 1
    fields = ('file', 'url', 'display_text', 'custom_display_text', 'is_active', 'order')
    verbose_name = _('File List')
    verbose_name_plural = _('File List')

    def get_formset(self, request, obj=None, **kwargs):
        self.verbose_name = '\u6587\u4ef6\u5217\u8868' if _is_zh_mode() else _('File List')
        self.verbose_name_plural = '\u6587\u4ef6\u5217\u8868' if _is_zh_mode() else _('File List')
        formset = super().get_formset(request, obj, **kwargs)
        if _is_zh_mode():
            for field_name, label in {
                'file': '\u6587\u4ef6',
                'url': '\u7eaf URL',
                'display_text': '\u9996\u9875\u663e\u793a\u6587\u5b57',
                'custom_display_text': '\u81ea\u5b9a\u4e49\u663e\u793a\u6587\u5b57',
                'is_active': '\u542f\u7528',
                'order': '\u6392\u5e8f',
            }.items():
                if field_name in formset.form.base_fields:
                    formset.form.base_fields[field_name].label = label
        return formset

class PublicationAdmin(DraftSaveMixin, BaseAdmin):
    form = PublicationAdminForm
    inlines = (PublicationFileInline,)
    list_display = ('title', 'get_formatted_authors', 'journal', 'year', 'is_active', 'is_draft', 'order')
    search_fields = ('title', 'authors', 'journal')
    list_filter = ('is_active', 'is_draft', 'year')
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('title', 'authors', 'journal', 'year', 'date', 'is_active', 'is_draft', 'order', 'image')
        }),
        (_('Detail Page'), {
            'fields': ('enable_detail', 'detail_content', 'detail_content_zh'),
            'description': _('Paste publication detail content here. Markdown is supported.')
        }),
        (_('Author Settings'), {
            'fields': ('highlighted_authors', 'corresponding_authors'),
            'description': _('Specify authors to highlight and mark as corresponding authors')
        }),
        (_('Links'), {
            'fields': ('doi', 'url')
        }),
        (_('BibTeX Information'), {
            'fields': ('bibtex_key', 'bibtex_type', 'raw_bibtex'),
            'classes': ('collapse',)
        }),
        (_('BibTeX Import'), {
            'fields': ('bibtex_input', 'bibtex_file'),
            'description': _('Paste BibTeX data or upload a BibTeX file to automatically fill the fields')
        }),
    )

    class Media:
        js = ('js/admin/publication_admin.js',)
        css = {
            'all': ('css/admin/publication_admin.css',)
        }

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        return _apply_zh_field_labels(form, {
            'title': '\u6807\u9898',
            'authors': '\u4f5c\u8005',
            'journal': '\u671f\u520a/\u4f1a\u8bae',
            'year': '\u5e74\u4efd',
            'month': '\u6708\u4efd',
            'day': '\u65e5',
            'date': '\u53d1\u8868\u65e5\u671f',
            'doi': 'DOI',
            'url': 'URL',
            'enable_detail': '\u5f00\u542f\u8be6\u60c5\u9875',
            'detail_content': '\u8be6\u60c5\u5185\u5bb9',
            'detail_content_zh': '\u8be6\u60c5\u5185\u5bb9\uff08\u4e2d\u6587\uff09',
            'image': '\u56fe\u7247',
            'highlighted_authors': '\u9ad8\u4eae\u4f5c\u8005',
            'corresponding_authors': '\u901a\u8baf\u4f5c\u8005',
            'bibtex_key': 'BibTeX \u952e',
            'bibtex_type': 'BibTeX \u7c7b\u578b',
            'raw_bibtex': '\u539f\u59cb BibTeX',
            'is_active': '\u542f\u7528',
            'is_draft': '\u8349\u7a3f',
            'order': '\u6392\u5e8f',
            'bibtex_input': 'BibTeX \u8f93\u5165',
            'bibtex_file': 'BibTeX \u6587\u4ef6',
        })

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if not SystemConfig.is_chinese_enabled():
            return _strip_zh_fields(fieldsets)
        if not _is_zh_mode():
            return fieldsets
        title_map = {
            'Basic Information': '\u57fa\u672c\u4fe1\u606f',
            'Detail Page': '\u8be6\u60c5\u9875',
            'Author Settings': '\u4f5c\u8005\u8bbe\u7f6e',
            'Links': '\u94fe\u63a5',
            'BibTeX Information': 'BibTeX \u4fe1\u606f',
            'BibTeX Import': 'BibTeX \u5bfc\u5165',
        }
        return tuple((title_map.get(str(title), title), opts) for title, opts in fieldsets)

    def get_formatted_authors(self, obj):
        return obj.get_formatted_authors()
    get_formatted_authors.short_description = _('Authors')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('preview-detail/', self.admin_site.admin_view(self.preview_detail), name='publication-preview-detail'),
            path('<path:object_id>/ai-providers/', self.admin_site.admin_view(self.ai_providers), name='publication-ai-providers'),
            path('<path:object_id>/generate-detail/', self.admin_site.admin_view(self.generate_detail), name='publication-generate-detail'),
            path('<path:object_id>/save-detail/', self.admin_site.admin_view(self.save_detail), name='publication-save-detail'),
            path('parse-bibtex/', self.admin_site.admin_view(self.parse_bibtex), name='parse-bibtex'),
            path('import-bibtex/', self.admin_site.admin_view(self.import_bibtex), name='import-bibtex'),
        ]
        return custom_urls + urls

    def preview_detail(self, request):
        if request.method != 'POST':
            return JsonResponse({'error': _('Unsupported request method')}, status=405)
        content = request.POST.get('content', '')
        html = markdown.markdown(escape(content), extensions=['extra']) if content else ''
        return JsonResponse({'html': html})

    def _detail_preview_html(self, content):
        return markdown.markdown(escape(content or ''), extensions=['extra']) if content else ''

    def _read_template_file(self, filename):
        path = os.path.join(settings.BASE_DIR, 'templates', filename)
        try:
            with open(path, 'r', encoding='utf-8') as handle:
                return handle.read()
        except Exception:
            return ''

    def _extract_pdf_text(self, file_path, max_chars=12000):
        if not file_path or not os.path.exists(file_path):
            return ''
        try:
            try:
                from pypdf import PdfReader
            except Exception:
                from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            chunks = []
            total = 0
            for page in getattr(reader, 'pages', []):
                try:
                    text = page.extract_text() or ''
                except Exception:
                    text = ''
                text = ' '.join(text.split())
                if not text:
                    continue
                chunks.append(text)
                total += len(text)
                if total >= max_chars:
                    break
            return ' '.join(chunks)[:max_chars]
        except Exception as exc:
            logger.warning('Failed to extract publication PDF text: %s', exc)
            return ''

    def _publication_ai_payload(self, publication, metadata):
        data = {
            'title': metadata.get('title') or publication.title,
            'authors': metadata.get('authors') or publication.authors,
            'journal': metadata.get('journal') or publication.journal,
            'year': metadata.get('year') or publication.year,
            'date': metadata.get('date') or publication.date,
            'doi': metadata.get('doi') or publication.doi,
            'url': metadata.get('url') or publication.url,
            'keywords': metadata.get('keywords') or publication.keywords,
            'raw_bibtex': metadata.get('raw_bibtex') or publication.raw_bibtex,
        }
        files = []
        pdf_chunks = []
        for item in publication.get_active_files():
            file_name = os.path.basename(item.file.name) if item.file else ''
            file_label = item.get_display_text()
            entry = {'label': file_label, 'file_name': file_name}
            if file_name.lower().endswith('.pdf') and item.file:
                pdf_text = self._extract_pdf_text(item.file.path)
                entry['extracted_text_chars'] = len(pdf_text)
                if pdf_text:
                    pdf_chunks.append('File: {} ({})\n{}'.format(file_name, file_label, pdf_text))
            files.append(entry)
        data['files'] = files
        data['pdf_text'] = '\n\n'.join(pdf_chunks)[:18000]
        return data

    def _parse_llm_detail_response(self, content):
        raw = (content or '').strip()
        if raw.startswith('```'):
            raw = raw.strip('`')
            raw = raw[4:].strip() if raw.lower().startswith('json') else raw.strip()
        try:
            data = json.loads(raw)
        except Exception:
            return {'en': raw, 'zh': ''}
        return {
            'en': str(data.get('detail_content') or data.get('en') or data.get('detail_content_en') or '').strip(),
            'zh': str(data.get('detail_content_zh') or data.get('zh') or '').strip(),
        }

    def ai_providers(self, request, object_id):
        if request.method != 'GET':
            return JsonResponse({'error': _('Unsupported request method')}, status=405)
        from .ai_services import check_ai_config
        results = []
        for item in AIConfig.objects.all().order_by('-is_default', 'name'):
            if not item.is_complete_for_text():
                continue
            checked = check_ai_config(item)
            if checked.get('ok') is True:
                results.append({
                    'id': item.pk,
                    'name': item.name,
                    'provider': item.provider,
                    'model_name': item.model_name,
                    'is_default': item.is_default,
                })
        return JsonResponse({'providers': results})

    def generate_detail(self, request, object_id):
        if request.method != 'POST':
            return JsonResponse({'error': _('Unsupported request method')}, status=405)
        publication = self.get_object(request, object_id)
        if publication is None:
            return JsonResponse({'error': _('Publication must be saved before AI generation.')}, status=404)
        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except Exception:
            payload = {}
        provider_id = payload.get('provider_id')
        if not provider_id:
            return JsonResponse({'error': _('Please select an LLM provider.')}, status=400)
        metadata = payload.get('metadata') if isinstance(payload.get('metadata'), dict) else {}
        feedback = (payload.get('feedback') or '').strip()
        previous = payload.get('previous') if isinstance(payload.get('previous'), dict) else {}
        source_data = self._publication_ai_payload(publication, metadata)
        template_zh = self._read_template_file('paper_introduction_framework.md')
        template_en = self._read_template_file('paper_introduction_framework_en.md')
        system_prompt = (
            'You are a rigorous research writing assistant. Generate publication detail content in Markdown. '
            'Return strict JSON only with keys "detail_content" and "detail_content_zh". '
            'Do not fabricate facts that are not supported by metadata or extracted file text; state uncertainty where needed.'
        )
        user_prompt = json.dumps({
            'task': 'Generate or revise homepage publication detail introduction.',
            'metadata': source_data,
            'english_template': template_en,
            'chinese_template': template_zh,
            'previous_result': previous,
            'user_feedback': feedback,
            'requirements': [
                'detail_content must be English Markdown.',
                'detail_content_zh must be Simplified Chinese Markdown.',
                'Use the provided templates as structure, but adapt to the actual paper.',
                'Prefer evidence from PDF text when available.',
            ],
        }, ensure_ascii=False)
        try:
            from .ai_services import generate_text_with_provider
            content = generate_text_with_provider(provider_id, system_prompt, user_prompt, temperature=0.2)
            parsed = self._parse_llm_detail_response(content)
        except Exception as exc:
            return JsonResponse({'error': str(exc)}, status=500)
        return JsonResponse({
            'detail_content': parsed['en'],
            'detail_content_zh': parsed['zh'],
            'html': self._detail_preview_html(parsed['en']),
            'html_zh': self._detail_preview_html(parsed['zh']),
        })

    def save_detail(self, request, object_id):
        if request.method != 'POST':
            return JsonResponse({'error': _('Unsupported request method')}, status=405)
        publication = self.get_object(request, object_id)
        if publication is None:
            return JsonResponse({'error': _('Publication does not exist.')}, status=404)
        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except Exception:
            payload = {}
        publication.detail_content = payload.get('detail_content') or ''
        publication.detail_content_zh = payload.get('detail_content_zh') or ''
        publication.enable_detail = True
        publication.save(update_fields=['detail_content', 'detail_content_zh', 'enable_detail', 'updated_at'])
        return JsonResponse({'ok': True})

    def _entry_to_raw_bibtex(self, entry):
        database = bibtexparser.bibdatabase.BibDatabase()
        database.entries = [entry]
        return bibtexparser.dumps(database).strip()

    def parse_bibtex(self, request):
        """Parse BibTeX data"""
        if not request.user.is_authenticated:
            return JsonResponse({'error': _('Please login first')}, status=401)
            
        if request.method != 'POST':
            return JsonResponse({'error': _('Unsupported request method')}, status=405)
            
        bibtex_data = request.POST.get('bibtex_text')
        if not bibtex_data:
            return JsonResponse({'error': _('No BibTeX data provided')}, status=400)
            
        try:
            # Parse BibTeX data
            parser = bibtexparser.bparser.BibTexParser(common_strings=True)
            bib_database = bibtexparser.loads(bibtex_data, parser=parser)
            
            if not bib_database.entries:
                return JsonResponse({'error': _('No valid BibTeX entries found')}, status=400)
                
            # Get first entry
            entry = bib_database.entries[0]
            logger.info('Parsed BibTeX entry: %s', entry)
            
            # Check for existing entry with same BibTeX key
            if 'ID' in entry:
                existing = Publication.objects.filter(bibtex_key=entry['ID']).first()
                if existing:
                    return JsonResponse({
                        'error': _('Entry with BibTeX key already exists: %(key)s') % {'key': entry['ID']},
                        'exists': True,
                        'bibtex_key': entry['ID'],
                        'id': existing.id
                    }, status=400)
            
            # Process date
            date = None
            if 'year' in entry:
                try:
                    if 'month' in entry:
                        date = datetime.strptime(f"{entry['year']}-{entry['month']}", "%Y-%b").date()
                    else:
                        date = datetime.strptime(f"{entry['year']}-01-01", "%Y-%m-%d").date()
                except ValueError:
                    date = datetime.now().date()
            
            # Process authors
            authors = entry.get('author', '')
            if authors:
                # Remove any LaTeX formatting
                authors = authors.replace('\\', '').strip('{}')
            
            # Process title
            title = entry.get('title', '')
            if title:
                title = title.replace('\\', '').strip('{}')
            
            # Process journal/booktitle
            journal = entry.get('journal', '') or entry.get('booktitle', '')
            if journal:
                journal = journal.replace('\\', '').strip('{}')
            
            # Process DOI
            doi = entry.get('doi', '')
            if doi:
                doi = doi.strip('{}')
            
            # Process URL
            url = entry.get('url', '')
            if not url and doi:
                url = f"https://doi.org/{doi}"
            
            # Process keywords
            keywords = entry.get('keywords', '').split(',') if 'keywords' in entry else []
            keywords = [k.strip() for k in keywords if k.strip()]
            
            # Prepare response data
            response_data = {
                'title': title,
                'authors': authors,
                'year': entry.get('year', ''),
                'journal': journal,
                'volume': entry.get('volume', ''),
                'number': entry.get('number', ''),
                'pages': entry.get('pages', ''),
                'publisher': entry.get('publisher', ''),
                'doi': doi,
                'url': url,
                'bibtex_type': entry.get('ENTRYTYPE', ''),
                'raw_bibtex': bibtex_data,
                'bibtex_key': entry.get('ID', ''),
                'date': date.strftime('%Y-%m-%d') if date else None,
                'keywords': ', '.join(keywords),
                'highlighted_authors': '',
                'corresponding_authors': ''
            }
            
            logger.info('Response data: %s', response_data)
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error('Failed to parse BibTeX data: %s', str(e), exc_info=True)
            return JsonResponse({'error': _('Failed to parse BibTeX data: %(error)s') % {'error': str(e)}}, status=400)

    def import_bibtex(self, request):
        """Import BibTeX data in batch"""
        if not request.user.is_authenticated:
            return JsonResponse({'error': _('Please login first')}, status=401)
            
        if request.method != 'POST':
            return JsonResponse({'error': _('Unsupported request method')}, status=405)
            
        # Get BibTeX data
        bibtex_data = None
        if 'bibtex_file' in request.FILES:
            bibtex_data = request.FILES['bibtex_file'].read().decode('utf-8')
        elif 'bibtex_text' in request.POST:
            bibtex_data = request.POST['bibtex_text']
            
        if not bibtex_data:
            return JsonResponse({'error': _('No BibTeX data provided')}, status=400)
            
        try:
            # Parse BibTeX data
            parser = bibtexparser.bparser.BibTexParser(common_strings=True)
            bib_database = bibtexparser.loads(bibtex_data, parser=parser)
            
            if not bib_database.entries:
                return JsonResponse({'error': _('No valid BibTeX entries found')}, status=400)
                
            # Process each entry
            imported = 0
            skipped = 0
            errors = []
            
            for entry in bib_database.entries:
                try:
                    # Check for existing entry
                    if 'ID' in entry:
                        existing = Publication.objects.filter(bibtex_key=entry['ID']).first()
                        if existing:
                            skipped += 1
                            errors.append(_('Skipped existing entry: %(key)s') % {'key': entry['ID']})
                            continue
                    
                    # Check for existing entry by DOI
                    doi = entry.get('doi', '')
                    if doi and Publication.objects.filter(doi=doi).exists():
                        skipped += 1
                        errors.append(_('Skipped existing entry with DOI: %(doi)s') % {'doi': doi})
                        continue
                    
                    # Process date
                    date = None
                    if 'year' in entry:
                        try:
                            if 'month' in entry:
                                date = datetime.strptime(f"{entry['year']}-{entry['month']}", "%Y-%b").date()
                            else:
                                date = datetime.strptime(f"{entry['year']}-01-01", "%Y-%m-%d").date()
                        except ValueError:
                            date = datetime.now().date()
                    
                    # Process keywords
                    keywords = entry.get('keywords', '').split(',') if 'keywords' in entry else []
                    keywords = [k.strip() for k in keywords if k.strip()]
                    
                    # Create new entry
                    publication = Publication(
                        title=entry.get('title', ''),
                        authors=entry.get('author', ''),
                        year=entry.get('year', ''),
                        journal=entry.get('journal', ''),
                        doi=entry.get('doi', ''),
                        url=entry.get('url', '') or (entry.get('doi', '') and f"https://doi.org/{entry['doi']}"),
                        bibtex_type=entry.get('ENTRYTYPE', ''),
                        raw_bibtex=self._entry_to_raw_bibtex(entry),
                        bibtex_key=entry.get('ID', ''),
                        date=date,
                        keywords=', '.join(keywords)
                    )
                    publication.save()
                    imported += 1
                    
                except Exception as e:
                    errors.append(_('Failed to process entry: %(error)s') % {'error': str(e)})
                    continue
            
            # Return import results
            message = _('Successfully imported %(count)d entries') % {'count': imported}
            if skipped > 0:
                message += _('; skipped %(count)d existing entries') % {'count': skipped}
            if errors:
                message += _('; %(count)d entries failed') % {'count': len(errors)}
                
            return JsonResponse({
                'success': True,
                'message': message,
                'imported': imported,
                'skipped': skipped,
                'errors': errors
            })
            
        except Exception as e:
            return JsonResponse({'error': _('Failed to import BibTeX data: %(error)s') % {'error': str(e)}}, status=400)

class ResearchAdmin(DraftSaveMixin, BaseAdmin):
    list_display = ('title', 'enable_detail', 'is_active', 'is_draft', 'order', 'start_date', 'end_date', 'is_current')
    search_fields = ('title', 'title_zh', 'summary', 'summary_zh', 'description', 'description_zh')
    list_filter = ('enable_detail', 'is_current', 'is_active', 'is_draft', 'start_date')
    date_hierarchy = 'start_date'
    fieldsets = (
        (_('Basic Information'), {
            'fields': (
                'title', 'title_zh',
                'summary', 'summary_zh',
                'description', 'description_zh',
                'enable_detail', 'is_active', 'is_draft', 'order'
            )
        }),
        (_('Timeline'), {
            'fields': ('start_date', 'end_date', 'is_current')
        }),
        (_('Media'), {
            'fields': ('image',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        return _apply_zh_field_labels(form, {
            'title': '\u6807\u9898',
            'title_zh': '\u6807\u9898\uff08\u4e2d\u6587\uff09',
            'summary': '\u6458\u8981',
            'summary_zh': '\u6458\u8981\uff08\u4e2d\u6587\uff09',
            'description': '\u63cf\u8ff0',
            'description_zh': '\u63cf\u8ff0\uff08\u4e2d\u6587\uff09',
            'enable_detail': '\u5f00\u542f\u8be6\u60c5\u9875',
            'start_date': '\u5f00\u59cb\u65f6\u95f4',
            'end_date': '\u7ed3\u675f\u65f6\u95f4',
            'is_current': '\u6b63\u5728\u8fdb\u884c',
            'image': '\u56fe\u7247',
            'is_active': '\u542f\u7528',
            'is_draft': '\u8349\u7a3f',
            'order': '\u6392\u5e8f',
        })

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if not SystemConfig.is_chinese_enabled():
            return _strip_zh_fields(fieldsets)
        return fieldsets

@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    form = SystemConfigAdminForm
    list_display = ('category_display', 'value', 'description_display', 'is_active')
    list_filter = (SystemConfigCategoryFilter, 'is_active')
    search_fields = ('category', 'value', 'description')

    change_form_template = 'admin/myHomePage/systemconfig/change_form.html'

    def _category_map(self):
        return _category_label_map()

    def _ensure_config_entries(self):
        expected = [choice[0] for choice in SystemConfig.CATEGORY_CHOICES]
        existing = set(SystemConfig.objects.values_list('category', flat=True))
        for category in expected:
            if category in existing:
                continue
            if category == 'sync_interval':
                default_value = '24'
            elif category == 'enable_chinese':
                default_value = '1'
            elif category == 'cards_per_page':
                default_value = '6'
            elif category == 'resource_log_retention_hours':
                default_value = '168'
            else:
                default_value = ''
            SystemConfig.objects.create(
                category=category,
                value=default_value,
                description='',
                is_active=True,
            )

    def category_display(self, obj):
        return self._category_map().get(obj.category, obj.category)
    category_display.short_description = _('Category')

    def description_display(self, obj):
        return self._category_map().get(obj.category, obj.description)
    description_display.short_description = _('Description')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'value' in form.base_fields:
            form.base_fields['value'].required = False
        if obj and obj.category == 'enable_chinese':
            enabled_label = '启用' if _is_zh_mode() else _('Enabled')
            disabled_label = '禁用' if _is_zh_mode() else _('Disabled')
            help_text = '控制是否在全站启用中文内容字段。' if _is_zh_mode() else _(
                'Control whether Chinese content fields are enabled across the site.'
            )
            form.base_fields['value'].widget = forms.RadioSelect(choices=(
                ('1', enabled_label),
                ('0', disabled_label),
            ))
            form.base_fields['value'].help_text = help_text
        if obj and obj.category == 'cards_per_page':
            form.base_fields['value'].help_text = (
                '设置首页每个栏目每页最多显示的卡片数量。'
                if _is_zh_mode()
                else _('Maximum number of cards displayed per page in each homepage section.')
            )
        if obj and obj.category == 'resource_log_retention_hours':
            form.base_fields['value'].help_text = (
                '\u8d44\u6e90\u76d1\u63a7\u5386\u53f2\u65e5\u5fd7\u4fdd\u7559\u65f6\u957f\uff08\u5c0f\u65f6\uff09\uff0c\u9ed8\u8ba4 168 \u5c0f\u65f6\u3002'
                if _is_zh_mode()
                else _('How long resource monitor logs are retained, in hours. Default is 168 hours.')
            )
        if obj and obj.category == 'scholar_proxy':
            form.base_fields['value'].help_text = _('Format: http://username:password@host:port or http://host:port')
        if obj and obj.category == 'footer_items':
            if _is_zh_mode():
                form.base_fields['value'].help_text = (
                    'JSON 格式：{"item":{"content":"Text","href":"https://example.com"}} '
                    '或 {"item":[{"content":"Text1"},{"content":"Text2","href":"https://example.com"}]}'
                )
            else:
                form.base_fields['value'].help_text = _(
                    'JSON format: {"item":{"content":"Text","href":"https://example.com"}} '
                    'or {"item":[{"content":"Text1"},{"content":"Text2","href":"https://example.com"}]}'
                )
        return _apply_zh_field_labels(form, {
            'category': '分类',
            'value': '值',
            'description': '描述',
            'is_active': '启用',
        })

    def save_model(self, request, obj, form, change):
        # Allow empty values for all categories except sync_interval, which defaults to 24 hours.
        value = (obj.value or '').strip()
        if obj.category == 'enable_chinese':
            value = '1' if str(value).strip().lower() in ('1', 'true', 'on', 'yes') else '0'
        if obj.category == 'cards_per_page':
            try:
                value = str(max(1, int(float(value or '6'))))
            except (ValueError, TypeError):
                value = '6'
        if obj.category == 'resource_log_retention_hours':
            try:
                value = str(max(1.0, float(value or '168')))
            except (ValueError, TypeError):
                value = '168'
        if obj.category == 'footer_items':
            value = _validate_footer_items_json(value)
        if obj.category == 'sync_interval' and not value:
            obj.value = '24'
        elif obj.category == 'enable_chinese' and not value:
            obj.value = '1'
        elif obj.category == 'cards_per_page' and not value:
            obj.value = '6'
        elif obj.category == 'resource_log_retention_hours' and not value:
            obj.value = '168'
        else:
            obj.value = value
        super().save_model(request, obj, form, change)

    class Media:
        js = ('js/admin/systemconfig_json_validate.js', 'js/admin/systemconfig_switch_category.js')
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('orcid-authorize/', self.admin_site.admin_view(self.orcid_authorize), name='orcid-authorize'),
        ]
        return custom_urls + urls
    
    def orcid_authorize(self, request):
        """触发 ORCID OAuth 授权"""
        try:
            oauth = ORCIDOAuth()
            # 使用不带语言前缀的回调 URL
            redirect_uri = request.build_absolute_uri('/orcid/callback/')
            auth_url = oauth.get_authorization_url(redirect_uri)
            logger.info('Redirecting to ORCID authorization URL: %s', auth_url)
            return redirect(auth_url)
        except ValueError as e:
            self.message_user(request, str(e), level=messages.ERROR)
            return redirect('admin:myHomePage_systemconfig_changelist')
    
    def changelist_view(self, request, extra_context=None):
        self._ensure_config_entries()
        extra_context = extra_context or {}
        extra_context['show_orcid_auth'] = True
        return super().changelist_view(request, extra_context=extra_context)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        self._ensure_config_entries()
        extra_context = extra_context or {}
        category_switch_map = {}
        for config in SystemConfig.objects.all().only('id', 'category'):
            category_switch_map[config.category] = reverse('admin:myHomePage_systemconfig_change', args=[config.id])
        current_category = ''
        if object_id:
            obj = self.get_object(request, object_id)
            if obj:
                current_category = obj.category
        extra_context['systemconfig_category_switch_map'] = category_switch_map
        extra_context['systemconfig_current_category'] = current_category
        return super().changeform_view(request, object_id, form_url, extra_context)


class AIConfigAdminForm(forms.ModelForm):
    class Meta:
        model = AIConfig
        fields = '__all__'

    def clean_config_json(self):
        return _validate_ai_config_json(self.cleaned_data.get('config_json', ''))


class AIConfigAdmin(admin.ModelAdmin):
    form = AIConfigAdminForm
    list_display = ('name', 'provider', 'model_name', 'base_url', 'check_status', 'test_link', 'is_default', 'is_active', 'updated_at')
    list_filter = ('provider', 'is_default', 'is_active', 'last_check_ok')
    search_fields = ('name', 'provider', 'model_name', 'base_url', 'description')
    readonly_fields = ('last_check_at', 'last_check_ok', 'last_check_message')
    actions = ('check_selected_availability',)
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'provider', 'model_name', 'base_url', 'api_key')
        }),
        (_('Advanced Configuration'), {
            'fields': ('config_json', 'description', 'is_default', 'is_active')
        }),
        (_('Availability Check'), {
            'fields': ('last_check_at', 'last_check_ok', 'last_check_message'),
            'classes': ('collapse',)
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'config_json' in form.base_fields:
            form.base_fields['config_json'].required = False
            form.base_fields['config_json'].help_text = (
                '\u004a\u0053\u004f\u004e \u683c\u5f0f\u3002\u793a\u4f8b\uff1a{"temperature":0.2,"max_tokens":2048}'
                if _is_zh_mode()
                else _('JSON format. Example: {"temperature":0.2,"max_tokens":2048}')
            )
        return _apply_zh_field_labels(form, {
            'name': '\u540d\u79f0',
            'provider': '\u63d0\u4f9b\u5546',
            'base_url': '\u0042\u0061\u0073\u0065 \u0055\u0052\u004c',
            'api_key': '\u0041\u0050\u0049 \u5bc6\u94a5',
            'model_name': '\u6a21\u578b',
            'config_json': '\u914d\u7f6e \u004a\u0053\u004f\u004e',
            'description': '\u63cf\u8ff0',
            'is_default': '\u9ed8\u8ba4',
            'is_active': '\u542f\u7528',
            'last_check_at': '\u4e0a\u6b21\u68c0\u6d4b\u65f6\u95f4',
            'last_check_ok': '\u4e0a\u6b21\u68c0\u6d4b\u7ed3\u679c',
            'last_check_message': '\u4e0a\u6b21\u68c0\u6d4b\u4fe1\u606f',
        })

    def save_model(self, request, obj, form, change):
        if obj.is_default:
            AIConfig.objects.exclude(pk=obj.pk).update(is_default=False)
        super().save_model(request, obj, form, change)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/check/',
                self.admin_site.admin_view(self.check_view),
                name='myHomePage_aiconfig_check',
            ),
            path(
                'check-all/',
                self.admin_site.admin_view(self.check_all_view),
                name='myHomePage_aiconfig_check_all',
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['ai_check_all_url'] = reverse('admin:myHomePage_aiconfig_check_all')
        return super().changelist_view(request, extra_context=extra_context)

    def check_status(self, obj):
        if obj.last_check_ok is True:
            label = '\u6b63\u5e38' if _is_zh_mode() else 'OK'
            color = '#15803d'
        elif obj.last_check_ok is False:
            label = '\u5931\u8d25' if _is_zh_mode() else 'Failed'
            color = '#b91c1c'
        else:
            label = '\u672a\u68c0\u6d4b' if _is_zh_mode() else 'Not checked'
            color = '#6b7280'
        return format_html('<span style="color:{};font-weight:700;">{}</span>', color, label)
    check_status.short_description = _('Availability')

    def test_link(self, obj):
        url = reverse('admin:myHomePage_aiconfig_check', args=[obj.pk])
        label = '\u68c0\u6d4b' if _is_zh_mode() else 'Test'
        return format_html('<a class="button" href="{}">{}</a>', url, label)
    test_link.short_description = _('Keep-alive Test')

    def _message_check_results(self, request, results):
        ok_count = sum(1 for item in results if item.get('ok') is True)
        skipped_count = sum(1 for item in results if item.get('ok') is None)
        failed = [item for item in results if item.get('ok') is False]
        if failed:
            detail = '; '.join('{}: {}'.format(item.get('name', ''), item.get('detail', '')) for item in failed[:3])
            messages.warning(
                request,
                _('%(ok)s provider(s) available, %(failed)s failed, %(skipped)s skipped. %(detail)s') % {
                    'ok': ok_count,
                    'failed': len(failed),
                    'skipped': skipped_count,
                    'detail': detail,
                }
            )
        else:
            messages.success(
                request,
                _('%(ok)s provider(s) available, %(skipped)s skipped.') % {
                    'ok': ok_count,
                    'skipped': skipped_count,
                }
            )

    def check_view(self, request, object_id):
        from .ai_services import check_ai_config
        obj = self.get_object(request, object_id)
        if obj is None:
            messages.error(request, _('AI Configuration does not exist.'))
            return redirect('admin:myHomePage_aiconfig_changelist')
        self._message_check_results(request, [check_ai_config(obj)])
        return redirect('admin:myHomePage_aiconfig_changelist')

    def check_all_view(self, request):
        from .ai_services import check_all_ai_configs
        self._message_check_results(request, check_all_ai_configs())
        return redirect('admin:myHomePage_aiconfig_changelist')

    def check_selected_availability(self, request, queryset):
        from .ai_services import check_all_ai_configs
        self._message_check_results(request, check_all_ai_configs(queryset))
    check_selected_availability.short_description = _('Run keep-alive test for selected AI configurations')

    class Media:
        js = ('js/admin/ai_config_json_validate.js',)

class NewsAdmin(DraftSaveMixin, BaseAdmin):
    list_display = ('title', 'enable_detail', 'is_active', 'is_draft', 'order', 'created_at', 'updated_at')
    list_filter = ('enable_detail', 'is_active', 'is_draft')
    search_fields = ('title', 'title_zh', 'summary', 'summary_zh', 'content', 'content_zh')
    ordering = ('-order', '-created_at')
    fieldsets = (
        (_('Basic Information'), {
            'fields': (
                'title', 'title_zh',
                'summary', 'summary_zh',
                'content', 'content_zh',
                'enable_detail', 'is_active', 'is_draft', 'order'
            )
        }),
        (_('Media'), {
            'fields': ('image',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if not SystemConfig.is_chinese_enabled():
            return _strip_zh_fields(fieldsets)
        return fieldsets

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        return _apply_zh_field_labels(form, {
            'title': '标题',
            'title_zh': '标题（中文）',
            'summary': '\u6458\u8981',
            'summary_zh': '\u6458\u8981\uff08\u4e2d\u6587\uff09',
            'content': '内容',
            'content_zh': '内容（中文）',
            'enable_detail': '\u5f00\u542f\u8be6\u60c5\u9875',
            'image': '图片',
            'is_active': '启用',
            'is_draft': '草稿',
            'order': '排序',
        })



class SectionItemInline(admin.TabularInline):
    model = SectionItem
    extra = 1
    fields = ('title', 'title_zh', 'content', 'content_zh', 'is_active', 'is_draft', 'order')
    ordering = ('order', 'id')

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if not SystemConfig.is_chinese_enabled():
            return tuple(f for f in fields if not str(f).endswith('_zh'))
        return fields

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if _is_zh_mode():
            label_map = {
                'title': '标题',
                'title_zh': '标题（中文）',
                'content': '内容',
                'content_zh': '内容（中文）',
                'is_active': '启用',
                'is_draft': '草稿',
                'order': '排序',
            }
            if db_field.name in label_map:
                formfield.label = label_map[db_field.name]
        return formfield


@admin.register(Section)
class SectionAdmin(DraftSaveMixin, BaseAdmin):
    list_display = ('title', 'order', 'is_active', 'is_draft', 'created_at', 'updated_at')
    inlines = (SectionItemInline,)
    list_filter = ('is_active', 'is_draft')
    search_fields = ('title', 'title_zh', 'content', 'content_zh')
    ordering = ('order', '-created_at')
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('title', 'title_zh', 'content', 'content_zh', 'is_active', 'is_draft', 'order')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        return _apply_zh_field_labels(form, {
            'title': '栏目标题',
            'title_zh': '栏目标题（中文）',
            'content': '栏目描述',
            'content_zh': '栏目描述（中文）',
            'is_active': '启用',
            'is_draft': '草稿',
            'order': '排序',
        })

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if not SystemConfig.is_chinese_enabled():
            return _strip_zh_fields(fieldsets)
        return fieldsets


@admin.register(MediaFile)
class MediaFileAdmin(DraftSaveMixin, BaseAdmin):
    list_display = ('title', 'file_url', 'markdown_link', 'is_active', 'is_draft', 'created_at')
    list_filter = ('is_active', 'is_draft')
    search_fields = ('title', 'file')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'file_url', 'markdown_link')
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('title', 'file', 'is_active', 'is_draft')
        }),
        (_('Markdown Usage'), {
            'fields': ('file_url', 'markdown_link'),
            'description': _('Copy the generated URL/Markdown and use it in markdown-enabled fields.')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def file_url(self, obj):
        if not obj.file or not obj.access_key:
            return '-'
        url = reverse('media_file_access', args=[obj.access_key])
        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>',
            url,
            url
        )
    file_url.short_description = _('File URL')

    def markdown_link(self, obj):
        if not obj.file or not obj.access_key:
            return '-'
        alt_text = obj.title or 'resource'
        lower_name = (obj.file.name or '').lower()
        access_url = reverse('media_file_access', args=[obj.access_key])
        if lower_name.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg')):
            markdown = '![{}]({})'.format(alt_text, access_url)
        else:
            markdown = '[{}]({})'.format(alt_text, access_url)
        return format_html('<code>{}</code>', markdown)
    markdown_link.short_description = _('Markdown Snippet')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'title' in form.base_fields:
            form.base_fields['title'].help_text = _('Leave empty to auto-fill from selected filename')
        return _apply_zh_field_labels(form, {
            'title': '标题',
            'file': '文件',
            'is_active': '启用',
            'is_draft': '草稿',
        })

    class Media:
        css = {'all': ('css/admin/mediafile_admin.css',)}
        js = ('js/admin/mediafile_admin.js',)

# Register models with the custom admin site
admin_site.register(Profile, ProfileAdmin)
admin_site.register(Publication, PublicationAdmin)
admin_site.register(Research, ResearchAdmin)
admin_site.register(SystemConfig, SystemConfigAdmin)
admin_site.register(AIConfig, AIConfigAdmin)
admin_site.register(News, NewsAdmin)
admin_site.register(Section, SectionAdmin)
admin_site.register(MediaFile, MediaFileAdmin)
