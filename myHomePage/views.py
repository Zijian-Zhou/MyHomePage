from django.shortcuts import render, redirect
from django.views import View
from .models import Profile, Publication, Research, News, Section, SystemConfig
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from .services import ORCIDOAuth
from django.conf import settings
from django.contrib.auth.models import User, Group
import logging

logger = logging.getLogger(__name__)

# Create your views here.
class Index(View):
    def get(self, request):
        profile = Profile.objects.filter(is_active=True).first()
        publications = Publication.objects.filter(is_active=True).order_by('-year')
        research_list = Research.objects.filter(is_active=True).order_by('order')
        news_list = News.objects.filter(is_active=True).order_by('-created_at')
        sections = Section.objects.filter(is_active=True).order_by('order')
        
        context = {
            'profile': profile,
            'publications': publications,
            'research_list': research_list,
            'news_list': news_list,
            'sections': sections,
        }
        return render(request, 'index.html', context)

    def post(self, request):
        profile = Profile.objects.filter(is_active=True).first()
        publications = Publication.objects.filter(is_active=True).order_by('-year')
        research_list = Research.objects.filter(is_active=True).order_by('order')
        news_list = News.objects.filter(is_active=True).order_by('-created_at')
        sections = Section.objects.filter(is_active=True).order_by('order')
        
        context = {
            'profile': profile,
            'publications': publications,
            'research_list': research_list,
            'news_list': news_list,
            'sections': sections,
        }
        return render(request, 'index.html', context)

def index(request):
    """Homepage view"""
    profile = Profile.objects.filter(is_active=True).first()
    publications = Publication.objects.filter(is_active=True).order_by('-year')
    research_list = Research.objects.filter(is_active=True).order_by('order')
    news_list = News.objects.filter(is_active=True).order_by('-created_at')
    sections = Section.objects.filter(is_active=True).order_by('order')
    
    context = {
        'profile': profile,
        'publications': publications,
        'research_list': research_list,
        'news_list': news_list,
        'sections': sections,
    }
    return render(request, 'index.html', context)

@login_required
def orcid_authorize(request):
    """ORCID OAuth 授权视图"""
    try:
        oauth = ORCIDOAuth()
        redirect_uri = request.build_absolute_uri('/orcid/callback/')
        auth_url = oauth.get_authorization_url(redirect_uri)
        return redirect(auth_url)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('admin:index')

@login_required
def orcid_callback(request):
    """处理 ORCID OAuth 回调"""
    logger.info('Received ORCID callback request')
    logger.info('Request GET parameters: %s', request.GET)
    
    # 检查是否有错误
    if 'error' in request.GET:
        error_msg = request.GET.get('error_description', request.GET.get('error', 'Unknown error'))
        logger.error('ORCID authorization error: %s', error_msg)
        messages.error(request, _('ORCID authorization failed: %(error)s') % {'error': error_msg})
        return redirect('admin:index')
    
    # 获取授权码
    code = request.GET.get('code')
    if not code:
        logger.error('No authorization code received')
        messages.error(request, _('No authorization code received from ORCID'))
        return redirect('admin:index')
    
    try:
        # 获取访问令牌
        oauth = ORCIDOAuth()
        # 使用不带语言前缀的回调 URL
        redirect_uri = request.build_absolute_uri('/orcid/callback/')
        logger.info('Using redirect URI: %s', redirect_uri)
        access_token = oauth.get_access_token(code, redirect_uri)
        
        # 保存访问令牌
        SystemConfig.set_value(
            'orcid_access_token',
            access_token,
            'ORCID访问令牌'
        )
        
        logger.info('Successfully saved ORCID access token')
        messages.success(request, _('Successfully obtained ORCID access token'))
    except ValueError as e:
        logger.error('Failed to get access token: %s', str(e))
        messages.error(request, str(e))
    except Exception as e:
        logger.error('Unexpected error during ORCID callback: %s', str(e))
        messages.error(request, _('An unexpected error occurred during ORCID authorization'))
    
    return redirect('admin:index')

@login_required
@user_passes_test(lambda u: u.is_staff)
def user_management(request):
    users = User.objects.all().select_related('profile')
    groups = Group.objects.all()
    
    context = {
        'users': users,
        'groups': groups,
    }
    return render(request, 'admin/user_management.html', context)
