from django.shortcuts import get_object_or_404, render, redirect
from django.views import View
from .models import Profile, Publication, Research, News, Section, SystemConfig, MediaFile
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from .services import ORCIDOAuth
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.http import JsonResponse, Http404
from django.core.paginator import Paginator
import logging
import os

from django.views.static import serve as static_serve

logger = logging.getLogger(__name__)

def _safe_page(paginator, page_number):
    try:
        return paginator.page(page_number)
    except Exception:
        return paginator.page(1)


def _build_home_context(request=None):
    cards_per_page = SystemConfig.get_cards_per_page()
    is_chinese_page = False
    if request is not None:
        path = getattr(request, 'path', '') or ''
        is_chinese_page = path.startswith('/zh-hans/') or path.startswith('/zh-cn/')
    profile = Profile.objects.filter(is_active=True, is_draft=False).first()
    publications_qs = Publication.objects.filter(is_active=True, is_draft=False).order_by('-order', '-year')
    research_qs = Research.objects.filter(is_active=True, is_draft=False).order_by('-order')
    news_qs = News.objects.filter(is_active=True, is_draft=False).order_by('-order', '-created_at')
    sections = Section.objects.filter(is_active=True, is_draft=False).prefetch_related('items').order_by('-order')
    footer_items = SystemConfig.get_footer_items()

    pub_page_num = request.GET.get('pub_page', '1') if request else '1'
    research_page_num = request.GET.get('research_page', '1') if request else '1'
    news_page_num = request.GET.get('news_page', '1') if request else '1'

    publications_paginator = Paginator(publications_qs, cards_per_page)
    research_paginator = Paginator(research_qs, cards_per_page)
    news_paginator = Paginator(news_qs, cards_per_page)

    publications_page = _safe_page(publications_paginator, pub_page_num)
    research_page = _safe_page(research_paginator, research_page_num)
    news_page = _safe_page(news_paginator, news_page_num)

    has_contact_data = bool(
        profile and (
            profile.get_display_address() or profile.email or profile.phone or profile.orcid_id or
            profile.google_scholar_id or profile.github_username or
            profile.researchgate_url or profile.linkedin_url
        )
    )

    visible_sections = []
    for section in sections:
        all_items = [
            item for item in section.items.all()
            if item.is_active and not item.is_draft and (item.get_display_content() or item.get_display_title())
        ]
        if all_items:
            sec_page_num = request.GET.get('sec_{}_page'.format(section.id), '1') if request else '1'
            sec_paginator = Paginator(all_items, cards_per_page)
            section.visible_items_page = _safe_page(sec_paginator, sec_page_num)
            section.visible_items = section.visible_items_page.object_list
            visible_sections.append(section)

    return {
        'profile': profile,
        'is_chinese_page': is_chinese_page,
        'publications': publications_page.object_list,
        'research_list': research_page.object_list,
        'news_list': news_page.object_list,
        'publications_page': publications_page,
        'research_page': research_page,
        'news_page': news_page,
        'sections': visible_sections,
        'footer_items': footer_items,
        'show_about': bool(profile),
        'show_publications': publications_qs.exists(),
        'show_research': research_qs.exists(),
        'show_news': news_qs.exists(),
        'show_contact': has_contact_data,
        'show_custom_sections': bool(visible_sections),
        'cards_per_page': cards_per_page,
        'show_language_switcher': SystemConfig.is_chinese_enabled(),
    }


# Create your views here.
class Index(View):
    def get(self, request):
        return render(request, 'index.html', _build_home_context(request))

    def post(self, request):
        return render(request, 'index.html', _build_home_context(request))


def index(request):
    """Homepage view"""
    context = _build_home_context(request)
    return render(request, 'index.html', context)


def news_detail(request, pk):
    news = get_object_or_404(News, pk=pk, is_active=True, is_draft=False)
    context = _build_home_context(request)
    detail_news = list(
        News.objects.filter(is_active=True, is_draft=False)
        .order_by('-order', '-created_at', '-id')
    )
    current_index = next((idx for idx, item in enumerate(detail_news) if item.pk == news.pk), None)
    context['news'] = news
    context['previous_news'] = detail_news[current_index - 1] if current_index and current_index > 0 else None
    context['next_news'] = detail_news[current_index + 1] if current_index is not None and current_index + 1 < len(detail_news) else None
    return render(request, 'news_detail.html', context)


def research_detail(request, pk):
    research = get_object_or_404(Research, pk=pk, is_active=True, is_draft=False)
    context = _build_home_context(request)
    detail_research = list(
        Research.objects.filter(is_active=True, is_draft=False)
        .order_by('-order', '-start_date', '-id')
    )
    current_index = next((idx for idx, item in enumerate(detail_research) if item.pk == research.pk), None)
    context['research'] = research
    context['previous_research'] = detail_research[current_index - 1] if current_index and current_index > 0 else None
    context['next_research'] = detail_research[current_index + 1] if current_index is not None and current_index + 1 < len(detail_research) else None
    return render(request, 'research_detail.html', context)

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


def rsa_public_key(request):
    from .security import get_public_key_spki_b64
    return JsonResponse({"spki_b64": get_public_key_spki_b64()})


def media_file_access(request, access_key):
    try:
        media_file = MediaFile.objects.get(access_key=access_key)
    except MediaFile.DoesNotExist:
        raise Http404

    if not media_file.is_active:
        user = getattr(request, 'user', None)
        if not (user and user.is_authenticated and user.is_staff):
            return render(request, '403.html', status=403)

    if not media_file.file:
        raise Http404

    rel_path = media_file.file.name
    if not rel_path.startswith('markdown_assets/'):
        raise Http404
    return static_serve(request, rel_path.replace('markdown_assets/', '', 1), document_root=os.path.join(settings.MEDIA_ROOT, 'markdown_assets'))


def media_asset_access(request, path):
    rel_name = 'markdown_assets/' + path
    try:
        media_file = MediaFile.objects.get(file=rel_name)
    except MediaFile.DoesNotExist:
        raise Http404

    if not media_file.is_active:
        user = getattr(request, 'user', None)
        if not (user and user.is_authenticated and user.is_staff):
            return render(request, '403.html', status=403)

    return static_serve(request, path, document_root=os.path.join(settings.MEDIA_ROOT, 'markdown_assets'))
