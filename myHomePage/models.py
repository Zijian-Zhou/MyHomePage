from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
import markdown

class Profile(models.Model):
    """用户个人资料模型"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    display_name = models.CharField(_('Display Name'), max_length=100, help_text=_('Name to be displayed on the homepage'), default='')
    title = models.CharField(max_length=100)
    institution = models.CharField(max_length=200)
    bio = models.TextField()
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)
    is_active = models.BooleanField(_('Active'), default=True)
    order = models.IntegerField(_('Order'), default=0)
    
    # 联系方式
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    
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
        ordering = ['order', '-created_at']

    def __str__(self):
        """返回原始显示名称，用于管理界面显示"""
        return self.display_name or self.user.get_full_name() or self.user.username
    
    def get_formatted_bio(self):
        """将 bio 字段的 Markdown 内容转换为 HTML"""
        if not self.bio:
            return ''
        return markdown.markdown(self.bio, extensions=['extra', 'codehilite'])
    
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
        ordering = ['-year', '-order']
        verbose_name = _('Publication')
        verbose_name_plural = _('Publications')

    def __str__(self):
        return self.title

    def get_formatted_authors(self):
        """Format authors with highlighting and corresponding author markers, including global highlighted authors from SystemConfig"""
        if not self.authors:
            return ''
        
        # Split authors and clean up
        author_list = [a.strip() for a in self.authors.split(' and ')]
        
        # Get highlighted and corresponding authors from entry
        highlighted = [a.strip() for a in self.highlighted_authors.split(';')] if self.highlighted_authors else []
        corresponding = [a.strip() for a in self.corresponding_authors.split(';')] if self.corresponding_authors else []
        
        # Get global highlighted authors from SystemConfig
        from .models import SystemConfig
        global_highlighted = []
        try:
            global_highlighted = [a.strip() for a in SystemConfig.get_highlighted_authors().split(';') if a.strip()]
        except Exception:
            pass
        # 合并去重
        all_highlighted = set(highlighted) | set(global_highlighted)
        
        # Format each author
        formatted_authors = []
        for author in author_list:
            author_name = author
            # Add highlighting if author is in highlighted list
            if author in all_highlighted:
                author_name = f'<strong>{author_name}</strong>'
            # Add corresponding author marker as superscript
            if author in corresponding:
                author_name = f'{author_name}<sup>*</sup>'
            formatted_authors.append(author_name)
        
        return ' and '.join(formatted_authors)

class Research(models.Model):
    """研究项目模型"""
    title = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_current = models.BooleanField(default=False)
    is_active = models.BooleanField(_('Active'), default=True)
    order = models.IntegerField(_('Order'), default=0)
    image = models.ImageField(upload_to='research_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-start_date']

    def __str__(self):
        return self.title

class SystemConfig(models.Model):
    """系统配置模型"""
    CATEGORY_CHOICES = [
        ('orcid_client_id', 'ORCID Client ID'),
        ('orcid_client_secret', 'ORCID Client Secret'),
        ('orcid_access_token', 'ORCID Access Token'),
        ('scholar_proxy', 'Google Scholar Proxy'),
        ('sync_interval', 'Sync Interval'),
        ('github_token', 'GitHub Token'),
        ('researchgate_token', 'ResearchGate Token'),
        ('linkedin_token', 'LinkedIn Token'),
        ('highlighted_authors', 'Highlighted Authors'),
    ]
    
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, verbose_name='Category')
    value = models.TextField(verbose_name='Value')
    description = models.TextField(verbose_name='Description', blank=True, help_text='Description of this configuration')
    is_active = models.BooleanField(default=True, verbose_name='Is Active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'System Configuration'
        verbose_name_plural = 'System Configurations'
        ordering = ['category', 'created_at']

    def __str__(self):
        return f"{self.get_category_display()}: {self.value}"

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
            return int(cls.get_value('sync_interval', 1))
        except (ValueError, TypeError):
            return 1  # Default 1 hour

    @classmethod
    def get_sync_interval_seconds(cls):
        """Get synchronization interval (seconds)"""
        return cls.get_sync_interval_hours() * 3600

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

class News(models.Model):
    """News model for sharing information"""
    title = models.CharField(_('Title'), max_length=200)
    content = models.TextField(_('Content'))
    image = models.ImageField(_('Image'), upload_to='news_images/', blank=True, null=True)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)
    is_active = models.BooleanField(_('Active'), default=True)
    order = models.IntegerField(_('Order'), default=0)

    class Meta:
        verbose_name = _('News')
        verbose_name_plural = _('News')
        ordering = ['-order', '-created_at']

    def __str__(self):
        return self.title

    def get_formatted_content(self):
        """将 content 字段的 Markdown 内容转换为 HTML"""
        if not self.content:
            return ''
        return markdown.markdown(self.content, extensions=['extra', 'codehilite'])

class Section(models.Model):
    title = models.CharField(_('Title'), max_length=200)
    content = models.TextField(_('Content'))
    order = models.IntegerField(_('Order'), default=0)
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)

    class Meta:
        verbose_name = _('Section')
        verbose_name_plural = _('Sections')
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title
