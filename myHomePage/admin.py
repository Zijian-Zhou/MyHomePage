from django.contrib import admin
from django.urls import path
from django.http import HttpResponseRedirect, JsonResponse
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta, datetime
from .models import Profile, Publication, Research, SystemConfig, News, Section
from .services import sync_publications, ORCIDService, GoogleScholarService, ORCIDOAuth
from django.contrib.auth.decorators import user_passes_test
from django.contrib.admin.sites import AdminSite
from django.template.response import TemplateResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django import forms
from django.contrib.auth.models import User, Group
import bibtexparser
import json
import logging
from django.shortcuts import redirect

logger = logging.getLogger(__name__)

def is_staff_user(user):
    return user.is_authenticated and user.is_staff

class CustomAdminSite(AdminSite):
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
        app_list = super().get_app_list(request)
        for app in app_list:
            for model in app['models']:
                info = (app['app_label'], model['object_name'].lower())
                try:
                    model['admin_url'] = reverse(f'admin:{info[0]}_{info[1]}_changelist')
                except:
                    continue
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
class BaseAdmin(admin.ModelAdmin):
    class Media:
        css = {
            'all': ('css/admin/custom.css', 'css/admin/dark_mode.css')
        }
        js = ('js/admin/dark_mode.js',)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('get_admin_display_name', 'orcid_link', 'google_scholar_link', 'sync_status', 'actions_column')
    list_filter = ('auto_sync_orcid', 'auto_sync_google_scholar')
    search_fields = ('user__username', 'orcid_id', 'google_scholar_id')
    actions = ['sync_selected']
    
    class Media:
        css = {
            'all': ('css/admin.css',)
        }
    
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
            
            # 获取同步间隔设置
            sync_interval = SystemConfig.objects.filter(
                category='sync_interval',
                is_active=True
            ).first()
            
            # 检查是否需要同步（仅当启用了自动同步时）
            if (profile.auto_sync_orcid or profile.auto_sync_google_scholar) and \
               sync_interval and profile.last_sync_time and \
               (timezone.now() - profile.last_sync_time).total_seconds() <= int(sync_interval.value) * 3600:
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
            
            if imported_count > 0:
                messages.success(request, _('Successfully synchronized %(count)d publications') % {'count': imported_count})
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
            interval_hours = int(sync_interval.value)
            if time_diff < timedelta(hours=interval_hours):
                return format_html('<span class="sync-status recent">{}</span>', _('Recently synced'))
            elif time_diff < timedelta(days=1):
                return format_html('<span class="sync-status today">{}</span>', _('Synced today'))
            else:
                return format_html('<span class="sync-status old">{}</span>', 
                    _('Synced %(days)d days ago') % {'days': time_diff.days})
        else:
            if time_diff < timedelta(hours=1):
                return format_html('<span class="sync-status recent">{}</span>', _('Recently synced'))
            elif time_diff < timedelta(days=1):
                return format_html('<span class="sync-status today">{}</span>', _('Synced today'))
            else:
                return format_html('<span class="sync-status old">{}</span>', 
                    _('Synced %(days)d days ago') % {'days': time_diff.days})
    
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
        sync_interval = SystemConfig.objects.filter(
            category='sync_interval',
            is_active=True
        ).first()
        
        for profile in queryset:
            try:
                # 检查是否需要同步（仅当启用了自动同步时）
                if (profile.auto_sync_orcid or profile.auto_sync_google_scholar) and \
                   sync_interval and profile.last_sync_time and \
                   (timezone.now() - profile.last_sync_time).total_seconds() <= int(sync_interval.value) * 3600:
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
        
        if total_imported > 0:
            messages.success(request, _('Successfully synchronized %(count)d publications') % {'count': total_imported})
    
    sync_selected.short_description = _('Sync selected profiles')

    def orcid_link(self, obj):
        if obj.orcid_id:
            return format_html(
                '<a href="https://orcid.org/{}" target="_blank">{}</a>',
                obj.orcid_id,
                obj.orcid_id
            )
        return '-'
    orcid_link.short_description = _('ORCID ID')
    
    def google_scholar_link(self, obj):
        if obj.google_scholar_id:
            return format_html(
                '<a href="https://scholar.google.com/citations?user={}" target="_blank">{}</a>',
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

class PublicationAdmin(BaseAdmin):
    form = PublicationAdminForm
    list_display = ('title', 'get_formatted_authors', 'journal', 'year', 'is_active', 'order')
    search_fields = ('title', 'authors', 'journal')
    list_filter = ('is_active', 'year')
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('title', 'authors', 'journal', 'year', 'date', 'is_active', 'order', 'image')
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

    def get_formatted_authors(self, obj):
        return format_html(obj.get_formatted_authors())
    get_formatted_authors.short_description = _('Authors')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('parse-bibtex/', self.admin_site.admin_view(self.parse_bibtex), name='parse-bibtex'),
            path('import-bibtex/', self.admin_site.admin_view(self.import_bibtex), name='import-bibtex'),
        ]
        return custom_urls + urls

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
                'keywords': keywords,
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
                        raw_bibtex=bibtexparser.dumps(bib_database),
                        bibtex_key=entry.get('ID', ''),
                        date=date,
                        keywords=keywords
                    )
                    publication.save()
                    imported += 1
                    
                except Exception as e:
                    errors.append(_('Failed to process entry: %(error)s') % {'error': str(e)})
                    continue
            
            # Return import results
            message = _('Successfully imported %(count)d entries') % {'count': imported}
            if skipped > 0:
                message += _('，skipped %(count)d existing entries') % {'count': skipped}
            if errors:
                message += _('，%(count)d entries failed') % {'count': len(errors)}
                
            return JsonResponse({
                'success': True,
                'message': message,
                'imported': imported,
                'skipped': skipped,
                'errors': errors
            })
            
        except Exception as e:
            return JsonResponse({'error': _('Failed to import BibTeX data: %(error)s') % {'error': str(e)}}, status=400)

class ResearchAdmin(BaseAdmin):
    list_display = ('title', 'is_active', 'order', 'start_date', 'end_date', 'is_current')
    search_fields = ('title', 'description')
    list_filter = ('is_current', 'is_active', 'start_date')
    date_hierarchy = 'start_date'
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('title', 'description', 'is_active', 'order')
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

@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ('category', 'value', 'description', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('category', 'value', 'description')
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.category == 'scholar_proxy':
            form.base_fields['value'].help_text = _('Format: http://username:password@host:port or http://host:port')
        return form
    
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
        extra_context = extra_context or {}
        extra_context['show_orcid_auth'] = True
        return super().changelist_view(request, extra_context=extra_context)

class NewsAdmin(BaseAdmin):
    list_display = ('title', 'is_active', 'order', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'content')
    ordering = ('-order', '-created_at')
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('title', 'content', 'is_active', 'order')
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
        form.base_fields['title'].label = _('Title')
        form.base_fields['content'].label = _('Content')
        return form

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'content')
    ordering = ('order', '-created_at')
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('title', 'content', 'is_active', 'order')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

# Register models with the custom admin site
admin_site.register(Profile, ProfileAdmin)
admin_site.register(Publication, PublicationAdmin)
admin_site.register(Research, ResearchAdmin)
admin_site.register(SystemConfig, SystemConfigAdmin)
admin_site.register(News, NewsAdmin)
