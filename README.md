# MyHomePage

> A bilingual, database-driven academic homepage and administration system built with Django.<br>
> 基于 Django 的双语、数据库驱动学术主页与后台管理系统。

[![Python](https://img.shields.io/badge/Python-3.7%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.2-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-v1.1.0-orange)](HomePage/version.py)

[English](#english) | [简体中文](#简体中文)

---

<a id="english"></a>

## English

### Overview

MyHomePage is a self-hosted academic profile and content management system for researchers, students, laboratories, and professionals. A responsive public homepage is paired with a customized Django administration portal, so profiles, publications, research projects, news, custom sections, files, AI providers, and site-wide settings can be managed without editing templates.

The application supports English and Simplified Chinese, Markdown content, ORCID and Google Scholar synchronization, publication deduplication, configurable LLM assistance, protected file delivery, database-backed sessions, and real-time resource monitoring.

### Features

#### Public website

- Light ("Mist") and dark ("Slate") themes shared with the administration portal; the saved theme is applied before the first paint, so reloads never flash white.
- Phone and tablet layouts: a compact two-line header with a swipeable navigation row and finger-sized tap targets.
- One card design across About, News, Publications, Research, Contact, and custom sections.
- About layout: the portrait lines up with the "About Me" title, and the biography card stretches to the bottom of the contact card when the profile column is taller.
- Contact block with a centred address and pill links for email, phone, ORCID, Google Scholar, GitHub, ResearchGate, and LinkedIn.
- Section images zoom on hover and open in a full-screen viewer on double-click or double-tap; PNG images (often transparent logos) are shown without a drop shadow.
- Navigation scrolls smoothly to each section just below the fixed header and highlights the section in view.
- Page transitions and long operations use a soft overlay with a chomping loading animation instead of a white flash.
- Thin, theme-aware scrollbars across the site.
- Profile information, portrait, contact details, academic identity links, and a Markdown biography.
- Publication cards with highlighted/corresponding authors, venue, date, DOI, keywords, images, BibTeX, detail pages, and ordered file links.
- One-click BibTeX copy with localized feedback.
- Publication attachments can be uploaded files or external URLs, with labels such as PDF, Slides, Code, Data, and Supplement.
- News and research cards support summaries, optional Markdown detail pages, images, and previous/next navigation.
- When a news or research summary is empty, it is generated from the first 300 words/characters of the content.
- Custom homepage sections and ordered section items with Markdown rendering; an item can enable its own detail page with separate detail content (the card adds a View Details link); items collapse in the admin and have their own Save / Delete buttons, and the admin offers a Markdown preview for item content.
- Independent asynchronous pagination for each homepage section; changing one section does not reset the others or reload the whole page.
- Empty sections are omitted from both navigation and page content.
- Configurable footer items (display name, optional icon and link; the icon can be a Font Awesome class, an image URL, or an uploaded image) and styled 4xx/5xx/access-denied pages.
- The footer shows the running version (`Powered By MyHomePage v1.1.0`); the version is defined once in `HomePage/version.py`.

#### Bilingual content

- English and Simplified Chinese routes through Django i18n.
- Chinese variants for profile biography/address, news, research, custom sections, titles, summaries, descriptions, and detail content.
- Chinese fields and translation controls are hidden when Chinese mode is disabled.
- Requests to Chinese URLs are redirected to English when Chinese mode is disabled.
- Administration labels, validation messages, overlays, detail navigation, and public controls are localized.
- Optional automatic field translation using the configured translation library.
- Synchronization error messages follow the active interface language.

#### Administration portal

- Customized dashboard, navigation, dark mode, responsive forms, and collapsible left/right sidebars.
- Theme aligned with the public site in light and dark mode, a sticky header and breadcrumb bar, and a footer pinned to the bottom of the window.
- Consistent buttons, upload areas, checkboxes, and focus states; the Translate / Preview / AI Generate actions sit in one row under their field.
- Tablet and phone layouts: the outline panel collapses (tablets) or hides (phones), change-list tables scroll horizontally, and filters move below the results.
- Loading overlay for navigation, saving, synchronization, and backup operations.
- A right-side form outline links directly to configuration fieldsets.
- Save and Save as Draft workflows for managed content.
- Markdown preview for profile Bio and publication detail content.
- Publication BibTeX parsing/import, raw BibTeX storage, and metadata editing.
- AI-assisted publication detail generation with provider selection, progress states, PDF/file context, preview, feedback-based revision, manual editing, and save actions.
- Media library with generated access keys and ready-to-use Markdown snippets.
- System Configuration and AI Configuration are independent top-level administration entries.
- Footer items are edited in a table with live icon preview and icon upload (PNG/JPG/GIF/WEBP/ICO, stored as Media Files).
- User/group management and localized configuration forms.
- System resource monitor with live and historical CPU, memory, disk, and network throughput charts, plus database / media / backup storage usage.
- Audit log (superusers only): logins, failed logins, lockouts, logouts, every admin add/change/delete, publication syncs, and backup operations, with user, IP, and user agent; filters, search, 24-hour summary, CSV export (selected rows, or **Export all logs**), and configurable retention (`audit_log_retention_days`, default 180). The audit trail is included in backups; a restore merges it with the current trail instead of rolling it back.
- Anomaly log (audit category **Anomaly**): attack payloads in URLs/headers (SQL injection, XSS, path traversal, command injection, Log4Shell), probes for well-known attack targets (`.env`, `.git`, `wp-admin`, phpMyAdmin, `*.php`, backups), known scanner User-Agents, request floods and 404 bursts per IP, requests Django rejects (forged Host header, CSRF failures) and server errors (500). Repeats from the same source within 10 minutes are merged into one row with a hit count, and new rows are capped per minute so an attack cannot flood the database. Nothing is blocked; signed-in staff are not monitored. Thresholds: `SECURITY_FLOOD_PER_MINUTE` (300), `SECURITY_404_PER_MINUTE` (30); the rate rules need `TRUST_X_FORWARDED_FOR=True` behind Nginx.
- System backup (superusers only): create full backups of the database and media, download, delete, import external backups, and restore with an automatic pre-restore safety backup.

#### Publication synchronization

- ORCID and Google Scholar sources can be enabled independently per profile.
- Manual single-profile, bulk, management-command, and Celery-scheduled synchronization.
- Direct network access is attempted when no proxy is configured; failures are isolated by source.
- Duplicate publications are matched primarily by normalized title.
- Duplicate records merge missing metadata and keep the richest field values, including raw BibTeX.
- Synchronization messages report the post-deduplication result.
- The synchronization interval is configurable in hours and is applied without editing the Celery schedule.

#### AI integrations

- Separate `AIConfig` records for multiple LLM endpoints.
- Supported presets: OpenAI Official, generic OpenAI-compatible APIs, DeepSeek, GLM BigModel, SCNet Qwen, and SCNet MiniMax.
- Configurable base URL, model, API key, default provider, activation state, and JSON parameters.
- Individual, selected, and all-provider connectivity/keep-alive checks.
- Publication-detail generation uses publication metadata, attached readable files such as PDFs, and the bilingual templates in `templates/paper_introduction_framework*.md`.

#### Security and operations

- Browser-side RSA encryption for administration login fields; server RSA keys rotate every 10 minutes.
- SHA-256 is used as part of the protected login exchange.
- Login rate limiting, temporary lockout, localized lockout page, and live countdown.
- Database-backed sessions with a 30-minute lifetime and hourly expired-session cleanup.
- Sessions remain valid across ordinary application restarts when the same database and secret key are retained.
- Managed media files are public only when active; inactive files require an authenticated administrator.
- Publication downloads use non-sequential access keys instead of database IDs.
- Replaced/deleted uploaded media, profile images, publication images, and publication files are removed from storage.
- User-authored Markdown is HTML-escaped before rendering.
- Environment-driven HTTPS, secure-cookie, HSTS, clickjacking, and referrer-policy settings.
- Resource-monitor history is stored in the database and pruned according to the configured retention period.

### Content model

| Model | Purpose |
| --- | --- |
| `Profile` | Identity, biography, portrait, contact details, external profiles, and synchronization preferences |
| `Publication` | Bibliographic metadata, raw BibTeX, image, files, author formatting, and optional Markdown details |
| `PublicationFile` | Ordered uploaded files or external URLs attached to a publication |
| `Research` | Bilingual project title, summary, description, dates, image, and optional detail page |
| `News` | Bilingual title, summary, content, image, and optional detail page |
| `Section` / `SectionItem` | Custom homepage sections and their ordered Markdown entries (with optional detail pages) |
| `MediaFile` | Managed Markdown assets with opaque access keys and activation control |
| `SystemConfig` | Language, pagination, synchronization, footer, integration, and monitoring settings |
| `AIConfig` | LLM provider endpoint, model, credentials, parameters, and health state |
| `ResourceMetricLog` | Historical CPU, memory, disk, and network measurements |

### Technology stack

| Area | Technology |
| --- | --- |
| Backend | Python and Django 4.2 |
| Database | SQLite by default |
| Frontend | Django Templates, HTML, CSS, and vanilla JavaScript |
| Content | Markdown and BibTeX |
| Tasks | Celery Worker/Beat with RabbitMQ in Docker Compose |
| Integrations | ORCID, Google Scholar, and OpenAI-compatible chat-completions APIs |
| Monitoring | psutil with database-backed history |
| Container runtime | Docker Compose and Python 3.11 |

### Project structure

```text
MyHomePage/
|-- HomePage/                  # Django settings, root URLs, and version.py
|-- myHomePage/                # Main application
|   |-- management/commands/   # Sync, diagnostics, and Docker initialization commands
|   |-- migrations/            # Database migrations
|   |-- admin.py               # Customized administration portal
|   |-- ai_services.py         # LLM provider adapters
|   |-- backup.py              # System backup: create, import, restore
|   |-- middleware.py          # Language, login, session, and file-access controls
|   |-- models.py              # Content and configuration models
|   |-- resource_monitor.py    # Resource sampling and retention
|   |-- security.py            # Login cryptography helpers
|   |-- services.py            # ORCID/Scholar synchronization and deduplication
|   |-- tasks.py               # Celery tasks
|   |-- urls.py                # Application routes
|   `-- views.py               # Public views and protected downloads
|-- templates/                 # Public, detail, error, admin, and shared include templates
|-- static/                    # CSS, JavaScript, icons, and fonts
|-- locale/                    # English and Simplified Chinese catalogs
|-- media/                     # User uploads (ignored by Git except media/.gitkeep)
|-- deploy/nginx/              # Production Nginx examples and bilingual guide
|-- Dockerfile
|-- compose.yaml
|-- docker-up.ps1             # Windows startup helper
|-- docker-up.sh              # Linux/macOS startup helper
|-- requirements.txt
|-- requirements-docker.txt
`-- manage.py
```

### Quick start with Docker Compose

Docker is the recommended way to run the complete local stack. It starts Django, RabbitMQ, Celery Worker, Celery Beat, and an initialization service.

Requirements: Docker Desktop or Docker Engine with Compose v2, plus Git.

Windows PowerShell:

```powershell
git clone https://github.com/Zijian-Zhou/MyHomePage.git
cd MyHomePage
Copy-Item .env.example .env
.\docker-up.ps1
```

If PowerShell blocks local scripts:

```powershell
powershell -ExecutionPolicy Bypass -File .\docker-up.ps1
```

Linux/macOS:

```bash
git clone https://github.com/Zijian-Zhou/MyHomePage.git
cd MyHomePage
cp .env.example .env
sh ./docker-up.sh
```

The script builds and starts the services, runs migrations, creates the first `superadmin`, prints its one-time credentials, and removes the temporary credential file. The generated password has this format:

```text
MyPageAdmin@YYYYMMDDHHMM
```

Change the generated password immediately:

```powershell
docker compose exec web python manage.py changepassword superadmin
```

Open:

- Homepage: <http://127.0.0.1:5000/en/>
- Chinese homepage: <http://127.0.0.1:5000/zh-hans/>
- Administration: <http://127.0.0.1:5000/en/admin/>

Useful commands:

```powershell
docker compose ps
docker compose logs -f web worker beat
docker compose down
```

Runtime data:

- SQLite: `docker-data/db.sqlite3`
- Uploaded files: `media/`
- Collected static files: `staticfiles/` (generated and safe to recreate)
- RabbitMQ: Docker volume `homepage_rabbitmq-data`

#### Host mounts and persistence

Compose bind-mounts the host directory `./docker-data` at `/data` in every Django/Celery container. Django uses `/data/db.sqlite3`, so database changes made inside a container are written directly to `docker-data/db.sqlite3` on the host. The repository-root `db.sqlite3` is **not** mounted or used by the containers.

The host `./media` directory is mounted at `/app/media`, so uploaded files are also shared with and retained on the host. Its contents are ignored by Git (only `media/.gitkeep` is tracked), so uploads never end up in the repository. System backups are written to `docker-data/backups/` (`BACKUP_ROOT=/data/backups`). The generated `./staticfiles` directory is mounted at `/app/staticfiles` for `collectstatic` and Nginx. RabbitMQ uses the Docker-managed `homepage_rabbitmq-data` named volume instead of a bind mount.

To initialize Docker from the existing repository-root database, stop the stack before copying it:

```powershell
# Windows PowerShell
docker compose down
New-Item -ItemType Directory -Force docker-data | Out-Null
Copy-Item .\db.sqlite3 .\docker-data\db.sqlite3 -Force
```

```bash
# Linux/macOS
docker compose down
mkdir -p docker-data
cp ./db.sqlite3 ./docker-data/db.sqlite3
```

`docker compose down` removes containers and the Compose network but preserves all three data locations. `docker compose down -v` additionally removes the RabbitMQ named volume, but it does not delete the bind-mounted `docker-data` or `media` directories. Back up both `docker-data/db.sqlite3` and `media/` for a complete site backup, and never replace the database file while the services are running.

On Linux/macOS, a newly created bind-mounted directory may initially be owned by `root`. The `init` service starts with temporary root privileges only to assign `/data` and `/app/media` to the container's `django` user, then drops privileges before running migrations. Web, Worker, and Beat always run as the non-root `django` user. If initialization fails, both startup scripts automatically print the `init` service logs; when starting Compose directly, inspect them with `docker compose logs init`.

You may also run `docker compose up -d --build` directly on every platform. Detached mode cannot print container logs automatically. The credential file is intentionally readable only by the container's `django` user, so read and remove it through the Web container rather than accessing the bind-mounted host file directly:

```bash
docker compose exec -T web cat /data/superadmin-credentials.txt
docker compose exec -T web rm -f /data/superadmin-credentials.txt
```

Alternatively, use the platform-independent initialization log command:

```bash
docker compose logs init
```

Delete the plaintext credential file after reading it. Existing `superadmin` accounts are not reset on later starts.

> The included Compose stack uses Django's development server and `DEBUG=True` by default. It is intended for local use, not direct Internet-facing production deployment.

### Traditional local setup

```bash
git clone https://github.com/Zijian-Zhou/MyHomePage.git
cd MyHomePage
python -m venv .venv
```

Activate and initialize:

```bash
# Linux/macOS
source .venv/bin/activate

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

For scheduled synchronization outside Docker, install a compatible Celery release and provide RabbitMQ or another supported broker before starting Worker and Beat.

### Initial administration setup

1. Create or edit an active `Profile`.
2. Add publications, research projects, and news entries.
3. Add custom sections when additional homepage blocks are needed.
4. Review `SystemConfig`, especially Chinese mode, cards per page, synchronization interval, highlighted authors, footer JSON, and resource-log retention.
5. Upload reusable assets in **File Manager** (the Media Files page) and use their copied links or Markdown snippets in content.

### File Manager

The Media Files page is a small file manager over everything uploaded to the site (`MEDIA_ROOT`), one folder per purpose: **Uploads** (`markdown_assets/`), profile, news, publication and research images, and the private publication files.

- **Uploads** is the free area: upload (drag and drop, up to 50 MB per file; HTML/SVG/scripts are refused), create folders, rename, move, edit a file's title and Active/Draft flags, copy its link or Markdown snippet, and delete.
- The other folders belong to their records: files can be browsed, previewed and downloaded, and a file no record uses any more can be deleted. A file still used by a record cannot be deleted.
- Every file shows where it is used (record fields and links in Markdown/settings). Renaming, moving or deleting a file that content links to asks for confirmation first; `/media-file/<key>/` links keep working after a rename or move.
- **Preview** shows images, video, audio, PDF and plain-text files (`.txt/.md/.csv/.json/.bib/.tex`) in the browser; Office documents are download-only.
- **Unused files** lists every file nothing references, for clean-up. All file operations are recorded in the audit log.
6. Configure ORCID, Google Scholar, or one or more AI providers only when needed.

Most content records support `is_active`, `is_draft`, and `order`. Draft and inactive records are excluded from the public homepage. Higher positive `order` values are displayed first for models whose ordering is descending.

### System configuration

| Category | Description |
| --- | --- |
| `enable_chinese` | Enables Chinese routes, fields, controls, and content |
| `cards_per_page` | Maximum cards shown per section page |
| `items_per_page` | Rows per page in every admin list (default 20, 1-500). Pages are fetched one at a time and cached in the browser tab; the cache is cleared on save/delete/actions, on logout and when the tab closes |
| `sync_interval` | Automatic publication synchronization interval in hours; default `24` |
| `scholar_proxy` | Optional Google Scholar proxy; direct access is attempted when empty |
| `highlighted_authors` | Semicolon-separated authors highlighted across publications |
| `footer_items` | Footer items: display name (required), optional icon and link |
| `resource_log_retention_hours` | Resource-history retention; default `168` hours |

`footer_items` is edited in a table: each row has a **display name** (required), an optional **icon** and an optional **link**, and rows can be reordered or removed. The icon accepts Font Awesome classes (for example `fab fa-github` or `fas fa-envelope`) or an image URL (`http(s)://...` or a site path such as a media-file link). The upload button next to the icon field stores a PNG/JPG/GIF/WEBP/ICO image (up to 2 MB; SVG is not accepted) as an active Media File and fills in its link. Links may use `http(s)://`, `mailto:`, `tel:`, a site path starting with `/`, or a `#` anchor; other schemes such as `javascript:` are rejected. The value is stored as JSON, and the older format without icons is still accepted:

```json
{
  "item": [
    {"content": "Research Group"},
    {"content": "GitHub", "icon": "fab fa-github", "href": "https://github.com/example"},
    {"content": "University", "href": "https://example.com"}
  ]
}
```

Both browser-side and server-side validation reject malformed footer and AI configuration JSON.

### System backup

Superusers can open **System Backup** from the administration index. A backup is a `.zip` archive that contains:

- `manifest.json`: format marker, app version, creation time, record/file counts, and the applied migrations;
- `data.json`: every database record (content, configuration, users and groups, AI providers, admin log, audit log, resource-monitor history), exported with natural foreign keys. Sessions, content types and permissions are not included; content types and permissions are recreated automatically. On restore the audit log and resource-monitor history are merged with the current ones (nothing recorded since the backup is lost);
- `media/`: every uploaded file.

Available actions:

- **Create**: writes a new archive, with an optional note.
- **Import**: uploads an external archive; it is validated (format, safe paths, CRC) and added to the list.
- **Download / Delete**: manage the stored archives.
- **Restore**: replaces the whole database and media directory with the archive contents. An automatic `myhomepage-pre-restore-*.zip` backup of the current state is written first. The database is replaced in one transaction, and media files are rolled back if loading fails. Archives from a newer schema (unknown migrations) are refused. Everyone is signed out afterwards and must sign in with an account stored in the backup.

Archives are stored in `BACKUP_ROOT` (`backups/` locally, `docker-data/backups/` in Docker). They contain password hashes and API keys, so keep downloaded copies safe. Behind Nginx, imports are limited by `client_max_body_size` (100 MB in the sample configuration).

### Publication synchronization

```bash
python manage.py sync_publications
```

Enable `auto_sync_orcid` and/or `auto_sync_google_scholar` on the relevant profile. The scheduled task runs frequently but only synchronizes a profile after its configured interval has elapsed.

ORCID, GitHub and LinkedIn credentials are stored per profile, right below each platform's ID / link (followed by its auto-sync switch). Fill in the ORCID Client ID / Client Secret from ORCID Developer Tools, register the redirect URI shown there (`https://<your-domain>/orcid/callback/`) and click **Authorize ORCID**; the access token is saved on that profile. Secret values are never shown again after saving (leave the box blank to keep them, tick **Clear** to remove them).

ORCID diagnostics (`--profile <id>` defaults to the first active profile):

```bash
python manage.py check_orcid_config --check
python manage.py check_orcid_config --token YOUR_ORCID_ACCESS_TOKEN
```

Google Scholar may rate-limit or block automated requests. Use synchronization conservatively and comply with upstream terms.

### Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `DEBUG` | `True` | Django debug mode |
| `SECRET_KEY` | Development fallback | Signing key; must be replaced when `DEBUG=False` |
| `ALLOWED_HOSTS` | `127.0.0.1,localhost` | Accepted hostnames, comma-separated |
| `DATABASE_PATH` | `db.sqlite3` | SQLite database path |
| `MEDIA_ROOT` | `media/` | Uploaded-file directory |
| `BACKUP_ROOT` | `backups/` | System-backup archive directory (`/data/backups` in Docker) |
| `CELERY_BROKER_URL` | Local AMQP guest URL | Celery broker connection |
| `ENABLE_RESOURCE_MONITOR` | `True` | Starts the background resource sampler |
| `ENABLE_IP_GEO_LANGUAGE` | `False` | Enables IP-based language selection |
| `TRUST_X_FORWARDED_FOR` | `False` | Read the client IP from the reverse proxy (`X-Real-IP`); set `True` behind Nginx so audit logs and login lockout see real client addresses |
| `SECURITY_MONITOR_ENABLED` | `True` | Record anomalous / attack traffic in the audit log |
| `SECURITY_FLOOD_PER_MINUTE` | `300` | Requests per minute from one IP that count as a flood |
| `SECURITY_404_PER_MINUTE` | `30` | 404 responses per minute from one IP that count as a scan |
| `LOGIN_MAX_ATTEMPTS` | `5` | Failed-login threshold |
| `LOGIN_ATTEMPT_WINDOW_SECONDS` | `600` | Login-attempt window |
| `LOGIN_LOCKOUT_SECONDS` | `900` | Lockout duration |
| `DEFAULT_SUPERADMIN_USERNAME` | `superadmin` | Docker-created administrator username |
| `DEFAULT_SUPERADMIN_EMAIL` | `admin@example.com` | Docker-created administrator email |
| `SECURE_SSL_REDIRECT` | Environment-dependent | Redirects HTTP to HTTPS |
| `SESSION_COOKIE_SECURE` | Environment-dependent | Restricts session cookies to HTTPS |
| `CSRF_COOKIE_SECURE` | Environment-dependent | Restricts CSRF cookies to HTTPS |
| `SECURE_HSTS_SECONDS` | Environment-dependent | HSTS lifetime |

`python-dotenv` is installed, but Django settings do not directly load `.env`; Docker Compose loads it automatically. For non-Docker execution, export variables through the shell or process manager.

### URL map

| Route | Description |
| --- | --- |
| `/<language>/` | Public homepage |
| `/<language>/publication/<id>/` | Publication detail or metadata summary |
| `/<language>/research/<id>/` | Research detail or summary |
| `/<language>/news/<id>/` | News detail or summary |
| `/<language>/admin/` | Administration portal |
| `/<language>/orcid/authorize/` | Start ORCID OAuth |
| `/<language>/orcid/callback/` | Complete ORCID OAuth |
| `/publication-file/<access-key>/` | Download or open a publication attachment |
| `/media-file/<access-key>/` | Access a managed media file |
| `/media/markdown_assets/<path>` | Controlled legacy Markdown-asset access |

### Production deployment

The supplied Compose file is a complete local stack, but production should use an HTTPS reverse proxy and a production WSGI/ASGI server rather than `runserver`.

An Nginx example for `example.com` and `www.example.com`, including HTTPS redirects, static/media delivery, and protected-file proxying, is provided at `deploy/nginx/example.com.conf`, with a temporary HTTP-only `deploy/nginx/example.com.http.conf` for obtaining the certificate. See `deploy/nginx/README.md` for bilingual step-by-step instructions and troubleshooting.

Common pitfalls when deploying to a cloud server:

- Open inbound TCP 80/443 in the cloud provider's security group, not only in `ufw`.
- Mainland-China servers require an ICP filing for the domain; otherwise the provider intercepts requests with its own `403` page and certificate renewal fails.
- Install the HTTP-only site and issue the certificate (`certbot --webroot`) before installing the HTTPS site, because `nginx -t` fails when certificate files are missing.
- Run `chmod 711 /home/<user>` so Nginx can read `staticfiles` and `media`.
- Keep `127.0.0.1,localhost` in `ALLOWED_HOSTS` so the container health check passes.
- Raise Nginx `client_max_body_size` (100 MB in the example) if backup archives to import are larger, and `proxy_read_timeout` (300 s) for very long backup/restore operations.
- Static files are cached by browsers for 7 days; the application's CSS/JS URLs carry version query strings, so users receive updates without clearing their cache.

Before production deployment:

1. Set `DEBUG=False` and provide a strong, unique `SECRET_KEY`.
2. Configure `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, HTTPS, secure cookies, and HSTS carefully.
3. Serve `STATIC_ROOT` (`./staticfiles`, filled by `collectstatic`) and public media through Nginx.
4. Use persistent, backed-up database and media storage.
5. Consider PostgreSQL/MySQL instead of SQLite for concurrent workloads.
6. Run `python manage.py check --deploy` and resolve applicable warnings.
7. Rotate the generated default administrator password and all external API credentials.

### Development, testing, and limitations

```bash
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py test
python manage.py compilemessages
```

- SQLite can lock under concurrent writes and is best suited to small/local deployments.
- Google Scholar synchronization depends on an unofficial web surface and may break after upstream changes.
- The automated test suite is still limited and needs broader regression coverage.
- The Docker resource monitor reports container-level resources, not complete host metrics.
- Docker Compose uses the development server unless replaced for production.
- Static asset URLs carry version query strings (`APP_VERSION`, plus the file modification time for ModelAdmin `Media`); keep them when adding new assets so deployments bypass stale caches.

### License

Licensed under the [GNU General Public License v3.0](LICENSE).

---

<a id="简体中文"></a>

## 简体中文

### 项目简介

MyHomePage 是一个面向研究人员、学生、实验室和专业人士的自托管学术主页与内容管理系统。系统将响应式公开主页与定制 Django 管理后台结合，管理员无需修改模板即可维护个人资料、出版物、研究项目、新闻、自定义栏目、文件、AI 服务和全站配置。

系统支持英文与简体中文、Markdown 内容、ORCID 和 Google Scholar 同步、论文去重、多模型 LLM 辅助、受控文件访问、数据库会话及实时资源监控。

### 功能特性

#### 公开主页

- 浅色（雾蓝 Mist）和深色（石板 Slate）主题，与管理后台保持一致；已保存的主题会在页面首次绘制前生效，刷新时不会闪白。
- 适配手机和平板：顶栏压缩为两行，导航栏可左右滑动，所有可点击区域都适合手指操作。
- 关于、新闻、出版物、研究、联系方式和自定义栏目使用统一的卡片样式。
- “关于我”布局：头像与 “About Me” 标题对齐；左侧资料栏较高时，简介卡片会自动拉伸到与联系卡片底部对齐。
- 联系信息区：地址居中显示，邮箱、电话、ORCID、Google Scholar、GitHub、ResearchGate、LinkedIn 以胶囊按钮展示。
- 栏目中的图片悬停时有缩放动画，双击（触屏双击）可全屏查看；PNG 图片（通常是透明 Logo）不加阴影。
- 点击导航会平滑滚动到对应栏目标题，停在固定顶栏下方，并高亮当前所在栏目。
- 页面切换和长时间操作使用柔和的遮罩和“吃豆豆”加载动画，避免刷新时闪白。
- 全站统一的细滚动条，随主题变色。
- 展示个人资料、头像、联系方式、学术平台链接和 Markdown 个人简介。
- 出版物卡片支持高亮作者、通讯作者、期刊、日期、DOI、关键词、图片、BibTeX、详情页和有序附件。
- 支持一键复制 BibTeX，并提供中英文复制状态反馈。
- 论文附件既可以上传本地文件，也可以填写外部 URL；内置 PDF、Slides、Code、Data、Supplement 等显示文字。
- 新闻和研究项目支持摘要、图片、可选 Markdown 详情页，以及上一篇/下一篇导航。
- 新闻或研究摘要为空时，自动截取正文前 300 个字词作为摘要。
- 支持自定义主页栏目和有序栏目条目，内容可使用 Markdown；条目可启用独立详情页并单独填写详情内容（卡片显示“查看详情”链接）；后台条目可折叠，并带独立的保存 / 删除按钮，后台可对条目内容进行 Markdown 预览。
- 每个栏目独立异步分页；切换某个栏目页码不会重置其他栏目，也不会刷新整个页面。
- 数据数量为 0 的栏目不会出现在主页导航和内容区域。
- 支持配置页脚项（显示名称、可选图标和链接；图标可以是 Font Awesome 类名、图片地址或上传的图片），并提供统一美化的 4xx、5xx 和禁止访问页面。
- 页脚显示当前运行版本（`Powered By MyHomePage v1.1.0`），版本号统一定义在 `HomePage/version.py`。

#### 中英文内容

- 通过 Django 国际化提供英文和简体中文路由。
- 个人简介/地址、新闻、研究、自定义栏目、标题、摘要、描述和详情正文均支持中文字段。
- 禁用中文模式后，中文字段和翻译按钮会自动隐藏。
- 禁用中文模式时，中文 URL 会自动纠正到英文 URL。
- 后台字段、验证提示、加载遮罩、详情导航和前台按钮均支持中英文显示。
- 支持使用已配置的翻译库自动翻译字段。
- 同步失败等提示信息跟随当前界面语言显示。

#### 管理后台

- 定制后台首页、导航、暗黑模式、响应式表单，以及可收缩的左右侧栏。
- 后台主题与前台一致（浅色/深色），页头和面包屑在滚动时固定在顶部，页脚始终贴在窗口底部。
- 按钮、上传区域、复选框和输入框聚焦样式统一；“翻译 / 预览 / AI 生成”按钮在字段下方排成一行。
- 适配平板和手机：大纲面板在平板上默认折叠、在手机上隐藏；列表表格可横向滑动，筛选面板移到表格下方。
- 页面跳转、保存、同步和备份等操作显示加载遮罩。
- 右侧大纲会列出当前配置页的字段分组，并支持点击跳转。
- 主要内容类型支持“保存”和“保存为草稿”。
- Profile 的 Bio 和论文详情正文支持 Markdown 预览。
- 支持解析/导入 BibTeX、保存原始 BibTeX 和编辑论文元数据。
- 论文详情支持 AI 生成：选择模型、显示处理进度、读取论文元数据和 PDF 等附件、预览结果、提交修改意见、手动编辑并保存中英文内容。
- 媒体文件系统会生成不可预测的访问键和可直接粘贴的 Markdown 片段。
- “系统配置”和“AI 配置”是后台同级入口。
- 页脚项以表格方式编辑，支持图标实时预览和图标上传（PNG/JPG/GIF/WEBP/ICO，保存到媒体文件）。
- 支持用户、用户组及本地化配置管理。
- 系统资源监控展示实时和历史 CPU、内存、磁盘、网络上下行速度，以及数据库、媒体文件和备份文件的存储占用。
- 日志审计（仅超级管理员）：记录登录成功/失败、锁定、登出、后台所有新增/修改/删除、出版物同步和备份操作，包含用户、IP 和浏览器信息；支持筛选、搜索、近 24 小时统计、导出 CSV（所选记录或“导出全部日志”），保留天数可配置（`audit_log_retention_days`，默认 180 天）。审计日志包含在备份中；恢复时会与当前日志合并，不会被回滚。
- 异常日志（审计分类 **异常**）：记录 URL/请求头中的攻击特征（SQL 注入、XSS、路径穿越、命令注入、Log4Shell）、对常见攻击目标的探测（`.env`、`.git`、`wp-admin`、phpMyAdmin、`*.php`、备份文件等）、已知扫描工具的 User-Agent、单个 IP 的请求过载和大量 404、Django 拒绝的请求（伪造 Host 头、CSRF 校验失败）以及服务器错误（500）。同一来源 10 分钟内的重复事件合并为一条并累计次数，每分钟新增条数有上限，攻击时不会把数据库写满。只记录不拦截；已登录的管理员不受监控。阈值：`SECURITY_FLOOD_PER_MINUTE`（300）、`SECURITY_404_PER_MINUTE`（30）；频率类规则需要在 Nginx 后面设置 `TRUST_X_FORWARDED_FOR=True`。
- 系统备份（仅超级管理员）：一键备份数据库和 media 文件，支持下载、删除、导入外部备份，以及恢复（恢复前自动创建安全备份）。

#### 出版物同步

- 每个 Profile 可分别启用 ORCID 和 Google Scholar。
- 支持单条手动同步、批量同步、管理命令同步和 Celery 定时同步。
- 未配置代理时会尝试直连；不同来源的失败互不影响。
- 重复论文主要按照规范化后的标题匹配。
- 重复记录会相互补充缺失字段，并保留信息最丰富的值，包括原始 BibTeX。
- 同步提示显示去重后的实际结果。
- 同步间隔以小时配置，无需修改 Celery 调度代码即可生效。

#### AI 接入

- 可创建多个独立的 `AIConfig` 模型配置。
- 内置 OpenAI Official、通用 OpenAI Compatible、DeepSeek、GLM BigModel、SCNet Qwen 和 SCNet MiniMax 类型。
- 可配置 Base URL、模型、API Key、默认模型、启用状态和额外 JSON 参数。
- 支持单个、选中项和全部模型的连通性/保活测试。
- 论文详情生成会读取论文元数据、PDF 等可读附件，以及 `templates/paper_introduction_framework*.md` 中的中英文模板。

#### 安全与运维

- 后台登录字段在浏览器端进行 RSA 加密，服务端 RSA 密钥每 10 分钟轮换。
- 受保护的登录交换流程中使用 SHA-256。
- 支持登录频率限制、临时锁定、本地化锁定页面和实时倒计时。
- 登录会话存储在数据库中，有效期 30 分钟，并每小时清理过期会话。
- 在数据库和密钥保持不变时，普通服务重启不会使有效会话立即失效。
- 媒体文件只有在激活时才允许公开访问；未激活文件仅管理员登录后可访问。
- 论文下载链接使用非连续访问键，不直接暴露数据库 ID。
- 替换或删除媒体文件、头像、论文图片和论文附件时，会同步删除存储中的实际文件。
- 用户维护的 Markdown 在渲染前会转义原始 HTML。
- 支持通过环境变量配置 HTTPS 跳转、安全 Cookie、HSTS、防嵌入和 Referrer Policy。
- 资源监控历史写入数据库，并根据系统配置的保留时长自动清理。

### 数据模型

| 模型 | 用途 |
| --- | --- |
| `Profile` | 身份信息、简介、头像、联系方式、外部平台和同步设置 |
| `Publication` | 论文元数据、原始 BibTeX、图片、附件、作者样式和可选 Markdown 详情 |
| `PublicationFile` | 论文下有序排列的上传文件或外部 URL |
| `Research` | 双语研究标题、摘要、描述、日期、图片和可选详情页 |
| `News` | 双语新闻标题、摘要、正文、图片和可选详情页 |
| `Section` / `SectionItem` | 自定义主页栏目及其中的有序 Markdown 条目（条目可启用详情页） |
| `MediaFile` | 带访问键和激活控制的 Markdown 媒体资源 |
| `SystemConfig` | 语言、分页、同步、页脚、外部服务和监控设置 |
| `AIConfig` | LLM 地址、模型、凭据、参数和健康状态 |
| `ResourceMetricLog` | CPU、内存、磁盘和网络历史监测数据 |

### 技术栈与项目结构

| 范围 | 技术 |
| --- | --- |
| 后端 | Python、Django 4.2 |
| 数据库 | 默认 SQLite |
| 前端 | Django Templates、HTML、CSS、原生 JavaScript |
| 内容 | Markdown、BibTeX |
| 后台任务 | Docker Compose 中的 Celery Worker/Beat 和 RabbitMQ |
| 外部服务 | ORCID、Google Scholar、OpenAI 兼容 Chat Completions API |
| 系统监控 | psutil、数据库历史日志 |
| 容器环境 | Docker Compose、Python 3.11 |

```text
MyHomePage/
|-- HomePage/                  # Django 配置、根路由和版本号 version.py
|-- myHomePage/                # 模型、视图、后台、服务、任务、系统备份和迁移
|-- templates/                 # 主页、详情、错误、后台模板和公共片段
|-- static/                    # CSS、JavaScript、图标和字体
|-- locale/                    # 英文和简体中文翻译目录
|-- media/                     # 用户上传文件（除 media/.gitkeep 外不纳入 Git）
|-- deploy/nginx/              # 生产环境 Nginx 示例和中英双语部署指南
|-- Dockerfile
|-- compose.yaml
|-- docker-up.ps1             # Windows 启动脚本
|-- docker-up.sh              # Linux/macOS 启动脚本
|-- requirements.txt
|-- requirements-docker.txt
`-- manage.py
```

### 使用 Docker Compose 快速启动

Docker 是运行完整本地环境的推荐方式，会同时启动 Django、RabbitMQ、Celery Worker、Celery Beat 和初始化服务。需要 Docker Desktop 或带 Compose v2 的 Docker Engine，以及 Git。

Windows PowerShell：

```powershell
git clone https://github.com/Zijian-Zhou/MyHomePage.git
cd MyHomePage
Copy-Item .env.example .env
.\docker-up.ps1
```

如果 PowerShell 禁止执行本地脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\docker-up.ps1
```

Linux/macOS：

```bash
git clone https://github.com/Zijian-Zhou/MyHomePage.git
cd MyHomePage
cp .env.example .env
sh ./docker-up.sh
```

脚本会构建并启动服务、执行数据库迁移、首次创建 `superadmin`、显示一次性登录凭据，然后删除临时凭据文件。密码格式为 `MyPageAdmin@年月日小时分钟`，实际使用 12 位数字时间戳，例如 `MyPageAdmin@202610252130`。

登录后请立即修改密码：

```powershell
docker compose exec web python manage.py changepassword superadmin
```

访问地址：

- 英文主页：<http://127.0.0.1:5000/en/>
- 中文主页：<http://127.0.0.1:5000/zh-hans/>
- 管理后台：<http://127.0.0.1:5000/en/admin/>

常用命令：

```powershell
docker compose ps
docker compose logs -f web worker beat
docker compose down
```

持久化数据位置：

- SQLite：`docker-data/db.sqlite3`
- 上传文件：`media/`
- 收集后的静态文件：`staticfiles/`（自动生成，可重新创建）
- RabbitMQ：Docker 数据卷 `homepage_rabbitmq-data`

#### 宿主机挂载与数据持久化

Compose 会把宿主机的 `./docker-data` 目录绑定挂载到所有 Django/Celery 容器中的 `/data`。Django 实际使用 `/data/db.sqlite3`，因此容器内产生的数据库修改会直接写入宿主机的 `docker-data/db.sqlite3`。项目根目录下原有的 `db.sqlite3` **不会**被容器挂载或使用。

宿主机的 `./media` 会绑定挂载到容器的 `/app/media`，因此上传文件同样保留并共享在宿主机。该目录的内容不纳入 Git（只跟踪 `media/.gitkeep`），上传的文件不会进入代码仓库。系统备份文件保存在 `docker-data/backups/`（`BACKUP_ROOT=/data/backups`）。自动生成的 `./staticfiles` 会挂载到 `/app/staticfiles`，供 `collectstatic` 和 Nginx 使用。RabbitMQ 不使用目录绑定，而是使用 Docker 管理的 `homepage_rabbitmq-data` 命名卷。

如果需要让 Docker 使用项目根目录已有的数据库，必须先关闭服务再复制：

```powershell
# Windows PowerShell
docker compose down
New-Item -ItemType Directory -Force docker-data | Out-Null
Copy-Item .\db.sqlite3 .\docker-data\db.sqlite3 -Force
```

```bash
# Linux/macOS
docker compose down
mkdir -p docker-data
cp ./db.sqlite3 ./docker-data/db.sqlite3
```

`docker compose down` 只删除容器和 Compose 网络，不会删除上述三处数据。`docker compose down -v` 会额外删除 RabbitMQ 命名卷，但不会删除绑定挂载的 `docker-data` 和 `media` 目录。完整备份站点时应同时备份 `docker-data/db.sqlite3` 和 `media/`，并且不要在容器运行期间替换数据库文件。

在 Linux/macOS 上，新建的绑定挂载目录最初可能归 `root` 所有。`init` 服务仅在启动阶段临时以 root 身份修正 `/data` 和 `/app/media` 的所有权，随后在执行迁移前立即降权为容器内的 `django` 用户；Web、Worker 和 Beat 始终使用非 root 用户运行。如果初始化失败，Windows 和 Linux/macOS 启动脚本都会自动打印 `init` 日志；直接执行 Compose 时可使用 `docker compose logs init` 查看原因。

所有平台都可以直接执行 `docker compose up -d --build`。由于 `-d` 后台模式不会自动输出容器日志，而且凭据文件按安全要求仅允许容器内的 `django` 用户读取，因此不要在宿主机直接执行 `cat` 或 `Get-Content`。首次启动后使用 `docker compose exec -T web cat /data/superadmin-credentials.txt` 读取，再执行 `docker compose exec -T web rm -f /data/superadmin-credentials.txt` 删除；也可以在任意平台执行 `docker compose logs init` 查看初始化输出。后续启动不会重置已经存在的 `superadmin` 密码。

> 当前 Compose 默认使用 Django 开发服务器并设置 `DEBUG=True`，适合本地运行，不应直接暴露到公网生产环境。

### 传统本地启动

```bash
git clone https://github.com/Zijian-Zhou/MyHomePage.git
cd MyHomePage
python -m venv .venv
```

```bash
# Linux/macOS
source .venv/bin/activate

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

如果不使用 Docker 但需要定时同步，请额外安装兼容版本的 Celery，并配置 RabbitMQ 或其他支持的 Broker，再启动 Worker 和 Beat。

### 初始后台配置

1. 创建或编辑一个已激活的 `Profile`。
2. 添加出版物、研究项目和新闻。
3. 需要额外主页内容时添加自定义栏目。
4. 检查 `SystemConfig`，特别是中文模式、每页卡片数、同步间隔、高亮作者、页脚 JSON 和资源日志保留时间。
5. 在 **文件管理**（原“媒体文件”页面）上传可复用资源，复制链接或 Markdown 片段用于内容中。

### 文件管理

“媒体文件”页面是一个简单的文件管理器，管理网站上传的所有文件（`MEDIA_ROOT`），按用途分文件夹：**上传文件**（`markdown_assets/`）、头像、新闻、论文、研究图片，以及私有的论文附件。

- **上传文件** 是自由区域：可上传（支持拖拽，单个文件 ≤ 50 MB，拒绝 HTML/SVG/脚本）、新建文件夹、重命名、移动、编辑标题和启用/草稿状态、复制链接或 Markdown 片段、删除。
- 其他文件夹由对应的内容记录管理：可以浏览、预览、下载；不再被任何记录使用的文件可以删除，仍被记录使用的文件不能删除。
- 每个文件都会显示使用位置（记录字段以及 Markdown/配置中的链接）。重命名、移动或删除被内容链接的文件前会先确认；`/media-file/<key>/` 形式的链接在重命名或移动后仍然有效。
- **预览** 支持图片、视频、音频、PDF 和纯文本文件（`.txt/.md/.csv/.json/.bib/.tex`）；Office 文档只能下载。
- **未使用的文件** 列出所有没有被引用的文件，方便清理。所有文件操作都会写入日志审计。
6. 仅在需要时配置 ORCID、Google Scholar 或 AI Provider。

多数内容记录支持 `is_active`、`is_draft` 和 `order`。草稿和未激活记录不会显示在公开主页。对于采用倒序排序的模型，较大的正数 `order` 会优先显示。

### 系统配置

| 配置类型 | 说明 |
| --- | --- |
| `enable_chinese` | 开启中文路由、字段、控件和内容 |
| `cards_per_page` | 每个栏目单页最多显示的卡片数量 |
| `items_per_page` | 管理后台所有列表每页条数（默认 20，范围 1-500）。翻页时只请求当前页并缓存在当前标签页中；保存、删除、执行操作、退出登录或关闭页面时清除缓存 |
| `sync_interval` | 自动同步间隔，单位为小时，默认 `24` |
| `scholar_proxy` | 可选 Google Scholar 代理；为空时尝试直连 |
| `highlighted_authors` | 全局高亮作者，使用分号分隔 |
| `footer_items` | 页脚项：显示名称（必填）、图标和链接（选填） |
| `resource_log_retention_hours` | 资源监控历史保留时间，默认 `168` 小时 |

`footer_items` 使用表格编辑：每行包含**显示名称**（必填）、**图标**（选填）和**链接**（选填），可以调整顺序或删除。图标可填写 Font Awesome 类名（如 `fab fa-github`、`fas fa-envelope`）或图片地址（`http(s)://...` 或媒体文件链接等站内路径）。点击图标输入框旁的上传按钮，可上传 PNG/JPG/GIF/WEBP/ICO 图片（≤ 2 MB，出于安全考虑不支持 SVG），图片会保存为启用状态的媒体文件并自动填入链接。链接支持 `http(s)://`、`mailto:`、`tel:`、以 `/` 开头的站内路径和 `#` 锚点，`javascript:` 等其他协议会被拒绝。配置以 JSON 存储，旧版不带图标的格式仍然兼容：

```json
{
  "item": [
    {"content": "研究团队"},
    {"content": "GitHub", "icon": "fab fa-github", "href": "https://github.com/example"},
    {"content": "学校主页", "href": "https://example.com"}
  ]
}
```

页脚配置和 AI 配置的 JSON 均会进行前端和后端格式校验。

### 系统备份

超级管理员可在后台首页进入 **系统备份**。备份文件是一个 `.zip` 压缩包，包含：

- `manifest.json`：格式标识、系统版本、创建时间、记录数和文件数，以及已应用的数据库迁移；
- `data.json`：全部数据库记录（内容、配置、用户和用户组、AI 配置、后台操作日志、审计日志、资源监控历史），使用自然外键导出。不包含会话、ContentType 和权限，其中 ContentType 和权限会自动重建。恢复时审计日志和资源监控历史与当前记录合并，备份之后新增的记录不会丢失；
- `media/`：全部上传文件。

支持的操作：

- **新建备份**：生成新的备份文件，可填写备注。
- **导入外部备份**：上传外部备份文件，校验格式、路径安全和 CRC 后加入列表。
- **下载 / 删除**：管理已有备份文件。
- **恢复**：用备份内容整体替换当前数据库和 media 目录。恢复前会自动生成当前状态的 `myhomepage-pre-restore-*.zip` 备份。数据库在单个事务中替换，加载失败时 media 文件也会回滚。来自更新版本（包含未知迁移）的备份会被拒绝。恢复后所有用户都会退出登录，需要使用备份中的账号重新登录。

备份文件保存在 `BACKUP_ROOT`（本地默认 `backups/`，Docker 中为 `docker-data/backups/`）。备份包含密码哈希和 API 密钥，请妥善保管下载的副本。通过 Nginx 访问时，导入文件大小受 `client_max_body_size` 限制（示例配置为 100 MB）。

### 出版物同步

```bash
python manage.py sync_publications
```

需要先在对应 Profile 中启用 `auto_sync_orcid` 和/或 `auto_sync_google_scholar`。定时任务会高频检查，但只有达到系统配置的同步间隔后才会真正同步。

ORCID、GitHub、LinkedIn 的凭据按个人资料分别保存，紧跟在各平台的 ID / 链接下方（其后是该平台的自动同步开关）。填写在 ORCID 开发者工具中获取的 Client ID / Client Secret，登记页面上显示的回调地址（`https://<你的域名>/orcid/callback/`），然后点击 **授权 ORCID**，访问令牌会保存到该个人资料。密钥保存后不再显示（留空即保持不变，勾选 **清除** 可删除）。

ORCID 诊断命令（`--profile <id>` 默认为第一个启用的个人资料）：

```bash
python manage.py check_orcid_config --check
python manage.py check_orcid_config --token YOUR_ORCID_ACCESS_TOKEN
```

Google Scholar 可能限制或阻止自动请求，请控制同步频率并遵守上游服务条款。

### 环境变量

| 变量 | 默认值 | 用途 |
| --- | --- | --- |
| `DEBUG` | `True` | Django 调试模式 |
| `SECRET_KEY` | 开发回退值 | 签名密钥；`DEBUG=False` 时必须替换 |
| `ALLOWED_HOSTS` | `127.0.0.1,localhost` | 允许的主机名，逗号分隔 |
| `DATABASE_PATH` | `db.sqlite3` | SQLite 数据库路径 |
| `MEDIA_ROOT` | `media/` | 上传文件目录 |
| `BACKUP_ROOT` | `backups/` | 系统备份文件目录（Docker 中为 `/data/backups`） |
| `CELERY_BROKER_URL` | 本地 AMQP guest 地址 | Celery Broker 连接地址 |
| `ENABLE_RESOURCE_MONITOR` | `True` | 是否启动后台资源采样线程 |
| `ENABLE_IP_GEO_LANGUAGE` | `False` | 是否根据 IP 自动选择语言 |
| `TRUST_X_FORWARDED_FOR` | `False` | 从反向代理（`X-Real-IP`）读取真实客户端 IP；部署在 Nginx 后面时设为 `True`，审计日志和登录锁定才能识别真实 IP |
| `SECURITY_MONITOR_ENABLED` | `True` | 把异常/攻击流量记录到审计日志 |
| `SECURITY_FLOOD_PER_MINUTE` | `300` | 单个 IP 每分钟请求数超过该值视为请求过载 |
| `SECURITY_404_PER_MINUTE` | `30` | 单个 IP 每分钟 404 次数超过该值视为扫描 |
| `LOGIN_MAX_ATTEMPTS` | `5` | 登录失败次数阈值 |
| `LOGIN_ATTEMPT_WINDOW_SECONDS` | `600` | 登录失败统计窗口 |
| `LOGIN_LOCKOUT_SECONDS` | `900` | 锁定时长 |
| `DEFAULT_SUPERADMIN_USERNAME` | `superadmin` | Docker 自动创建的管理员用户名 |
| `DEFAULT_SUPERADMIN_EMAIL` | `admin@example.com` | Docker 自动创建的管理员邮箱 |
| `SECURE_SSL_REDIRECT` | 根据环境决定 | 是否强制跳转 HTTPS |
| `SESSION_COOKIE_SECURE` | 根据环境决定 | 是否仅通过 HTTPS 发送 Session Cookie |
| `CSRF_COOKIE_SECURE` | 根据环境决定 | 是否仅通过 HTTPS 发送 CSRF Cookie |
| `SECURE_HSTS_SECONDS` | 根据环境决定 | HSTS 有效时间 |

项目安装了 `python-dotenv`，但 Django 配置不会主动读取 `.env`；Docker Compose 会自动读取。非 Docker 运行时，请通过 Shell 或进程管理器导出环境变量。

### URL 路由

| 路由 | 说明 |
| --- | --- |
| `/<language>/` | 公开主页 |
| `/<language>/publication/<id>/` | 论文详情或元数据摘要 |
| `/<language>/research/<id>/` | 研究详情或摘要 |
| `/<language>/news/<id>/` | 新闻详情或摘要 |
| `/<language>/admin/` | 管理后台 |
| `/<language>/orcid/authorize/` | 开始 ORCID OAuth |
| `/<language>/orcid/callback/` | 完成 ORCID OAuth |
| `/publication-file/<access-key>/` | 下载或打开论文附件 |
| `/media-file/<access-key>/` | 访问受管理媒体文件 |
| `/media/markdown_assets/<path>` | 受控的旧版 Markdown 资源访问 |

### 生产部署

当前 Compose 提供完整的本地运行环境，但生产环境应使用 HTTPS 反向代理和正式 WSGI/ASGI Server，而不是 `runserver`。

项目已在 `deploy/nginx/example.com.conf` 提供适用于 `example.com` 和 `www.example.com` 的 Nginx 示例，包含 HTTPS 跳转、静态/媒体资源访问和受保护文件转发；另提供申请证书前使用的临时 HTTP 配置 `deploy/nginx/example.com.http.conf`。双语分步说明和常见问题见 `deploy/nginx/README.md`。

部署到云服务器时的常见问题：

- 需要在云厂商**安全组**中放行入方向 TCP 80/443，仅配置 `ufw` 不够。
- 中国内地服务器的域名必须完成 ICP 备案，否则云厂商会用自己的 `403` 页面拦截请求，证书也无法续期。
- 先启用临时 HTTP 配置并申请证书（`certbot --webroot`），再安装 HTTPS 配置，否则证书文件不存在会导致 `nginx -t` 失败。
- 执行 `chmod 711 /home/<用户名>`，使 Nginx 能读取 `staticfiles` 和 `media`。
- `ALLOWED_HOSTS` 中保留 `127.0.0.1,localhost`，否则容器健康检查失败。
- 需要导入的备份文件超过 100 MB 时，调大 Nginx 的 `client_max_body_size`；备份/恢复耗时很长时，调大 `proxy_read_timeout`（示例为 300 秒）。
- 静态文件在浏览器中缓存 7 天；系统的 CSS/JS 地址带有版本参数，更新部署后用户无需手动清缓存。

上线前至少需要：

1. 设置 `DEBUG=False`，并提供新的高强度 `SECRET_KEY`。
2. 正确配置 `ALLOWED_HOSTS`、`CSRF_TRUSTED_ORIGINS`、HTTPS、安全 Cookie 和 HSTS。
3. 通过 Nginx 提供 `STATIC_ROOT`（`./staticfiles`，由 `collectstatic` 生成）和公开媒体文件。
4. 为数据库和媒体文件配置持久化与备份。
5. 高并发环境考虑使用 PostgreSQL/MySQL 替代 SQLite。
6. 执行 `python manage.py check --deploy` 并处理适用警告。
7. 修改默认管理员密码，并定期轮换所有外部 API 凭据。

### 开发、测试与已知限制

```bash
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py test
python manage.py compilemessages
```

- SQLite 并发写入时可能锁库，更适合小型或本地部署。
- Google Scholar 同步依赖非官方网页结构，上游改版后可能失效。
- 当前自动化测试覆盖仍有限，需要继续补充回归测试。
- Docker 中的资源监控反映容器资源，而不是宿主机完整资源。
- Docker Compose 默认仍使用开发服务器，生产环境需要替换。
- 静态资源地址带有版本参数（`APP_VERSION`，后台 ModelAdmin `Media` 还会附加文件修改时间）；新增资源时请沿用这一做法，避免部署后用户读到旧缓存。

### 开源协议

本项目使用 [GNU General Public License v3.0](LICENSE)。
