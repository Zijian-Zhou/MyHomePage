from django.contrib import admin
from django.urls import path
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils.translation import get_language
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta, datetime
from .models import Profile, Publication, Research, SystemConfig, News, Section, SectionItem, MediaFile
from .services import sync_publications, ORCIDService, GoogleScholarService, ORCIDOAuth, deduplicate_publications
from django.contrib.auth.decorators import user_passes_test
from django.contrib.admin.sites import AdminSite
from django.template.response import TemplateResponse
from django import forms
from django.contrib.auth.models import User, Group
import bibtexparser
import json
import logging
from django.shortcuts import redirect

logger = logging.getLogger(__name__)


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

    def each_context(self, request):
        context = super().each_context(request)
        context['dark_mode'] = request.session.get('dark_mode', False)
        context['site_title'] = _('HomePage Administration')
        context['site_header'] = _('HomePage Administration')
        context['index_title'] = _('HomePage Administration')
        context['footer_items'] = SystemConfig.get_footer_items()
        context['show_language_switcher'] = SystemConfig.is_chinese_enabled()
        return context

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
            'news': _('News'),
            'section': _('Custom Sections'),
            'mediafile': _('Media Files'),
        }

        app_list = super().get_app_list(request)
        for app in app_list:
            if app.get('app_label') == 'myHomePage':
                app['name'] = _('Homepage Content')
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

class PublicationAdmin(DraftSaveMixin, BaseAdmin):
    form = PublicationAdminForm
    list_display = ('title', 'get_formatted_authors', 'journal', 'year', 'is_active', 'is_draft', 'order')
    search_fields = ('title', 'authors', 'journal')
    list_filter = ('is_active', 'is_draft', 'year')
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('title', 'authors', 'journal', 'year', 'date', 'is_active', 'is_draft', 'order', 'image')
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
            'title': '标题',
            'authors': '作者',
            'journal': '期刊/会议',
            'year': '年份',
            'date': '发表日期',
            'doi': 'DOI',
            'url': 'URL',
            'image': '图片',
            'highlighted_authors': '高亮作者',
            'corresponding_authors': '通讯作者',
            'bibtex_key': 'BibTeX 键',
            'bibtex_type': 'BibTeX 类型',
            'raw_bibtex': '原始 BibTeX',
            'is_active': '启用',
            'is_draft': '草稿',
            'order': '排序',
            'bibtex_input': 'BibTeX 输入',
            'bibtex_file': 'BibTeX 文件',
        })

    def get_formatted_authors(self, obj):
        return obj.get_formatted_authors()
    get_formatted_authors.short_description = _('Authors')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('parse-bibtex/', self.admin_site.admin_view(self.parse_bibtex), name='parse-bibtex'),
            path('import-bibtex/', self.admin_site.admin_view(self.import_bibtex), name='import-bibtex'),
        ]
        return custom_urls + urls

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
    list_display = ('title', 'is_active', 'is_draft', 'order', 'start_date', 'end_date', 'is_current')
    search_fields = ('title', 'title_zh', 'description', 'description_zh')
    list_filter = ('is_current', 'is_active', 'is_draft', 'start_date')
    date_hierarchy = 'start_date'
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('title', 'title_zh', 'description', 'description_zh', 'is_active', 'is_draft', 'order')
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
            'title': '标题',
            'title_zh': '标题（中文）',
            'description': '描述',
            'description_zh': '描述（中文）',
            'start_date': '开始时间',
            'end_date': '结束时间',
            'is_current': '正在进行',
            'image': '图片',
            'is_active': '启用',
            'is_draft': '草稿',
            'order': '排序',
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
        if obj.category == 'footer_items':
            value = _validate_footer_items_json(value)
        if obj.category == 'sync_interval' and not value:
            obj.value = '24'
        elif obj.category == 'enable_chinese' and not value:
            obj.value = '1'
        elif obj.category == 'cards_per_page' and not value:
            obj.value = '6'
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

class NewsAdmin(DraftSaveMixin, BaseAdmin):
    list_display = ('title', 'is_active', 'is_draft', 'order', 'created_at', 'updated_at')
    list_filter = ('is_active', 'is_draft')
    search_fields = ('title', 'title_zh', 'content', 'content_zh')
    ordering = ('-order', '-created_at')
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('title', 'title_zh', 'content', 'content_zh', 'is_active', 'is_draft', 'order')
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
            'content': '内容',
            'content_zh': '内容（中文）',
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
admin_site.register(News, NewsAdmin)
admin_site.register(Section, SectionAdmin)
admin_site.register(MediaFile, MediaFileAdmin)
