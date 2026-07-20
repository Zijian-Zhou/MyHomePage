# MyHomePage

> A bilingual, database-driven academic homepage and content management system built with Django.

[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.2%2B-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

MyHomePage is a self-hosted academic profile website for researchers, students, and professionals. It combines a responsive public homepage with a customized Django administration portal, allowing profile information, publications, research projects, news, custom sections, downloadable files, and site settings to be maintained without editing templates.

The project supports English and Simplified Chinese, publication synchronization through ORCID and Google Scholar, Markdown-based detail pages, configurable OpenAI-compatible LLM assistance in the administration interface, and several built-in security and operations features.

## 中文简介

MyHomePage 是一个基于 Django 的双语学术个人主页与内容管理系统。管理员可通过后台维护个人简介、论文成果、研究项目、新闻、自定义栏目和附件，无需直接修改 HTML。系统还提供 ORCID/Google Scholar 论文同步、BibTeX 数据、中英文内容切换、Markdown 详情页、可配置的大模型辅助、资源监控以及多项后台安全机制。

## Contents

- [Features](#features)
- [Screens and content model](#screens-and-content-model)
- [Technology stack](#technology-stack)
- [Project structure](#project-structure)
- [Quick start](#quick-start)
- [Initial configuration](#initial-configuration)
- [Publication synchronization](#publication-synchronization)
- [LLM-assisted administration](#llm-assisted-administration)
- [Configuration reference](#configuration-reference)
- [URL map](#url-map)
- [Deployment](#deployment)
- [Security notes](#security-notes)
- [Development and testing](#development-and-testing)
- [Known limitations](#known-limitations)
- [Contributing](#contributing)
- [License](#license)

## Features

### Public academic homepage

- Multiple profiles with configurable visibility, draft state, and ordering
- Academic identity links for ORCID, Google Scholar, GitHub, ResearchGate, and LinkedIn
- Publication cards with authors, venue, date, DOI, keywords, BibTeX, images, and detail pages
- Highlighted and corresponding-author formatting
- Research-project and news sections with optional images and Markdown detail pages
- Configurable custom sections and section items
- Secure links for uploaded media and publication attachments
- Responsive layout and locally bundled Font Awesome assets

### Bilingual content

- English and Simplified Chinese routes through Django internationalization
- Chinese variants for profile biographies, addresses, research content, news, and page details
- A site-level switch for enabling or disabling Chinese mode
- Locale catalogs under `locale/en` and `locale/zh_Hans`
- Optional IP-based language selection, disabled by default

### Administration portal

- Customized Django admin home, navigation, forms, and styling
- Draft/save workflow for major content types
- Publication BibTeX import and preview tools
- Media and publication-file management
- User and group management
- Site configuration stored in the database
- Dark mode and custom administration JavaScript
- CPU, memory, and resource-history views

### External data and AI integrations

- ORCID OAuth and publication import
- Google Scholar publication import with optional proxy configuration
- Manual and scheduled publication synchronization
- Configurable LLM providers for administration assistance
- OpenAI, generic OpenAI-compatible APIs, DeepSeek, GLM BigModel, SCNet Qwen, and SCNet MiniMax provider presets
- Provider availability checks and provider rotation

### Security and operations

- Environment-driven production security settings
- RSA-assisted admin-login payload protection
- Admin login rate limiting and temporary lockout
- Session expiry and expired-session cleanup task
- Controlled access to uploaded Markdown assets and publication files
- Secure-cookie, HTTPS redirect, HSTS, clickjacking, and referrer-policy settings
- Safe rendering of user-maintained Markdown content

## Screens and content model

The public site is assembled from database records managed in Django admin:

| Model | Purpose |
| --- | --- |
| `Profile` | Display name, title, institution, biography, portrait, contact details, academic links, and synchronization preferences |
| `Publication` | Bibliographic metadata, BibTeX, author emphasis, cover image, keywords, and optional detail content |
| `PublicationFile` | Ordered downloadable files or external links attached to a publication |
| `Research` | Research project title, summary, image, links, and bilingual detail content |
| `News` | News entries with date, image, URL, and bilingual detail content |
| `Section` / `SectionItem` | Custom homepage sections and ordered content items |
| `MediaFile` | Managed files with generated access keys |
| `SystemConfig` | Site behavior, integrations, footer items, synchronization, and display settings |
| `AIConfig` | LLM endpoint, model, credentials, activation/default state, and health-check status |
| `ResourceMetricLog` | Historical server resource measurements for the admin monitor |

## Technology stack

| Area | Technology |
| --- | --- |
| Backend | Python, Django 4.2+ |
| Database | SQLite by default |
| Templates | Django Templates |
| Frontend | HTML, CSS, vanilla JavaScript, Font Awesome |
| Content | Markdown, BibTeX |
| Images/files | Pillow and Django media storage |
| Internationalization | Django i18n/gettext |
| Integrations | ORCID API, Google Scholar, OpenAI-compatible chat-completions APIs |
| Background-task definitions | Celery tasks (optional; additional setup required) |
| Monitoring | psutil and database-backed resource logs |

## Project structure

```text
MyHomePage/
├── HomePage/                 # Django project settings, root URLs, ASGI/WSGI
├── myHomePage/               # Main application
│   ├── management/commands/  # Publication-sync and integration commands
│   ├── migrations/           # Database schema history
│   ├── admin.py              # Customized administration portal
│   ├── ai_services.py        # LLM provider adapters and routing
│   ├── middleware.py         # Language, login, session, and media controls
│   ├── models.py             # Site content and configuration models
│   ├── resource_monitor.py   # Background resource sampling
│   ├── security.py           # Login cryptography helpers
│   ├── services.py           # ORCID/Scholar synchronization services
│   ├── tasks.py              # Optional Celery task definitions
│   ├── urls.py               # Application URL routes
│   └── views.py              # Public and administration-related views
├── templates/                # Public, detail, error, and admin templates
├── static/                   # CSS, JavaScript, icons, fonts, and metadata
├── locale/                   # English and Simplified Chinese translations
├── media/                    # Development/user-uploaded media
├── manage.py
├── requirements.txt
└── LICENSE
```

## Quick start

### Prerequisites

- Python 3.8 or later is recommended
- `pip` and `venv`
- Git

The application uses SQLite by default, so a separate database server is not required for local development.

### 1. Clone the repository

```bash
git clone https://github.com/Zijian-Zhou/MyHomePage.git
cd MyHomePage
```

### 2. Create and activate a virtual environment

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Create the database schema

```bash
python manage.py migrate
```

### 5. Create an administrator

```bash
python manage.py createsuperuser
```

### 6. Start the development server

```bash
python manage.py runserver
```

Open:

- Homepage: <http://127.0.0.1:8000/en/>
- Chinese homepage: <http://127.0.0.1:8000/zh-hans/> (when Chinese mode is enabled)
- Administration: <http://127.0.0.1:8000/en/admin/>

Because the root URL uses Django's `i18n_patterns`, the default language prefix is included in normal page and admin URLs.

## Initial configuration

After signing in to the administration portal, a practical setup order is:

1. Create or edit a `Profile` and mark it active.
2. Add publications, research projects, and news entries.
3. Add custom sections if the standard content blocks are insufficient.
4. Review `SystemConfig`, particularly language, card-count, author-highlighting, footer, and synchronization settings.
5. Upload images and publication files through their corresponding admin forms.
6. Configure ORCID, Google Scholar, or an LLM provider only if those integrations are needed.

Most content models support `is_active`, `is_draft`, and/or `order` fields. Draft or inactive records are intended for staging content before it becomes visible.

## Publication synchronization

### Manual command

The management command synchronizes eligible profiles whose configured synchronization interval has elapsed:

```bash
python manage.py sync_publications
```

Enable `auto_sync_orcid` or `auto_sync_google_scholar` on the relevant profile before using scheduled synchronization.

### ORCID

ORCID integration uses settings stored through `SystemConfig`, including the client ID, client secret, and access token. The project exposes an OAuth authorization/callback flow and includes diagnostic/configuration commands:

```bash
python manage.py check_orcid_config
python manage.py check_orcid_config --token YOUR_ORCID_ACCESS_TOKEN
```

Do not commit real ORCID credentials or access tokens.

### Google Scholar

Set the profile's Google Scholar ID and optionally configure a Scholar proxy in `SystemConfig`. Scholar endpoints may rate-limit or block automated access; use synchronization conservatively and comply with the upstream service's terms.

### Scheduling

`myHomePage/tasks.py` defines Celery tasks for publication synchronization and expired-session cleanup. Celery and a broker are not fully provisioned by this repository's current `requirements.txt` or settings, so production scheduling requires you to add and pin Celery, choose a broker, configure `CELERY_*` settings, and run worker/beat processes. As a simpler alternative, invoke the management command from cron, systemd timers, or Windows Task Scheduler.

## LLM-assisted administration

LLM connections are configured in the `AIConfig` administration section. Each entry can define:

- Provider type
- Display name
- API base URL
- Model name
- API key
- Default/active state
- Additional provider options

The adapter calls an OpenAI-compatible chat-completions endpoint. Provider tests are available from the admin interface, and active providers can be selected for publication-related content assistance.

API use is optional. Keep API keys out of source control, restrict administration access, and review generated text before publishing it.

## Configuration reference

Create a `.env` file or export environment variables before starting Django. `python-dotenv` is installed, but the current settings module does not automatically call `load_dotenv`; load the file through your process manager or shell unless you add that call yourself.

Example development environment:

```dotenv
DEBUG=True
SECRET_KEY=replace-with-a-long-random-value
ALLOWED_HOSTS=127.0.0.1,localhost
ENABLE_IP_GEO_LANGUAGE=False
```

Generate a strong secret key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Environment variables

| Variable | Development default | Purpose |
| --- | --- | --- |
| `DEBUG` | `True` | Enables Django debug behavior; set to `False` in production |
| `SECRET_KEY` | Development fallback | Cryptographic signing key; mandatory and unique when `DEBUG=False` |
| `ALLOWED_HOSTS` | `127.0.0.1,localhost` | Comma-separated hostnames accepted by Django |
| `SECURE_SSL_REDIRECT` | `False` in debug, otherwise `True` | Redirect HTTP requests to HTTPS |
| `SESSION_COOKIE_SECURE` | `False` in debug, otherwise `True` | Send the session cookie only over HTTPS |
| `CSRF_COOKIE_SECURE` | `False` in debug, otherwise `True` | Send the CSRF cookie only over HTTPS |
| `SECURE_HSTS_SECONDS` | `0` in debug, otherwise `31536000` | HSTS lifetime |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | Matches environment mode | Applies HSTS to subdomains |
| `SECURE_HSTS_PRELOAD` | Matches environment mode | Enables the HSTS preload directive |
| `X_FRAME_OPTIONS` | `DENY` | Controls iframe embedding |
| `SECURE_REFERRER_POLICY` | `same-origin` | Configures the browser referrer policy |
| `ENABLE_IP_GEO_LANGUAGE` | `False` | Enables IP-based language selection |
| `LOGIN_MAX_ATTEMPTS` | `5` | Failed login threshold |
| `LOGIN_ATTEMPT_WINDOW_SECONDS` | `600` | Login-attempt counting window |
| `LOGIN_LOCKOUT_SECONDS` | `900` | Temporary lockout duration |

### Database and time zone

- Default database: `db.sqlite3` in the repository root
- Default time zone: `Asia/Shanghai`
- Default language: English
- Session lifetime: 30 minutes

For PostgreSQL or MySQL deployment, install the relevant database driver and replace the `DATABASES` definition in `HomePage/settings.py`.

## URL map

Language-aware routes are prefixed with `/en/` or `/zh-hans/`.

| Route | Description |
| --- | --- |
| `/<language>/` | Public homepage |
| `/<language>/publication/<id>/` | Publication detail |
| `/<language>/research/<id>/` | Research-project detail |
| `/<language>/news/<id>/` | News detail |
| `/<language>/admin/` | Customized administration portal |
| `/<language>/orcid/authorize/` | Start ORCID OAuth |
| `/<language>/orcid/callback/` | Complete ORCID OAuth |
| `/publication-file/<access-key>/` | Access a managed publication file |
| `/media-file/<access-key>/` | Access a managed media file |

## Deployment

The repository includes WSGI and ASGI entry points but intentionally does not prescribe one hosting provider. A typical production stack is:

```text
Browser -> HTTPS reverse proxy -> WSGI/ASGI application server -> Django -> database/media storage
```

Before deployment:

1. Set `DEBUG=False`.
2. Set a new, strong `SECRET_KEY` outside the repository.
3. Configure `ALLOWED_HOSTS` with the real domain names.
4. Configure HTTPS before leaving secure-cookie and HSTS settings enabled.
5. Run migrations with `python manage.py migrate`.
6. Configure production static-file collection and serving. The current settings define `STATICFILES_DIRS` but not a production `STATIC_ROOT`; add one before running `collectstatic`.
7. Store user uploads in persistent storage and back them up with the database.
8. Run `python manage.py check --deploy` and address every applicable warning.
9. Use a production server such as Gunicorn, uWSGI, or an ASGI server instead of `runserver`.
10. Configure process supervision and log rotation.

Example WSGI application target:

```text
HomePage.wsgi:application
```

Example ASGI application target:

```text
HomePage.asgi:application
```

## Security notes

- Never deploy with the repository's development secret-key fallback.
- Never commit `.env`, database files, API keys, OAuth secrets, access tokens, or production user uploads.
- Uploaded files require defense in depth: validate file types and sizes, serve untrusted content from a separate origin where possible, and keep the web server from executing uploaded content.
- HSTS can make a domain inaccessible if HTTPS is misconfigured. Confirm HTTPS first, then enable long-duration HSTS and preload deliberately.
- Keep Django and all dependencies patched and pinned for reproducible production builds.
- Restrict the administration portal by strong credentials and, where practical, network controls or multi-factor authentication at the identity/reverse-proxy layer.
- Back up both the database and media directory; either one alone is insufficient for a complete restore.

## Development and testing

Run Django's checks:

```bash
python manage.py check
```

Run migrations after model changes:

```bash
python manage.py makemigrations
python manage.py migrate
```

Compile translation catalogs after editing `.po` files (requires GNU gettext):

```bash
python manage.py compilemessages
```

Run the test suite:

```bash
python manage.py test
```

The current `myHomePage/tests.py` is only a placeholder, so contributors should add regression tests for models, views, middleware, synchronization behavior, permissions, file access, and administration workflows.

## Known limitations

- SQLite is convenient for local use but may not be suitable for higher-concurrency deployments.
- Celery task definitions exist, but Celery, broker, and beat configuration are not currently complete or pinned in the project dependencies.
- `python-dotenv` is listed as a dependency, but `.env` loading is not invoked automatically by `HomePage/settings.py`.
- Production static collection needs an explicit `STATIC_ROOT`.
- Automated tests have not yet been implemented beyond the generated placeholder.
- Google Scholar synchronization depends on an unofficially accessed upstream surface and may be affected by rate limits or markup changes.
- The repository currently contains generated/runtime artifacts and uploaded media; production deployments should separate runtime data from version-controlled source.

## Contributing

Issues and pull requests are welcome. For a change:

1. Fork the repository.
2. Create a focused branch.
3. Add or update tests where applicable.
4. Run `python manage.py check` and `python manage.py test`.
5. Avoid committing credentials, local databases, logs, caches, or personal uploaded files.
6. Submit a pull request describing the motivation, implementation, and verification performed.

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).

## Acknowledgements

MyHomePage is built with Django and uses open-source libraries and assets listed in `requirements.txt` and the `static` directory. Thanks to the maintainers and contributors of those projects.
