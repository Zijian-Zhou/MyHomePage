import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from django.utils import timezone

from .models import AIConfig


class BaseLLMProvider(object):
    def chat(self, model, messages, params=None):
        raise NotImplementedError


class OpenAICompatibleProvider(BaseLLMProvider):
    """Minimal OpenAI-compatible chat client with retry support."""

    RETRY_STATUS = {429, 500, 502, 503, 504}

    def __init__(self, api_base, api_key):
        self.api_base = (api_base or '').rstrip('/')
        self.api_key = api_key or ''
        self.session = requests.Session()
        # Avoid stale system proxy settings breaking direct LLM connectivity.
        self.session.trust_env = False

    def _headers(self):
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = 'Bearer {}'.format(self.api_key)
        return headers

    def chat(self, model, messages, params=None):
        if not self.api_base:
            raise RuntimeError('API base is empty')
        if not model:
            raise RuntimeError('Model name is empty')

        payload = {'model': model, 'messages': messages}
        if isinstance(params, dict):
            payload.update(params)

        endpoint = '{}/chat/completions'.format(self.api_base)
        last_response = None
        for attempt in range(3):
            try:
                response = self.session.post(
                    endpoint,
                    headers=self._headers(),
                    json=payload,
                    timeout=45,
                )
                last_response = response
                if response.status_code in self.RETRY_STATUS and attempt < 2:
                    retry_after = response.headers.get('Retry-After', '')
                    sleep_seconds = int(retry_after) if str(retry_after).isdigit() else min(8, 2 ** attempt)
                    time.sleep(max(1, sleep_seconds))
                    continue

                response.raise_for_status()
                try:
                    return response.json()
                except ValueError:
                    if attempt < 2:
                        time.sleep(min(8, 2 ** attempt))
                        continue
                    raise RuntimeError('LLM response JSON parse failed.')
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.ReadTimeout,
                requests.exceptions.ChunkedEncodingError,
            ) as exc:
                if attempt < 2:
                    time.sleep(min(8, 2 ** attempt))
                    continue
                raise RuntimeError('LLM network error after retries: {}'.format(exc))

        if last_response is not None:
            last_response.raise_for_status()
        raise RuntimeError('LLM request failed without response')


def build_provider(config):
    provider_type = config.get('provider_type') or AIConfig.OPENAI_COMPATIBLE
    if provider_type in (
        AIConfig.OPENAI,
        AIConfig.OPENAI_COMPATIBLE,
        AIConfig.GLM_BIGMODEL,
        AIConfig.DEEPSEEK,
        AIConfig.SCNET_QWEN,
        AIConfig.SCNET_MINIMAX,
    ):
        return OpenAICompatibleProvider(
            api_base=config.get('api_base', ''),
            api_key=config.get('api_key', ''),
        )
    raise ValueError('Unsupported provider type: {}'.format(provider_type))


def _content_from_response(response):
    choices = response.get('choices') or []
    if not choices:
        return ''
    message = choices[0].get('message') or {}
    return str(message.get('content') or '').strip()


def probe_provider_config(config):
    """Check whether one provider can answer a small chat-completions request."""
    if not config.get('api_key'):
        return False, 'API key is empty'
    if not config.get('api_base'):
        return False, 'API base is empty'
    if not config.get('model_name'):
        return False, 'Model name is empty'
    if config.get('provider_type') == AIConfig.FELO_PPT:
        return None, 'Felo PPT is skipped for text LLM keep-alive checks'

    try:
        provider = build_provider(config)
        response = provider.chat(
            model=config.get('model_name'),
            messages=[{'role': 'user', 'content': 'Reply with: pong'}],
            params={'temperature': 0},
        )
        if not _content_from_response(response):
            return False, 'Probe response is empty'
        return True, ''
    except Exception as exc:
        return False, str(exc)


def check_ai_config(item):
    cfg = item.to_provider_config()
    ok, message = probe_provider_config(cfg)
    if ok is None:
        item.last_check_at = timezone.now()
        item.last_check_ok = None
        item.last_check_message = message
        item.save(update_fields=['last_check_at', 'last_check_ok', 'last_check_message', 'updated_at'])
    else:
        item.set_check_result(ok, message)
    return {
        'id': item.pk,
        'name': item.name,
        'ok': ok,
        'status': 'OK' if ok else ('SKIPPED' if ok is None else 'FAILED'),
        'detail': message or '',
        'provider_type': item.provider,
        'model_name': item.model_name or '',
        'is_active': item.is_active,
    }


def check_all_ai_configs(queryset=None):
    items = queryset if queryset is not None else AIConfig.objects.all().order_by('-is_default', 'name')
    return [check_ai_config(item) for item in items]


_ROUTER_LOCK = threading.Lock()
_ROUTER = {'providers': [], 'cursor': 0, 'checked': False, 'errors': []}


def refresh_available_providers():
    available = []
    errors = []
    for item in AIConfig.objects.filter(is_active=True).order_by('-is_default', 'name'):
        if not item.is_complete_for_text():
            continue
        config = item.to_provider_config()
        ok, message = probe_provider_config(config)
        if ok:
            available.append(config)
        else:
            errors.append({
                'name': item.name,
                'provider_type': item.provider,
                'model_name': item.model_name,
                'error': message,
            })
            item.set_check_result(False, message)

    with _ROUTER_LOCK:
        _ROUTER.update({'providers': available, 'cursor': 0, 'checked': True, 'errors': errors})
    return {'available': available, 'failed': errors}


def _pick_provider():
    with _ROUTER_LOCK:
        providers = list(_ROUTER.get('providers') or [])
    if not providers:
        refresh_available_providers()
        with _ROUTER_LOCK:
            providers = list(_ROUTER.get('providers') or [])

    if not providers:
        with _ROUTER_LOCK:
            errors = list(_ROUTER.get('errors') or [])
        detail = '; '.join(['{}:{}'.format(x.get('name', ''), x.get('error', '')) for x in errors])
        raise RuntimeError('No available LLM providers. {}'.format(detail))

    with _ROUTER_LOCK:
        idx = _ROUTER['cursor'] % len(providers)
        _ROUTER['cursor'] += 1
    return providers[idx]


def generate_text(system_prompt, user_prompt, temperature=0.2):
    config = _pick_provider()
    return generate_text_with_config(config, system_prompt, user_prompt, temperature)


def generate_text_with_config(config, system_prompt, user_prompt, temperature=0.2):
    provider = build_provider(config)
    response = provider.chat(
        model=config.get('model_name'),
        messages=[
            {'role': 'system', 'content': system_prompt or ''},
            {'role': 'user', 'content': user_prompt or ''},
        ],
        params={'temperature': temperature},
    )
    content = _content_from_response(response)
    if not content:
        raise RuntimeError('LLM returned empty response')
    return content


def generate_text_with_provider(provider_id, system_prompt, user_prompt, temperature=0.2):
    item = AIConfig.objects.filter(pk=provider_id).first()
    if not item:
        raise RuntimeError('Selected LLM provider does not exist')
    if not item.is_complete_for_text():
        raise RuntimeError('Selected LLM provider is incomplete')
    return generate_text_with_config(item.to_provider_config(), system_prompt, user_prompt, temperature)
