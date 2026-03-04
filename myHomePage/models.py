from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils.translation import get_language
from django.utils.html import escape
from django.utils.safestring import mark_safe
import markdown
import hashlib
import time


def _use_zh_content():
    lang = (get_language() or '').lower()
    try:
        return SystemConfig.is_chinese_enabled() and lang.startswith('zh')
    except Exception:
        return lang.startswith('zh')

class Profile(models.Model):
    """用户个人资料模型"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    display_name = models.CharField(_('Display Name'), max_length=100, help_text=_('Name to be displayed on the homepage'), default='')
    title = models.CharField(max_length=100)
    institution = models.CharField(max_length=200)
    bio = models.TextField()
    bio_zh = models.TextField(_('Bio (Chinese)'), blank=True, default='')
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)
    is_active = models.BooleanField(_('Active'), default=True)
    is_draft = models.BooleanField(_('Draft'), default=False)
    order = models.IntegerField(_('Order'), default=0)
    
    # 联系方式
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    address_zh = models.TextField(_('Address (Chinese)'), blank=True, default='')
    
    # 学术档案链接
    orcid_id = models.CharField(max_length=50, blank=True, help_text="ORCID ID (e.g., 0000-0000-0000-0000)")
    google_scholar_id = models.CharField(max_length=100, blank=True, help_text="Google Scholar ID")
    github_username = models.CharField(max_length=100, blank=True, help_text="GitHub Username")
    researchgate_url = models.URLField(blank=True, help_text="ResearchGate Profile URL")
    linkedin_url = models.URLField(blank=True, help_text="LinkedIn Profile URL")
    
    # 自动同步设置
    auto_sync_orcid = models.BooleanField(default=False, help_text=_("Automatically sync publications from ORCID"))
    auto_sync_google_scholar = models.BooleanField(default=False, help_text=_("Automatically sync publications from Google Scholar"))
    last_sync_time = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Profile')
        verbose_name_plural = _('Profiles')
        ordering = ['order', '-created_at']

    def __str__(self):
        """返回原始显示名称，用于管理界面显示"""
        return self.display_name or self.user.get_full_name() or self.user.username
    
    def get_formatted_bio(self):
        """Convert markdown bio to safe HTML (raw HTML is escaped)."""
        content = self.get_display_bio()
        if not content:
            return ''
        return markdown.markdown(escape(content), extensions=['extra'])

    def get_display_bio(self):
        if _use_zh_content() and self.bio_zh:
            return self.bio_zh
        return self.bio

    def get_display_address(self):
        if _use_zh_content() and self.address_zh:
            return self.address_zh
        return self.address
    
    def get_institutions(self):
        """获取机构列表，每个机构独占一行"""
        if not self.institution:
            return []
        return [inst.strip() for inst in self.institution.split(';') if inst.strip()]
    
    def get_display_names(self):
        """获取显示名称列表"""
        if not self.display_name:
            return []
        return [name.strip() for name in self.display_name.split(';') if name.strip()]
    
    def get_formatted_display_name(self):
        """获取格式化后的显示名称，英文名在前，其他名称在括号中"""
        names = self.get_display_names()
        if not names:
            return self.user.get_full_name() or self.user.username
        
        # 尝试找到英文名（假设英文名只包含英文字母和空格）
        english_name = None
        other_names = []
        
        for name in names:
            # 检查是否包含非英文字符
            if any(not c.isascii() for c in name):
                other_names.append(name)
            else:
                english_name = name
        
        if not english_name and names:
            english_name = names[0]
            other_names = names[1:]
        
        if other_names:
            return f"{english_name} ({', '.join(other_names)})"
        return english_name
    
    def get_html_title(self):
        """获取HTML标题"""
        return self.display_name or self.user.get_full_name() or self.user.username
    
    def get_admin_display_name(self):
        """获取管理界面显示名称"""
        return self.display_name or self.user.get_full_name() or self.user.username
        
    def get_orcid_url(self):
        """获取ORCID完整URL"""
        if self.orcid_id:
            return f"https://orcid.org/{self.orcid_id}"
        return None
        
    def get_google_scholar_url(self):
        """获取Google Scholar完整URL"""
        if self.google_scholar_id:
            return f"https://scholar.google.com/citations?user={self.google_scholar_id}"
        return None
        
    def get_github_url(self):
        """获取GitHub完整URL"""
        if self.github_username:
            return f"https://github.com/{self.github_username}"
        return None

class Publication(models.Model):
    """Publication model"""
    title = models.CharField(_('Title'), max_length=500)
    authors = models.TextField(_('Authors'))
    journal = models.CharField(_('Journal'), max_length=500)
    year = models.IntegerField(_('Year'), null=True, blank=True)
    month = models.IntegerField(_('Month'), null=True, blank=True, 
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text=_('Month (1-12)'))
    day = models.IntegerField(_('Day'), null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        help_text=_('Day (1-31)'))
    doi = models.CharField(_('DOI'), max_length=100, null=True, blank=True, default=None)
    url = models.URLField(_('URL'), blank=True)
    is_active = models.BooleanField(_('Active'), default=True)
    is_draft = models.BooleanField(_('Draft'), default=False)
    order = models.IntegerField(_('Order'), default=0)
    image = models.ImageField(_('Image'), upload_to='publication_images/', blank=True, null=True)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)
    
    # Author metadata
    highlighted_authors = models.TextField(_('Highlighted Authors'), blank=True,
        help_text=_('Comma-separated list of author names to be highlighted'))
    corresponding_authors = models.TextField(_('Corresponding Authors'), blank=True,
        help_text=_('Comma-separated list of corresponding author names'))
    bibtex_key = models.CharField(_('BibTeX Key'), max_length=200, blank=True, unique=True)
    raw_bibtex = models.TextField(_('Raw BibTeX'), blank=True)
    bibtex_type = models.CharField(_('BibTeX Type'), max_length=50, blank=True)
    date = models.DateField(_('Publication Date'), null=True, blank=True)
    keywords = models.TextField(_('Keywords'), blank=True, help_text=_('Keywords separated by commas'))

    class Meta:
        ordering = ['-order', '-year']
        verbose_name = _('Publication')
        verbose_name_plural = _('Publications')

    def __str__(self):
        return self.title

    def get_formatted_authors(self):
        """Render authors safely and only inject controlled markup tags."""
        if not self.authors:
            return ''

        author_list = [a.strip() for a in self.authors.split(' and ') if a.strip()]
        highlighted = {a.strip() for a in self.highlighted_authors.split(';') if a.strip()} if self.highlighted_authors else set()
        corresponding = {a.strip() for a in self.corresponding_authors.split(';') if a.strip()} if self.corresponding_authors else set()

        global_highlighted = set()
        try:
            global_highlighted = {a.strip() for a in SystemConfig.get_highlighted_authors().split(';') if a.strip()}
        except Exception:
            pass
        highlighted |= global_highlighted

        rendered = []
        for author in author_list:
            display_name = escape(author)
            if author in highlighted:
                display_name = f'<strong>{display_name}</strong>'
            if author in corresponding:
                display_name = f'{display_name}<sup>*</sup>'
            rendered.append(display_name)

        return mark_safe(' and '.join(rendered))

class Research(models.Model):
    """研究项目模型"""
    title = models.CharField(max_length=200)
    title_zh = models.CharField(_('Title (Chinese)'), max_length=200, blank=True, default='')
    description = models.TextField()
    description_zh = models.TextField(_('Description (Chinese)'), blank=True, default='')
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_current = models.BooleanField(default=False)
    is_active = models.BooleanField(_('Active'), default=True)
    is_draft = models.BooleanField(_('Draft'), default=False)
    order = models.IntegerField(_('Order'), default=0)
    image = models.ImageField(upload_to='research_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Research')
        verbose_name_plural = _('Researches')
        ordering = ['order', '-start_date']

    def __str__(self):
        return self.title

    def get_display_title(self):
        if _use_zh_content() and self.title_zh:
            return self.title_zh
        return self.title

    def get_display_description(self):
        if _use_zh_content() and self.description_zh:
            return self.description_zh
        return self.description

class SystemConfig(models.Model):
    """系统配置模型"""
    CATEGORY_CHOICES = [
        ('enable_chinese', _('Enable Chinese')),
        ('cards_per_page', _('Cards Per Page')),
        ('orcid_client_id', _('ORCID Client ID')),
        ('orcid_client_secret', _('ORCID Client Secret')),
        ('orcid_access_token', _('ORCID Access Token')),
        ('scholar_proxy', _('Google Scholar Proxy')),
        ('sync_interval', _('Sync Interval')),
        ('github_token', _('GitHub Token')),
        ('researchgate_token', _('ResearchGate Token')),
        ('linkedin_token', _('LinkedIn Token')),
        ('highlighted_authors', _('Highlighted Authors')),
        ('footer_items', _('Footer Items')),
    ]
    
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, verbose_name=_('Category'))
    value = models.TextField(verbose_name=_('Value'), blank=True, default='')
    description = models.TextField(verbose_name=_('Description'), blank=True, help_text=_('Description of this configuration'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('System Configuration')
        verbose_name_plural = _('System Configurations')
        ordering = ['category', 'created_at']

    def get_category_label(self):
        lang = (get_language() or '').lower()
        if lang.startswith('zh'):
            zh_labels = {
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
            return zh_labels.get(self.category, self.category)
        return self.get_category_display()

    def __str__(self):
        return f"{self.get_category_label()}: {self.value}"

    @classmethod
    def get_value(cls, category, default=None):
        """Get configuration value"""
        try:
            return cls.objects.get(category=category, is_active=True).value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set_value(cls, category, value, description=''):
        """Set configuration value"""
        config, created = cls.objects.update_or_create(
            category=category,
            defaults={
                'value': value,
                'description': description,
                'is_active': True
            }
        )
        return config

    @classmethod
    def get_sync_interval_hours(cls):
        """Get synchronization interval (hours)"""
        try:
            return float(cls.get_value('sync_interval', 24))
        except (ValueError, TypeError):
            return 24.0  # Default 24 hours

    @classmethod
    def get_sync_interval_seconds(cls):
        """Get synchronization interval (seconds)"""
        return int(cls.get_sync_interval_hours() * 3600)

    @classmethod
    def get_orcid_token(cls):
        """Get ORCID access token"""
        return cls.get_value('orcid_access_token', '')

    @classmethod
    def get_scholar_proxy(cls):
        """Get Google Scholar proxy"""
        return cls.get_value('scholar_proxy', '')

    @classmethod
    def migrate_old_configs(cls):
        """迁移旧配置"""
        old_configs = {
            'orcid_client_id': ('orcid', 'client_id'),
            'orcid_client_secret': ('orcid', 'client_secret'),
            'orcid_access_token': ('orcid', 'access_token'),
            'google_scholar_proxy': ('scholar', 'proxy'),
            'sync_interval': ('sync', 'interval'),
        }

        for old_category, (new_category, name) in old_configs.items():
            try:
                old_config = cls.objects.get(category=old_category)
                cls.set_value(
                    category=new_category,
                    value=old_config.value,
                    description=old_config.description
                )
                old_config.delete()
            except cls.DoesNotExist:
                pass

    @classmethod
    def get_github_token(cls):
        return cls.get_value('github_token', '')

    @classmethod
    def get_researchgate_token(cls):
        return cls.get_value('researchgate_token', '')

    @classmethod
    def get_linkedin_token(cls):
        return cls.get_value('linkedin_token', '')

    @classmethod
    def get_highlighted_authors(cls):
        return cls.get_value('highlighted_authors', '')

    @classmethod
    def get_footer_items(cls):
        """
        Parse footer item configuration from JSON.
        Expected base format:
        {
            "item": {"content": "...", "href": "..."}
        }
        Also supports a list in "item" for multiple entries.
        """
        raw = cls.get_value('footer_items', '')
        if not raw:
            return []

        try:
            import json
            data = json.loads(raw)
        except Exception:
            return []

        item_data = data.get('item')
        if isinstance(item_data, dict):
            item_data = [item_data]
        if not isinstance(item_data, list):
            return []

        items = []
        for entry in item_data:
            if not isinstance(entry, dict):
                continue
            content = str(entry.get('content', '')).strip()
            href = str(entry.get('href', '')).strip()
            if not content:
                continue
            items.append({
                'content': content,
                'href': href,
            })
        return items

    @classmethod
    def is_chinese_enabled(cls):
        value = str(cls.get_value('enable_chinese', '1')).strip().lower()
        return value not in ('0', 'false', 'off', 'no')

    @classmethod
    def get_cards_per_page(cls):
        try:
            value = int(float(cls.get_value('cards_per_page', 6)))
            return max(1, value)
        except (ValueError, TypeError):
            return 6

class News(models.Model):
    """News model for sharing information"""
    title = models.CharField(_('Title'), max_length=200)
    title_zh = models.CharField(_('Title (Chinese)'), max_length=200, blank=True, default='')
    content = models.TextField(_('Content'))
    content_zh = models.TextField(_('Content (Chinese)'), blank=True, default='')
    image = models.ImageField(_('Image'), upload_to='news_images/', blank=True, null=True)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)
    is_active = models.BooleanField(_('Active'), default=True)
    is_draft = models.BooleanField(_('Draft'), default=False)
    order = models.IntegerField(_('Order'), default=0)

    class Meta:
        verbose_name = _('News')
        verbose_name_plural = _('News')
        ordering = ['-order', '-created_at']

    def __str__(self):
        return self.title

    def get_display_title(self):
        if _use_zh_content() and self.title_zh:
            return self.title_zh
        return self.title

    def get_display_content(self):
        if _use_zh_content() and self.content_zh:
            return self.content_zh
        return self.content

    def get_formatted_content(self):
        """Convert markdown content to safe HTML (raw HTML is escaped)."""
        content = self.get_display_content()
        if not content:
            return ''
        return markdown.markdown(escape(content), extensions=['extra'])

class Section(models.Model):
    title = models.CharField(_('Title'), max_length=200)
    title_zh = models.CharField(_('Title (Chinese)'), max_length=200, blank=True, default='')
    content = models.TextField(_('Content'), blank=True)
    content_zh = models.TextField(_('Content (Chinese)'), blank=True, default='')
    order = models.IntegerField(_('Order'), default=0)
    is_active = models.BooleanField(_('Active'), default=True)
    is_draft = models.BooleanField(_('Draft'), default=False)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)

    class Meta:
        verbose_name = _('Section')
        verbose_name_plural = _('Sections')
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title

    def get_display_title(self):
        if _use_zh_content() and self.title_zh:
            return self.title_zh
        return self.title

    def get_display_content(self):
        if _use_zh_content() and self.content_zh:
            return self.content_zh
        return self.content

    def get_formatted_content(self):
        """Convert markdown content to safe HTML (raw HTML is escaped)."""
        content = self.get_display_content()
        if not content:
            return ''
        return markdown.markdown(escape(content), extensions=['extra'])


class SectionItem(models.Model):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='items', verbose_name=_('Section'))
    title = models.CharField(_('Title'), max_length=200, blank=True)
    title_zh = models.CharField(_('Title (Chinese)'), max_length=200, blank=True, default='')
    content = models.TextField(_('Content'))
    content_zh = models.TextField(_('Content (Chinese)'), blank=True, default='')
    is_active = models.BooleanField(_('Active'), default=True)
    is_draft = models.BooleanField(_('Draft'), default=False)
    order = models.IntegerField(_('Order'), default=0)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)

    class Meta:
        verbose_name = _('Section Item')
        verbose_name_plural = _('Section Items')
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title or self.section.title

    def get_display_title(self):
        if _use_zh_content() and self.title_zh:
            return self.title_zh
        return self.title

    def get_display_content(self):
        if _use_zh_content() and self.content_zh:
            return self.content_zh
        return self.content

    def get_formatted_content(self):
        """Convert markdown content to safe HTML (raw HTML is escaped)."""
        content = self.get_display_content()
        if not content:
            return ''
        return markdown.markdown(escape(content), extensions=['extra'])


class MediaFile(models.Model):
    title = models.CharField(_('Title'), max_length=200)
    file = models.FileField(_('File'), upload_to='markdown_assets/')
    access_key = models.CharField(max_length=64, unique=True, db_index=True, blank=True, default='')
    is_active = models.BooleanField(_('Active'), default=True)
    is_draft = models.BooleanField(_('Draft'), default=False)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)

    class Meta:
        verbose_name = _('Media File')
        verbose_name_plural = _('Media Files')
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def _build_access_key(self):
        ts = str(int(time.time() * 1000))
        h = hashlib.sha256()
        h.update(ts.encode('utf-8'))
        h.update(b'|')
        h.update((self.file.name or '').encode('utf-8'))
        h.update(b'|')
        try:
            if self.file:
                try:
                    current_pos = self.file.tell()
                except Exception:
                    current_pos = None
                if hasattr(self.file, 'seek'):
                    self.file.seek(0)
                chunk = self.file.read(1024 * 1024)
                if current_pos is not None and hasattr(self.file, 'seek'):
                    self.file.seek(current_pos)
                h.update(chunk or b'')
        except Exception:
            # Fall back to filename/timestamp based hash when file stream is unavailable.
            pass
        return h.hexdigest()

    def save(self, *args, **kwargs):
        if not self.access_key:
            candidate = self._build_access_key()
            while MediaFile.objects.filter(access_key=candidate).exists():
                candidate = self._build_access_key()
            self.access_key = candidate
        super().save(*args, **kwargs)
