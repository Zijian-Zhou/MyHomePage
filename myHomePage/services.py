import requests
from datetime import datetime
from django.utils import timezone
from .models import Publication, SystemConfig
import bibtexparser
from bs4 import BeautifulSoup
import re
import logging
from django.utils.translation import gettext_lazy as _
import json
from urllib.parse import urlencode
import time
import random

logger = logging.getLogger(__name__)


def _request_without_env_proxy(method, url, **kwargs):
    session = requests.Session()
    session.trust_env = False
    return session.request(method, url, **kwargs)


class ORCIDOAuth:
    """ORCID OAuth 认证处理"""
    
    def __init__(self):
        self.client_id = SystemConfig.get_value('orcid_client_id')
        self.client_secret = SystemConfig.get_value('orcid_client_secret')
        if not self.client_id or not self.client_secret:
            raise ValueError(_('ORCID Client ID and Client Secret must be configured first'))
        self.base_url = 'https://orcid.org'
        self.token_url = f'{self.base_url}/oauth/token'
        logger.info('ORCIDOAuth initialized with client_id: %s', self.client_id)
    
    def get_authorization_url(self, redirect_uri):
        """获取授权 URL"""
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'scope': '/authenticate',
            'redirect_uri': redirect_uri,
        }
        auth_url = f'{self.base_url}/oauth/authorize?{urlencode(params)}'
        logger.info('Generated authorization URL: %s', auth_url)
        return auth_url
    
    def get_access_token(self, code, redirect_uri):
        """使用授权码获取访问令牌"""
        try:
            logger.info('Attempting to get access token with code: %s', code)
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': redirect_uri,
            }
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            # 禁用代理，直接连接 ORCID
            response = _request_without_env_proxy('POST', self.token_url, data=data, headers=headers, timeout=30)
            response.raise_for_status()
            token_data = response.json()
            logger.info('Successfully obtained access token')
            return token_data.get('access_token')
        except requests.exceptions.RequestException as e:
            logger.error('Failed to get access token: %s', str(e))
            if hasattr(e.response, 'text'):
                logger.error('Response content: %s', e.response.text)
            raise ValueError(_('Failed to get ORCID access token: %(error)s') % {'error': str(e)})

class ORCIDService:
    """ORCID API服务"""
    BASE_URL = "https://pub.orcid.org/v3.0"
    
    def __init__(self, orcid_id):
        self.orcid_id = orcid_id
        self.access_token = SystemConfig.get_orcid_token()
        if not self.access_token:
            error_msg = _("ORCID access token not configured. Please complete OAuth authorization first by clicking the 'Authorize ORCID' button in the system configuration page.")
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        self.headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }
        # 使用与 Google Scholar 相同的代理配置
        self.proxy = SystemConfig.get_scholar_proxy()
        if not self.proxy:
            logger.warning("No proxy configured for ORCID. Requests may be blocked.")
        else:
            logger.info(f"Using proxy for ORCID: {self.proxy}")
        logger.info(f"Initialized ORCIDService for ORCID ID: {orcid_id}")

    def _request_orcid(self, url):
        # Prefer proxy if configured, then fall back to direct connection.
        attempts = []
        if self.proxy:
            attempts.append(("proxy", {'http': self.proxy, 'https': self.proxy}))
        # Force-disable environment proxy variables for direct mode
        attempts.append(("direct", {'http': None, 'https': None}))

        last_error = None
        for mode, proxies in attempts:
            try:
                logger.info(f"Requesting ORCID via {mode}: {url}")
                response = (_request_without_env_proxy('GET', url, headers=self.headers, timeout=30)
                            if mode == 'direct' else
                            requests.get(url, headers=self.headers, proxies=proxies, timeout=30))
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                last_error = e
                logger.warning(f"ORCID request failed via {mode}: {str(e)}")
        raise last_error
    
    def get_works(self):
        """获取ORCID作品列表"""
        url = f"{self.BASE_URL}/{self.orcid_id}/works"
        try:
            logger.info(f"Fetching works from ORCID API: {url}")
            response = self._request_orcid(url)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Successfully fetched {len(data.get('group', []))} works from ORCID")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching ORCID works: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response content: {e.response.text}")
            raise
    
    def get_work_details(self, put_code):
        """获取作品详细信息"""
        url = f"{self.BASE_URL}/{self.orcid_id}/work/{put_code}"
        try:
            logger.info(f"Fetching work details from ORCID API: {url}")
            response = self._request_orcid(url)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Successfully fetched work details for put_code: {put_code}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching ORCID work details: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response content: {e.response.text}")
            return None
    
    def sync_publications(self, profile=None):
        """同步ORCID出版物"""
        logger.info(f"Starting ORCID sync for ORCID ID: {self.orcid_id}")
        works = self.get_works()
        if not works or not isinstance(works, dict):
            logger.warning("Invalid works response from ORCID")
            return 0
        
        imported_count = 0
        for group in works.get('group', []):
            try:
                if not isinstance(group, dict) or 'work-summary' not in group:
                    logger.warning("Invalid work group format")
                    continue
                    
                work_summaries = group.get('work-summary', [])
                if not work_summaries or not isinstance(work_summaries, list) or len(work_summaries) == 0:
                    logger.warning("No work summaries found in group")
                    continue
                    
                work_summary = work_summaries[0]
                if not isinstance(work_summary, dict):
                    logger.warning("Invalid work summary format")
                    continue
                    
                put_code = work_summary.get('put-code')
                if not put_code:
                    logger.warning("No put-code found in work summary")
                    continue
                
                # Always fetch details so existing entries can be enriched.
                
                # 获取完整的作品详情
                work_details = self.get_work_details(put_code)
                if not work_details:
                    logger.warning(f"Failed to get work details for put_code {put_code}")
                    continue
                
                # 从 work_details 中提取数据
                title_dict = work_details.get('title', {})
                if not isinstance(title_dict, dict):
                    logger.warning(f"Invalid title format for work {put_code}")
                    continue
                    
                title_value = title_dict.get('title', {})
                if not isinstance(title_value, dict):
                    logger.warning(f"Invalid title value format for work {put_code}")
                    continue
                    
                title = title_value.get('value', '')
                if not title:  # 跳过没有标题的作品
                    logger.warning(f"Work with put_code {put_code} has no title, skipping")
                    continue
                    
                # 处理日期
                publication_date = work_details.get('publication-date', {})
                if not isinstance(publication_date, dict):
                    logger.warning(f"Invalid publication date format for work {put_code}")
                    continue
                    
                year_dict = publication_date.get('year', {})
                if not isinstance(year_dict, dict):
                    logger.warning(f"Invalid year format for work {put_code}")
                    continue
                    
                year = year_dict.get('value')
                
                # 安全地获取月份和日期
                month = '1'  # 默认值
                day = '1'    # 默认值
                
                month_dict = publication_date.get('month')
                if month_dict and isinstance(month_dict, dict):
                    month_value = month_dict.get('value')
                    if month_value:
                        month = month_value
                
                day_dict = publication_date.get('day')
                if day_dict and isinstance(day_dict, dict):
                    day_value = day_dict.get('value')
                    if day_value:
                        day = day_value
                
                # 处理外部ID
                external_ids_dict = work_details.get('external-ids', {})
                if not isinstance(external_ids_dict, dict):
                    logger.warning(f"Invalid external IDs format for work {put_code}")
                    continue
                    
                external_ids = external_ids_dict.get('external-id', [])
                if not isinstance(external_ids, list):
                    logger.warning(f"Invalid external ID list format for work {put_code}")
                    continue
                    
                # 获取 DOI 和其他标识符
                doi = None
                url = ''
                for external_id in external_ids:
                    id_type = external_id.get('external-id-type')
                    id_value = external_id.get('external-id-value')
                    if id_type == 'doi':
                        doi = id_value
                    elif id_type == 'url':
                        url = id_value
                
                # 如果没有 URL 但有 DOI，从 DOI 生成 URL
                if not url and doi:
                    url = f"https://doi.org/{doi}"
                
                # Existing records are merged after details are extracted.
                
                # 获取作者信息
                contributors = work_details.get('contributors', {}).get('contributor', [])
                authors = []
                
                # 处理贡献者
                for contributor in contributors:
                    contributor_orcid = contributor.get('contributor-orcid', {})
                    credit_name = contributor.get('credit-name', {}).get('value', '')
                    if credit_name:
                        authors.append(credit_name)
                    elif contributor_orcid and isinstance(contributor_orcid, dict):
                        orcid_path = contributor_orcid.get('path', '')
                        if orcid_path:
                            authors.append(f"ORCID: {orcid_path}")
                
                # 如果没有作者信息，使用默认值
                authors_str = ' and '.join(authors) if authors else 'Unknown'
                
                # 获取期刊信息
                journal_title_dict = work_details.get('journal-title', {})
                if not isinstance(journal_title_dict, dict):
                    logger.warning(f"Invalid journal title format for work {put_code}")
                    continue
                    
                journal = journal_title_dict.get('value', '')
                
                # 获取类型
                work_type = work_details.get('type', '')
                
                # Create or update publication.
                try:
                    publication_data = {
                        'bibtex_key': f"orcid_{put_code}",
                        'title': title,
                        'authors': authors_str,
                        'journal': journal,
                        'year': year,
                        'month': _safe_int(month),
                        'day': _safe_int(day),
                        'date': datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d").date() if year else None,
                        'doi': doi,
                        'url': url,
                        'bibtex_type': self._map_work_type(work_type)
                    }
                    existing = Publication.objects.filter(bibtex_key=publication_data['bibtex_key']).first()
                    if not existing and doi:
                        existing = Publication.objects.filter(doi=doi).first()
                    if not existing:
                        existing = _find_duplicate_publication(Publication(**publication_data))

                    if existing:
                        incoming = Publication(**publication_data)
                        if _update_publication(existing, incoming):
                            _refresh_publication_bibtex(existing)
                            logger.info(f"Updated existing publication: {title}")
                        else:
                            logger.info(f"Publication already up to date: {title}")
                    else:
                        publication = Publication.objects.create(**publication_data)
                        _refresh_publication_bibtex(publication)
                        imported_count += 1
                        logger.info(f"Successfully imported publication: {title}")
                except Exception as e:
                    logger.error(f"Error saving publication for work {put_code}: {str(e)}")
                    continue
                
            except Exception as e:
                logger.error(f"Error processing ORCID work: {str(e)}")
                continue
        
        logger.info(f"Completed ORCID sync, imported {imported_count} publications")
        return imported_count
    
    def _format_authors(self, contributors):
        """格式化作者列表"""
        authors = []
        for contributor in contributors:
            credit_name = contributor.get('credit-name', {}).get('value')
            if credit_name:
                authors.append(credit_name)
            else:
                # 如果没有credit-name，尝试使用given-names和family-name
                name_parts = []
                given_names = contributor.get('given-names', {}).get('value')
                family_name = contributor.get('family-name', {}).get('value')
                if given_names:
                    name_parts.append(given_names)
                if family_name:
                    name_parts.append(family_name)
                if name_parts:
                    authors.append(' '.join(name_parts))
        
        return ' and '.join(authors) if authors else 'Unknown'
    
    def _map_work_type(self, work_type):
        """映射ORCID作品类型到Publication类型"""
        type_mapping = {
            'journal-article': 'article',
            'conference-paper': 'conference',
            'book': 'book',
            'book-chapter': 'chapter',
            'dissertation': 'thesis',
            'patent': 'patent'
        }
        return type_mapping.get(work_type.lower(), 'other')

class GoogleScholarService:
    """Google Scholar服务"""
    
    def __init__(self, scholar_id):
        self.scholar_id = scholar_id
        self.base_url = f"https://scholar.google.com/citations"
        self.proxy = SystemConfig.get_scholar_proxy()
        if not self.proxy:
            logger.warning("No proxy configured for Google Scholar. Requests may be blocked.")
        else:
            logger.info(f"Using proxy for Google Scholar: {self.proxy}")
        logger.info(f"Initialized GoogleScholarService for Scholar ID: {scholar_id}")

    def _request_scholar(self, params, headers):
        # Prefer proxy if configured, then fall back to direct connection.
        attempts = []
        if self.proxy:
            attempts.append(("proxy", {'http': self.proxy, 'https': self.proxy}))
        # Force-disable environment proxy variables for direct mode
        attempts.append(("direct", {'http': None, 'https': None}))

        last_error = None
        for mode, proxies in attempts:
            try:
                logger.info(f"Fetching Google Scholar via {mode} for user: {self.scholar_id}")
                response = (_request_without_env_proxy(
                    'GET',
                    self.base_url,
                    params=params,
                    headers=headers,
                    timeout=30
                ) if mode == 'direct' else requests.get(
                    self.base_url,
                    params=params,
                    proxies=proxies,
                    headers=headers,
                    timeout=30
                ))
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                last_error = e
                logger.warning(f"Google Scholar request failed via {mode}: {str(e)}")
        raise last_error
    
    def get_publications(self, start=0, count=100):
        """获取Google Scholar出版物"""
        params = {
            'user': self.scholar_id,
            'hl': 'en',
            'cstart': start,
            'pagesize': count
        }
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0'
            }
            
            try:
                response = self._request_scholar(params, headers)
                response.raise_for_status()
                logger.info(f"Successfully received response from Google Scholar. Status code: {response.status_code}")
                
                # 记录响应内容的前1000个字符，用于调试
                logger.debug(f"Response content preview: {response.text[:1000]}")
                
            except requests.exceptions.ProxyError as e:
                error_msg = f"请求失败（代理/直连均不可用）: {str(e)}"
                logger.error(error_msg)
                raise Exception(error_msg)
            except requests.exceptions.ConnectTimeout:
                error_msg = "连接超时，直连和代理都未成功"
                logger.error(error_msg)
                raise Exception(error_msg)
            except requests.exceptions.RequestException as e:
                if '429' in str(e):
                    error_msg = "Google Scholar 请求频率限制。请配置代理服务器或稍后再试。"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                error_msg = f"请求失败: {str(e)}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            publications = []
            
            # 检查是否被阻止
            if 'Please show you&#39;re not a robot' in response.text or 'Too Many Requests' in response.text:
                error_msg = "Google Scholar 检测到爬虫行为。请配置有效的代理服务器。"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            # 检查页面结构
            publication_table = soup.select_one('#gsc_a_b')
            if not publication_table:
                logger.error("未找到出版物列表表格")
                logger.debug(f"页面内容: {response.text}")
                return []
            
            # 解析出版物列表
            items = soup.select('#gsc_a_b .gsc_a_tr')
            logger.info(f"Found {len(items)} publication items in the table")
            
            for item in items:
                try:
                    title_elem = item.select_one('.gsc_a_t a')
                    if not title_elem:
                        logger.warning("跳过没有标题的条目")
                        continue
                        
                    title = title_elem.text.strip()
                    url = f"https://scholar.google.com{title_elem['href']}" if title_elem.get('href') else ''
                    
                    # 获取作者和期刊信息
                    gray_elems = item.select('.gs_gray')
                    if len(gray_elems) < 2:
                        logger.warning(f"跳过格式不正确的条目: {title}")
                        continue
                        
                    authors = gray_elems[0].text.strip()
                    venue = gray_elems[1].text.strip()
                    
                    # 获取年份
                    year_elem = item.select_one('.gsc_a_y')
                    if not year_elem:
                        logger.warning(f"跳过没有年份的条目: {title}")
                        continue
                    year = year_elem.text.strip()
                    
                    # 获取引用次数
                    citations_elem = item.select_one('.gsc_a_c')
                    citations = int(citations_elem.text) if citations_elem and citations_elem.text.isdigit() else 0
                    
                    publication = {
                        'title': title,
                        'authors': authors,
                        'venue': venue,
                        'year': year,
                        'url': url,
                        'citations': citations
                    }
                    
                    logger.info(f"Successfully parsed publication: {title}")
                    logger.debug(f"Publication details: {publication}")
                    
                    publications.append(publication)
                    
                except Exception as e:
                    logger.error(f"Error parsing publication item: {str(e)}")
                    continue
            
            if not publications:
                logger.warning("No publications found in the response")
                return []
                
            logger.info(f"Successfully fetched {len(publications)} publications from Google Scholar")
            return publications
            
        except Exception as e:
            logger.error(f"Error fetching Google Scholar data: {str(e)}")
            raise
    
    def sync_publications(self, profile=None):
        """Sync Google Scholar publications."""
        logger.info(f"Starting Google Scholar sync for Scholar ID: {self.scholar_id}")
        try:
            publications = self.get_publications()
            if not publications:
                logger.warning("No publications found in Google Scholar response")
                return 0
            
            imported_count = 0
            for pub in publications:
                try:
                    bibtex_key = f"scholar_{self.scholar_id}_{pub['title']}"
                    doi = self._extract_doi(pub['url'])
                    logger.debug(f"Extracted DOI for publication '{pub['title']}': {doi}")
                    if not doi:
                        doi = None
                        logger.debug(f"No DOI found for publication '{pub['title']}', setting to None")
                    
                    year = pub['year']
                    if not year.isdigit():
                        year = re.search(r'\d{4}', year)
                        year = year.group(0) if year else None
                    
                    try:
                        publication_data = {
                            'bibtex_key': bibtex_key,
                            'title': pub['title'],
                            'authors': pub['authors'].replace(', ', ' and '),
                            'journal': pub['venue'],
                            'year': year,
                            'date': datetime.strptime(f"{year}-1-1", "%Y-%m-%d").date() if year else None,
                            'url': pub['url'],
                            'doi': doi,
                            'bibtex_type': 'article'
                        }
                        existing = Publication.objects.filter(bibtex_key=bibtex_key).first()
                        if not existing and doi:
                            existing = Publication.objects.filter(doi=doi).first()
                        if not existing:
                            existing = _find_duplicate_publication(Publication(**publication_data))

                        if existing:
                            incoming = Publication(**publication_data)
                            if _update_publication(existing, incoming):
                                _refresh_publication_bibtex(existing)
                                logger.info(f"Updated existing publication: {pub['title']} with DOI: {doi}")
                            else:
                                logger.info(f"Publication already up to date: {pub['title']} with DOI: {doi}")
                        else:
                            publication = Publication.objects.create(**publication_data)
                            _refresh_publication_bibtex(publication)
                            imported_count += 1
                            logger.info(f"Successfully imported publication: {pub['title']} with DOI: {doi}")
                    except Exception as e:
                        logger.error(f"Error saving publication '{pub['title']}': {str(e)}")
                        logger.error(f"Publication data: {pub}")
                        logger.error(f"DOI value: {doi}")
                        continue
                    
                except Exception as e:
                    logger.error(f"Error processing publication: {str(e)}")
                    continue
            
            logger.info(f"Completed Google Scholar sync, imported {imported_count} publications")
            return imported_count
            
        except Exception as e:
            logger.error(f"Error in Google Scholar sync: {str(e)}")
            raise
    
    def _extract_doi(self, url):
        """从URL中提取DOI"""
        if not url:
            logger.debug("No URL provided for DOI extraction")
            return None
        # 尝试从URL中提取DOI
        doi_pattern = r'10\.\d{4,9}/[-._;()/:A-Z0-9]+'
        match = re.search(doi_pattern, url, re.IGNORECASE)
        if match:
            doi = match.group(0)
            logger.info(f"Successfully extracted DOI: {doi} from URL: {url}")
            return doi
        else:
            logger.debug(f"No DOI found in URL: {url}")
            return None

def sync_publications(profile):
    """同步所有出版物"""
    total_imported = 0
    errors = []
    
    # 存储所有同步的出版物，用于后续比较和合并
    all_publications = {}
    
    # 同步ORCID出版物
    if profile.auto_sync_orcid and profile.orcid_id:
        try:
            orcid_service = ORCIDService(profile.orcid_id)
            imported = orcid_service.sync_publications(profile)
            # 获取所有ORCID出版物
            orcid_pubs = Publication.objects.filter(bibtex_key__startswith='orcid_')
            for pub in orcid_pubs:
                if pub.doi:
                    all_publications[_normalize_doi(pub.doi)] = pub
            total_imported += imported
            logger.info(f"Imported {imported} publications from ORCID for {profile}")
        except Exception as e:
            error_msg = f"ORCID sync error: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    # 同步Google Scholar出版物
    if profile.auto_sync_google_scholar and profile.google_scholar_id:
        try:
            scholar_service = GoogleScholarService(profile.google_scholar_id)
            imported = scholar_service.sync_publications(profile)
            # 获取所有Google Scholar出版物
            scholar_pubs = Publication.objects.filter(bibtex_key__startswith='scholar_')
            for pub in scholar_pubs:
                doi_key = _normalize_doi(pub.doi) if pub.doi else None
                if doi_key and doi_key in all_publications:
                    # 比较两个记录的完整性
                    existing_pub = all_publications[doi_key]
                    if _is_more_complete(pub, existing_pub):
                        # 如果新记录更完整，更新现有记录
                        _update_publication(existing_pub, pub)
                        # 删除新记录
                        pub.delete()
                    else:
                        # 如果现有记录更完整，删除新记录
                        pub.delete()
                else:
                    if doi_key:
                        all_publications[doi_key] = pub
            total_imported += imported
            logger.info(f"Imported {imported} publications from Google Scholar for {profile}")
        except Exception as e:
            error_msg = f"Google Scholar sync error: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    # 更新同步时间
    profile.last_sync_time = timezone.now()
    profile.save()
    
    if errors:
        raise Exception('; '.join(errors))

    _deduplicate_publications()
    _populate_missing_bibtex()
    return total_imported

def _is_more_complete(new_pub, existing_pub):
    """比较两个出版物的完整性，返回新记录是否更完整"""
    # 计算每个记录的完整字段数
    new_score = _calculate_completeness_score(new_pub)
    existing_score = _calculate_completeness_score(existing_pub)
    
    # 如果新记录得分更高，则认为它更完整
    return new_score > existing_score

def _calculate_completeness_score(publication):
    """计算出版物的完整性得分"""
    score = 0
    # 检查每个字段是否有值
    if publication.title:
        score += 5
    if publication.authors:
        score += 4
    if publication.journal:
        score += 3
    if publication.date:
        score += 3
    if publication.year:
        score += 2
    if publication.month:
        score += 1
    if publication.day:
        score += 1
    if publication.doi:
        score += 5
    if publication.url:
        score += 2
    if publication.keywords:
        score += 2
    if publication.raw_bibtex:
        score += 2
    if publication.bibtex_type:
        score += 1
    return score

def _update_publication(existing_pub, new_pub):
    """Merge richer incoming publication fields into an existing record."""
    fields_to_update = [
        'title', 'authors', 'journal', 'year', 'month', 'day',
        'doi', 'url', 'keywords', 'raw_bibtex', 'bibtex_type', 'date'
    ]

    prefer_longer_fields = {'title', 'authors', 'journal', 'raw_bibtex'}
    prefer_list_fields = {'keywords'}
    changed = False

    for field in fields_to_update:
        new_value = getattr(new_pub, field, None)
        existing_value = getattr(existing_pub, field, None)
        if new_value in (None, '', []):
            continue
        if existing_value in (None, '', []):
            setattr(existing_pub, field, new_value)
            changed = True
            continue

        if field in prefer_longer_fields:
            if isinstance(new_value, str) and isinstance(existing_value, str) and len(new_value) > len(existing_value):
                setattr(existing_pub, field, new_value)
                changed = True
            continue

        if field in prefer_list_fields:
            existing_items = _split_keywords(existing_value)
            new_items = _split_keywords(new_value)
            merged = sorted(set(existing_items) | set(new_items))
            if merged and merged != existing_items:
                setattr(existing_pub, field, '; '.join(merged))
                changed = True
            continue

        if field == 'doi':
            if not existing_value and new_value:
                setattr(existing_pub, field, new_value)
                changed = True
            continue
        if field == 'url':
            if _is_better_url(new_value, existing_value):
                setattr(existing_pub, field, new_value)
                changed = True
            continue
        if field == 'date':
            if _date_score(new_value) > _date_score(existing_value):
                setattr(existing_pub, field, new_value)
                changed = True
            continue

    _refresh_publication_bibtex(existing_pub, save=False)
    if changed:
        existing_pub.save()
        logger.info(f"Updated publication {existing_pub.bibtex_key} with more complete information")
    return changed

def _normalize_doi(doi):
    if not doi:
        return None
    doi = doi.strip().lower()
    doi = doi.replace('https://doi.org/', '').replace('http://doi.org/', '')
    doi = doi.replace('doi:', '').strip()
    return doi or None


def _normalize_title(title):
    if not title:
        return ''
    title = title.strip().lower()
    title = re.sub(r'[^a-z0-9]+', ' ', title)
    return re.sub(r'\s+', ' ', title).strip()


def _normalize_authors(authors):
    if not authors:
        return set()
    parts = re.split(r'\s+and\s+|,|;|&', authors, flags=re.IGNORECASE)
    last_names = set()
    for part in parts:
        tokens = [t for t in re.split(r'\s+', part.strip()) if t]
        if tokens:
            last_names.add(re.sub(r'[^a-z0-9]', '', tokens[-1].lower()))
    return {n for n in last_names if n}


def _title_similarity(a, b):
    a_tokens = set(re.findall(r'[a-z0-9]+', a))
    b_tokens = set(re.findall(r'[a-z0-9]+', b))
    if not a_tokens or not b_tokens:
        return 0.0
    return len(a_tokens & b_tokens) / len(a_tokens | b_tokens)


def _author_overlap(a, b):
    if not a or not b:
        return 1.0
    return len(a & b) / min(len(a), len(b))


def _date_score(d):
    if not d:
        return 0
    return 3


def _split_keywords(value):
    if not value:
        return []
    if isinstance(value, list):
        return [v.strip() for v in value if str(v).strip()]
    return [v.strip() for v in re.split(r'[;,]', str(value)) if v.strip()]


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _sanitize_bibtex_value(value):
    if value in (None, ''):
        return ''
    return str(value).replace('\r\n', ' ').replace('\n', ' ').strip()


def _fallback_bibtex_key(publication):
    base = _normalize_title(publication.title).replace(' ', '_') or 'publication'
    year = publication.year or (publication.date.year if publication.date else '')
    return '{}{}'.format(base[:60], year or '')


def _publication_bibtex_entry(publication):
    year = publication.year or (publication.date.year if publication.date else None)
    month = publication.month or (publication.date.month if publication.date else None)
    day = publication.day or (publication.date.day if publication.date else None)

    entry = {
        'ENTRYTYPE': publication.bibtex_type or 'article',
        'ID': publication.bibtex_key or _fallback_bibtex_key(publication),
        'title': _sanitize_bibtex_value(publication.title),
        'author': _sanitize_bibtex_value(publication.authors),
        'journal': _sanitize_bibtex_value(publication.journal),
    }

    optional_fields = {
        'year': year,
        'month': month,
        'day': day,
        'doi': _normalize_doi(publication.doi) if publication.doi else '',
        'url': publication.url,
        'keywords': ', '.join(_split_keywords(publication.keywords)),
    }
    for key, value in optional_fields.items():
        sanitized = _sanitize_bibtex_value(value)
        if sanitized:
            entry[key] = sanitized

    return entry


def _parse_first_bibtex_entry(raw_bibtex):
    if not raw_bibtex:
        return None
    try:
        parser = bibtexparser.bparser.BibTexParser(common_strings=True)
        database = bibtexparser.loads(raw_bibtex, parser=parser)
    except Exception:
        return None
    if not database.entries:
        return None
    return dict(database.entries[0])


def _score_bibtex_value(value):
    sanitized = _sanitize_bibtex_value(value)
    if not sanitized:
        return 0
    return len(sanitized)


def _merge_bibtex_entries(primary_entry, secondary_entry):
    merged = {}
    for source in (secondary_entry or {}, primary_entry or {}):
        for key, value in source.items():
            sanitized = _sanitize_bibtex_value(value)
            if not sanitized:
                continue
            existing = merged.get(key, '')
            if _score_bibtex_value(sanitized) >= _score_bibtex_value(existing):
                merged[key] = sanitized

    merged['ENTRYTYPE'] = _sanitize_bibtex_value(
        (primary_entry or {}).get('ENTRYTYPE') or
        (secondary_entry or {}).get('ENTRYTYPE') or
        'article'
    )
    merged['ID'] = _sanitize_bibtex_value(
        (primary_entry or {}).get('ID') or
        (secondary_entry or {}).get('ID') or
        'publication'
    )
    return merged


def _entry_to_bibtex(entry):
    if not entry:
        return ''
    database = bibtexparser.bibdatabase.BibDatabase()
    database.entries = [entry]
    return bibtexparser.dumps(database).strip()


def _refresh_publication_bibtex(publication, save=True):
    generated_entry = _publication_bibtex_entry(publication)
    existing_entry = _parse_first_bibtex_entry(publication.raw_bibtex)
    merged_entry = _merge_bibtex_entries(generated_entry, existing_entry)
    raw_bibtex = _entry_to_bibtex(merged_entry)
    if not raw_bibtex:
        return publication.raw_bibtex
    publication.raw_bibtex = raw_bibtex
    publication.bibtex_type = merged_entry.get('ENTRYTYPE', publication.bibtex_type or 'article')
    if save:
        publication.save(update_fields=['raw_bibtex', 'bibtex_type', 'updated_at'])
    return raw_bibtex


def _is_better_url(candidate, existing):
    if not candidate:
        return False
    if not existing:
        return True
    if candidate.startswith('https://') and not existing.startswith('https://'):
        return True
    if len(candidate) > len(existing):
        return True
    return False


def _is_duplicate(pub_a, pub_b):
    title_a = _normalize_title(pub_a.title)
    title_b = _normalize_title(pub_b.title)
    if not title_a or not title_b:
        return False
    return title_a == title_b


def _find_duplicate_publication(publication):
    doi = _normalize_doi(publication.doi)
    if doi:
        existing = Publication.objects.filter(doi__iexact=doi).first()
        if existing:
            return existing

    title_key = _normalize_title(publication.title)
    if not title_key:
        return None

    for existing in Publication.objects.exclude(title='').only('id', 'title', 'doi'):
        if _normalize_title(existing.title) == title_key:
            return existing
    return None


def _deduplicate_publications():
    publications = list(Publication.objects.all().order_by('id'))
    if len(publications) < 2:
        return {"groups": 0, "removed": 0}

    groups = {}
    for pub in publications:
        key = _normalize_title(pub.title)
        if not key:
            continue
        groups.setdefault(key, []).append(pub)

    merged_groups = 0
    removed = 0
    for group in groups.values():
        if len(group) < 2:
            continue
        merged_groups += 1
        winner = max(group, key=_calculate_completeness_score)
        for item in group:
            if item.id == winner.id:
                continue
            _update_publication(winner, item)
            item.delete()
            removed += 1
    _populate_missing_bibtex()
    return {"groups": merged_groups, "removed": removed}


def _populate_missing_bibtex():
    for publication in Publication.objects.filter(raw_bibtex='').only(
        'id', 'title', 'authors', 'journal', 'year', 'month', 'day', 'doi',
        'url', 'keywords', 'bibtex_key', 'bibtex_type', 'raw_bibtex', 'date'
    ):
        _refresh_publication_bibtex(publication)


def deduplicate_publications():
    """Public wrapper for title-based de-duplication."""
    return _deduplicate_publications()
