# MyHomePage

> A bilingual, database-driven academic homepage and administration system built with Django.<br>
> 基于 Django 的双语、数据库驱动学术主页与后台管理系统。

[![Python](https://img.shields.io/badge/Python-3.7%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.2-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

[English](#english) | [简体中文](#简体中文)

---

<a id="english"></a>

## English

### Overview

MyHomePage is a self-hosted academic profile and content management system for researchers, students, laboratories, and professionals. A responsive public homepage is paired with a customized Django administration portal, so profiles, publications, research projects, news, custom sections, files, AI providers, and site-wide settings can be managed without editing templates.

The application supports English and Simplified Chinese, Markdown content, ORCID and Google Scholar synchronization, publication deduplication, configurable LLM assistance, protected file delivery, database-backed sessions, and real-time resource monitoring.

### Features

#### Public website

- Responsive light and dark themes for desktop and mobile.
- Profile information, portrait, contact details, academic identity links, and a Markdown biography.
- Publication cards with highlighted/corresponding authors, venue, date, DOI, keywords, images, BibTeX, detail pages, and ordered file links.
- One-click BibTeX copy with localized feedback.
- Publication attachments can be uploaded files or external URLs, with labels such as PDF, Slides, Code, Data, and Supplement.
- News and research cards support summaries, optional Markdown detail pages, images, and previous/next navigation.
- When a news or research summary is empty, it is generated from the first 300 words/characters of the content.
- Custom homepage sections and ordered section items with Markdown rendering.
- Independent asynchronous pagination for each homepage section; changing one section does not reset the others or reload the whole page.
- Empty sections are omitted from both navigation and page content.
- Configurable JSON footer links and styled 4xx/5xx/access-denied pages.

#### Bilingual content

- English and Simplified Chinese routes through Django i18n.
- Chinese variants for profile biography/address, news, research, custom sections, titles, summaries, descriptions, and detail content.
- Chinese fields and translation controls are hidden when Chinese mode is disabled.
- Requests to Chinese URLs are redirected to English when Chinese mode is disabled.
- Administration labels, validation messages, overlays, detail navigation, and public controls are localized.
- Optional automatic field translation using the configured translation library.

#### Administration portal

- Customized dashboard, navigation, dark mode, responsive forms, and collapsible left/right sidebars.
- A right-side form outline links directly to configuration fieldsets.
- Save and Save as Draft workflows for managed content.
- Markdown preview for profile Bio and publication detail content.
- Publication BibTeX parsing/import, raw BibTeX storage, and metadata editing.
- AI-assisted publication detail generation with provider selection, progress states, PDF/file context, preview, feedback-based revision, manual editing, and save actions.
- Media library with generated access keys and ready-to-use Markdown snippets.
- System Configuration and AI Configuration are independent top-level administration entries.
- User/group management and localized configuration forms.
- System resource monitor with live and historical CPU, memory, disk, and network throughput charts.

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
| `Section` / `SectionItem` | Custom homepage sections and their ordered Markdown entries |
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
|-- HomePage/                  # Django settings and root URLs
|-- myHomePage/                # Main application
|   |-- management/commands/   # Sync, diagnostics, and Docker initialization commands
|   |-- migrations/            # Database migrations
|   |-- admin.py               # Customized administration portal
|   |-- ai_services.py         # LLM provider adapters
|   |-- middleware.py          # Language, login, session, and file-access controls
|   |-- models.py              # Content and configuration models
|   |-- resource_monitor.py    # Resource sampling and retention
|   |-- security.py            # Login cryptography helpers
|   |-- services.py            # ORCID/Scholar synchronization and deduplication
|   |-- tasks.py               # Celery tasks
|   |-- urls.py                # Application routes
|   `-- views.py               # Public views and protected downloads
|-- templates/                 # Public, detail, error, and admin templates
|-- static/                    # CSS, JavaScript, icons, and fonts
|-- locale/                    # English and Simplified Chinese catalogs
|-- media/                     # User-uploaded files
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

- Homepage: <http://127.0.0.1:8000/en/>
- Chinese homepage: <http://127.0.0.1:8000/zh-hans/>
- Administration: <http://127.0.0.1:8000/en/admin/>

Useful commands:

```powershell
docker compose ps
docker compose logs -f web worker beat
docker compose down
```

Runtime data:

- SQLite: `docker-data/db.sqlite3`
- Uploaded files: `media/`
- RabbitMQ: Docker volume `homepage_rabbitmq-data`

#### Host mounts and persistence

Compose bind-mounts the host directory `./docker-data` at `/data` in every Django/Celery container. Django uses `/data/db.sqlite3`, so database changes made inside a container are written directly to `docker-data/db.sqlite3` on the host. The repository-root `db.sqlite3` is **not** mounted or used by the containers.

The host `./media` directory is mounted at `/app/media`, so uploaded files are also shared with and retained on the host. RabbitMQ uses the Docker-managed `homepage_rabbitmq-data` named volume instead of a bind mount.

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
5. Upload reusable assets through Media Files and use their generated links in Markdown.
6. Configure ORCID, Google Scholar, or one or more AI providers only when needed.

Most content records support `is_active`, `is_draft`, and `order`. Draft and inactive records are excluded from the public homepage. Higher positive `order` values are displayed first for models whose ordering is descending.

### System configuration

| Category | Description |
| --- | --- |
| `enable_chinese` | Enables Chinese routes, fields, controls, and content |
| `cards_per_page` | Maximum cards shown per section page |
| `sync_interval` | Automatic publication synchronization interval in hours; default `24` |
| `scholar_proxy` | Optional Google Scholar proxy; direct access is attempted when empty |
| `orcid_client_id` / `orcid_client_secret` / `orcid_access_token` | ORCID integration credentials |
| `highlighted_authors` | Semicolon-separated authors highlighted across publications |
| `footer_items` | JSON-defined footer text and optional links |
| `resource_log_retention_hours` | Resource-history retention; default `168` hours |

Footer JSON accepts one item or a list:

```json
{
  "item": [
    {"content": "Research Group"},
    {"content": "University", "href": "https://example.com"}
  ]
}
```

Both browser-side and server-side validation reject malformed footer and AI configuration JSON.

### Publication synchronization

```bash
python manage.py sync_publications
```

Enable `auto_sync_orcid` and/or `auto_sync_google_scholar` on the relevant profile. The scheduled task runs frequently but only synchronizes a profile after its configured interval has elapsed.

ORCID diagnostics:

```bash
python manage.py check_orcid_config
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
| `CELERY_BROKER_URL` | Local AMQP guest URL | Celery broker connection |
| `ENABLE_RESOURCE_MONITOR` | `True` | Starts the background resource sampler |
| `ENABLE_IP_GEO_LANGUAGE` | `False` | Enables IP-based language selection |
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

Before production deployment:

1. Set `DEBUG=False` and provide a strong, unique `SECRET_KEY`.
2. Configure `ALLOWED_HOSTS`, HTTPS, secure cookies, and HSTS carefully.
3. Add production static-file collection/serving; the current settings do not define `STATIC_ROOT`.
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

- 支持桌面端和移动端的响应式亮色/暗色主题。
- 展示个人资料、头像、联系方式、学术平台链接和 Markdown 个人简介。
- 出版物卡片支持高亮作者、通讯作者、期刊、日期、DOI、关键词、图片、BibTeX、详情页和有序附件。
- 支持一键复制 BibTeX，并提供中英文复制状态反馈。
- 论文附件既可以上传本地文件，也可以填写外部 URL；内置 PDF、Slides、Code、Data、Supplement 等显示文字。
- 新闻和研究项目支持摘要、图片、可选 Markdown 详情页，以及上一篇/下一篇导航。
- 新闻或研究摘要为空时，自动截取正文前 300 个字词作为摘要。
- 支持自定义主页栏目和有序栏目条目，内容可使用 Markdown。
- 每个栏目独立异步分页；切换某个栏目页码不会重置其他栏目，也不会刷新整个页面。
- 数据数量为 0 的栏目不会出现在主页导航和内容区域。
- 支持通过 JSON 配置页脚，并提供统一美化的 4xx、5xx 和禁止访问页面。

#### 中英文内容

- 通过 Django 国际化提供英文和简体中文路由。
- 个人简介/地址、新闻、研究、自定义栏目、标题、摘要、描述和详情正文均支持中文字段。
- 禁用中文模式后，中文字段和翻译按钮会自动隐藏。
- 禁用中文模式时，中文 URL 会自动纠正到英文 URL。
- 后台字段、验证提示、加载遮罩、详情导航和前台按钮均支持中英文显示。
- 支持使用已配置的翻译库自动翻译字段。

#### 管理后台

- 定制后台首页、导航、暗黑模式、响应式表单，以及可收缩的左右侧栏。
- 右侧大纲会列出当前配置页的字段分组，并支持点击跳转。
- 主要内容类型支持“保存”和“保存为草稿”。
- Profile 的 Bio 和论文详情正文支持 Markdown 预览。
- 支持解析/导入 BibTeX、保存原始 BibTeX 和编辑论文元数据。
- 论文详情支持 AI 生成：选择模型、显示处理进度、读取论文元数据和 PDF 等附件、预览结果、提交修改意见、手动编辑并保存中英文内容。
- 媒体文件系统会生成不可预测的访问键和可直接粘贴的 Markdown 片段。
- “系统配置”和“AI 配置”是后台同级入口。
- 支持用户、用户组及本地化配置管理。
- 系统资源监控展示实时和历史 CPU、内存、磁盘、网络上下行速度。

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
| `Section` / `SectionItem` | 自定义主页栏目及其中的有序 Markdown 条目 |
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
|-- HomePage/                  # Django 配置和根路由
|-- myHomePage/                # 模型、视图、后台、服务、任务和迁移
|-- templates/                 # 主页、详情、错误和后台模板
|-- static/                    # CSS、JavaScript、图标和字体
|-- locale/                    # 英文和简体中文翻译目录
|-- media/                     # 用户上传文件
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

- 英文主页：<http://127.0.0.1:8000/en/>
- 中文主页：<http://127.0.0.1:8000/zh-hans/>
- 管理后台：<http://127.0.0.1:8000/en/admin/>

常用命令：

```powershell
docker compose ps
docker compose logs -f web worker beat
docker compose down
```

持久化数据位置：

- SQLite：`docker-data/db.sqlite3`
- 上传文件：`media/`
- RabbitMQ：Docker 数据卷 `homepage_rabbitmq-data`

#### 宿主机挂载与数据持久化

Compose 会把宿主机的 `./docker-data` 目录绑定挂载到所有 Django/Celery 容器中的 `/data`。Django 实际使用 `/data/db.sqlite3`，因此容器内产生的数据库修改会直接写入宿主机的 `docker-data/db.sqlite3`。项目根目录下原有的 `db.sqlite3` **不会**被容器挂载或使用。

宿主机的 `./media` 会绑定挂载到容器的 `/app/media`，因此上传文件同样保留并共享在宿主机。RabbitMQ 不使用目录绑定，而是使用 Docker 管理的 `homepage_rabbitmq-data` 命名卷。

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
5. 通过“媒体文件”上传可复用资源，并把生成的链接用于 Markdown。
6. 仅在需要时配置 ORCID、Google Scholar 或 AI Provider。

多数内容记录支持 `is_active`、`is_draft` 和 `order`。草稿和未激活记录不会显示在公开主页。对于采用倒序排序的模型，较大的正数 `order` 会优先显示。

### 系统配置

| 配置类型 | 说明 |
| --- | --- |
| `enable_chinese` | 开启中文路由、字段、控件和内容 |
| `cards_per_page` | 每个栏目单页最多显示的卡片数量 |
| `sync_interval` | 自动同步间隔，单位为小时，默认 `24` |
| `scholar_proxy` | 可选 Google Scholar 代理；为空时尝试直连 |
| `orcid_client_id` / `orcid_client_secret` / `orcid_access_token` | ORCID 接入凭据 |
| `highlighted_authors` | 全局高亮作者，使用分号分隔 |
| `footer_items` | 使用 JSON 配置页脚文字和可选链接 |
| `resource_log_retention_hours` | 资源监控历史保留时间，默认 `168` 小时 |

页脚 JSON 可以包含单个条目或条目列表：

```json
{
  "item": [
    {"content": "研究团队"},
    {"content": "学校主页", "href": "https://example.com"}
  ]
}
```

页脚配置和 AI 配置的 JSON 均会进行前端和后端格式校验。

### 出版物同步

```bash
python manage.py sync_publications
```

需要先在对应 Profile 中启用 `auto_sync_orcid` 和/或 `auto_sync_google_scholar`。定时任务会高频检查，但只有达到系统配置的同步间隔后才会真正同步。

```bash
python manage.py check_orcid_config
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
| `CELERY_BROKER_URL` | 本地 AMQP guest 地址 | Celery Broker 连接地址 |
| `ENABLE_RESOURCE_MONITOR` | `True` | 是否启动后台资源采样线程 |
| `ENABLE_IP_GEO_LANGUAGE` | `False` | 是否根据 IP 自动选择语言 |
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

上线前至少需要：

1. 设置 `DEBUG=False`，并提供新的高强度 `SECRET_KEY`。
2. 正确配置 `ALLOWED_HOSTS`、HTTPS、安全 Cookie 和 HSTS。
3. 增加生产静态文件收集和服务配置；当前设置未定义 `STATIC_ROOT`。
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

### 开源协议

本项目使用 [GNU General Public License v3.0](LICENSE)。
