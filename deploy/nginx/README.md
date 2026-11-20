# Nginx Deployment Guide / Nginx 部署指南

[English](#english) | [简体中文](#简体中文)

---

<a id="english"></a>

## English

### Overview

This directory contains a production Nginx setup for MyHomePage running behind HTTPS.

| File | Purpose |
| --- | --- |
| `example.com.http.conf` | Temporary HTTP-only site, used only until the TLS certificate is issued |
| `example.com.conf` | Final HTTPS site |

The examples assume:

- Domain names `example.com` and `www.example.com`, with `example.com` as the canonical host.
- Project directory `/home/homepage/MyHomePage`.
- Docker Compose publishes Django only on the host at `127.0.0.1:5000` (`WEB_PORT=5000`).
- Nginx runs directly on a Linux host (Ubuntu paths below).
- One Let's Encrypt certificate covers both domain names.

Replace the domain before installing the files:

```bash
sed 's/example\.com/your-domain.com/g' deploy/nginx/example.com.http.conf > /tmp/site.http.conf
sed 's/example\.com/your-domain.com/g' deploy/nginx/example.com.conf > /tmp/site.conf
```

If the project lives elsewhere, also update the `/home/homepage/MyHomePage` paths in both files.

### 0. Prerequisites

- **DNS**: `example.com` and `www.example.com` both resolve to the server.
- **Cloud firewall**: allow inbound TCP `80` and `443`. On Alibaba Cloud, Tencent Cloud and similar providers this is the instance *security group*, which is separate from `ufw`. If SSH works but `curl http://example.com` times out, the security group is the usual cause.
- **ICP filing (mainland-China servers)**: domains served from mainland-China regions need an ICP filing. Without it the provider intercepts HTTP/HTTPS traffic and returns its own `403` page (Alibaba Cloud: `Server: Beaver`, title `Non-compliance ICP Filing`). Nginx cannot fix this, and certificate renewal fails as well. Complete the filing or use a Hong Kong / overseas region.

### 1. Production environment

Create or update `.env` in the project directory:

```dotenv
DEBUG=False
SECRET_KEY=replace-with-a-long-random-secret
ALLOWED_HOSTS=example.com,www.example.com,127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com
WEB_PORT=5000
TRUST_X_FORWARDED_FOR=True
```

Generate a secret key:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

- Keep `127.0.0.1,localhost` in `ALLOWED_HOSTS`. The container health check requests `http://127.0.0.1:8000/en/` inside the container; without these hosts Django returns `400` and the `web` container stays `unhealthy`.
- `WEB_PORT` is the host port. It must match the `upstream` / `proxy_pass` port in both Nginx files.
- `TRUST_X_FORWARDED_FOR=True` makes Django read the client address from Nginx's `X-Real-IP` header. Without it every request appears to come from the Docker gateway: the audit log shows one IP for everybody, and the login lockout (5 failures) locks out all users at once. Enable it only when Nginx is in front of Django.

Build and start the stack. The `init` service runs migrations and `collectstatic` (output: `./staticfiles` on the host):

```bash
sh ./docker-up.sh
```

Changes to `.env` take effect only after the containers are recreated with `docker compose up -d`.

With `DEBUG=False`, Django forces HTTPS (`SECURE_SSL_REDIRECT`). Until Nginx serves HTTPS, every page redirects to `https://` and fails; this is expected during steps 2–4.

### 2. File permissions

The Nginx worker (`www-data`) must be able to traverse the home directory to read `staticfiles` and `media`. Ubuntu creates home directories as `750`, which blocks it. Grant traverse-only permission (directory listing remains denied):

```bash
chmod 711 /home/homepage
namei -l /home/homepage/MyHomePage/staticfiles   # every level needs "x" for others
```

### 3. Temporary HTTP site

The final configuration references certificate files that do not exist yet, so `nginx -t` would fail. Start with the HTTP-only site, which also serves the ACME challenge directory:

```bash
sudo mkdir -p /var/www/letsencrypt
sudo cp /tmp/site.http.conf /etc/nginx/sites-available/example.com
sudo ln -sf /etc/nginx/sites-available/example.com /etc/nginx/sites-enabled/example.com
sudo nginx -t && sudo systemctl enable --now nginx
sudo systemctl reload nginx
```

Verify from another machine. A `404` for this path means the request reached Nginx; a timeout points back to step 0:

```bash
curl -I http://example.com/.well-known/acme-challenge/test
```

### 4. TLS certificate

Use the webroot method so Nginx keeps running during issuance and renewal:

```bash
sudo certbot certonly --webroot -w /var/www/letsencrypt \
  -d example.com -d www.example.com \
  --email you@example.com --agree-tos --no-eff-email
```

The webroot method does not reload Nginx after a renewal. Add a deploy hook and test renewal:

```bash
printf '#!/bin/sh\nsystemctl reload nginx\n' | sudo tee /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
sudo certbot renew --dry-run
```

The final configuration expects these files; if certbot uses a different directory name, update the paths in `example.com.conf`:

```text
/etc/letsencrypt/live/example.com/fullchain.pem
/etc/letsencrypt/live/example.com/privkey.pem
```

### 5. Final HTTPS site

Replace the temporary site with the final configuration, keeping a backup:

```bash
sudo cp /etc/nginx/sites-available/example.com /etc/nginx/sites-available/example.com.bak
sudo cp /tmp/site.conf /etc/nginx/sites-available/example.com
sudo nginx -t && sudo systemctl reload nginx
```

If `nginx -t` fails, restore the `.bak` file; the running Nginx is unaffected until a successful reload. On distributions that use `/etc/nginx/conf.d`, copy the file there as `example.com.conf` instead.

Verify:

```bash
curl -I https://example.com/en/                        # 200
curl -I https://www.example.com/                       # 301 -> https://example.com/
curl -I http://example.com/                            # 301 -> https://example.com/
curl -I https://example.com/static/css/all.min.css     # 200
docker compose ps                                      # web becomes healthy
```

### Routing behaviour

| Path | Handled by | Notes |
| --- | --- | --- |
| `http://…`, `https://www.example.com` | Nginx | `301` to canonical `https://example.com` |
| `/.well-known/acme-challenge/` | Nginx | Served from `/var/www/letsencrypt` for certificate issuance/renewal |
| `/static/` | Nginx | Served from `staticfiles/`, cached for 7 days |
| `/media/` (images) | Nginx | Public profile/news/research/publication images from `media/`, cached for 7 days |
| `/media/markdown_assets/`, `/media-file/`, `/publication-file/` | Django | Access checks (inactive files, access keys) must not be bypassed |
| `/media/publication_files/` | Nginx | Always `404`; publication files are only reachable through `/publication-file/<access-key>/` |
| Everything else | Django (`127.0.0.1:5000`) | Proxy timeouts of 300 s |

### Limits and caching

- **Upload size**: `client_max_body_size 100m` applies to all uploads, including **System Backup → Import external backup**. Raise it in both files if your backup archives are larger, then reload Nginx.
- **Timeouts**: `proxy_read_timeout` / `proxy_send_timeout` are `300s` so long operations (creating or restoring a backup, publication sync, AI generation) are not cut off. Increase them for very large sites.
- **Static caching**: `/static/` and public `/media/` are cached by browsers for 7 days. The application versions its own CSS/JS URLs (`?v=…`, including admin assets), so deployments are picked up without users clearing their cache.

### Updating the application

```bash
cd ~/MyHomePage
git pull
docker compose up -d --build                   # also re-runs migrations and collectstatic
sudo nginx -t && sudo systemctl reload nginx   # only needed when Nginx files changed
```

`media/` is not tracked by Git (only `media/.gitkeep` is), so uploaded files stay in place across updates. If an update removes a file that used to be tracked, `git pull` deletes it from the working tree; back up `media/` before pulling such a change.

### Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| SSH works, `curl http://example.com` times out | Cloud security group blocks 80/443 | Allow inbound TCP 80 and 443 |
| `403`, `Server: Beaver`, "Non-compliance ICP Filing" | Domain lacks an ICP filing on a mainland-China server | Complete the filing or move to another region |
| Site unreachable, `systemctl status nginx` shows `inactive` | Nginx not started | `sudo nginx -t && sudo systemctl enable --now nginx` |
| Only the Nginx welcome page | Site not linked into `sites-enabled` | Create the symlink from step 3 |
| `nginx -t`: cannot load certificate | Final config installed before the certificate exists | Use `example.com.http.conf` first |
| Every page redirects to `https://` and fails | `DEBUG=False` forces HTTPS, no HTTPS site yet | Finish steps 4–5 |
| Pages load without CSS/images (403/404) | `www-data` cannot traverse `/home/homepage` | `chmod 711 /home/homepage` |
| `400 Bad Request` | Host missing from `ALLOWED_HOSTS` | Update `.env`, then `docker compose up -d` |
| `web` container `unhealthy` | `127.0.0.1` missing from `ALLOWED_HOSTS` | Add `127.0.0.1,localhost`, then `docker compose up -d` |
| `403 CSRF verification failed` on login/forms | Origin missing from `CSRF_TRUSTED_ORIGINS` | Add the `https://` origins, then `docker compose up -d` |
| `413 Request Entity Too Large` (e.g. importing a backup) | Upload exceeds `client_max_body_size` | Raise the limit and reload Nginx |
| `504 Gateway Timeout` on a long operation | Operation exceeded the proxy timeout | Raise `proxy_read_timeout` and reload Nginx |
| `502 Bad Gateway` | Django not listening on `127.0.0.1:5000` | Check `docker compose ps`, `docker compose logs web`, and `WEB_PORT` |

Nginx logs are readable only by root or the `adm` group: `sudo tail -50 /var/log/nginx/error.log`.

---

<a id="简体中文"></a>

## 简体中文

### 概述

本目录提供 MyHomePage 在 HTTPS 下运行的生产环境 Nginx 配置。

| 文件 | 用途 |
| --- | --- |
| `example.com.http.conf` | 临时的纯 HTTP 站点，仅在申请 TLS 证书之前使用 |
| `example.com.conf` | 正式的 HTTPS 站点 |

示例配置的前提：

- 域名为 `example.com` 和 `www.example.com`，以 `example.com` 为主域名。
- 项目目录为 `/home/homepage/MyHomePage`。
- Docker Compose 只把 Django 发布在宿主机的 `127.0.0.1:5000`（`WEB_PORT=5000`）。
- Nginx 直接运行在 Linux 宿主机上（下文使用 Ubuntu 路径）。
- 一张 Let's Encrypt 证书同时包含两个域名。

安装前先替换域名：

```bash
sed 's/example\.com/your-domain.com/g' deploy/nginx/example.com.http.conf > /tmp/site.http.conf
sed 's/example\.com/your-domain.com/g' deploy/nginx/example.com.conf > /tmp/site.conf
```

如果项目不在上述目录，还需要同步修改两个文件中的 `/home/homepage/MyHomePage` 路径。

### 0. 前置条件

- **DNS**：`example.com` 和 `www.example.com` 都解析到当前服务器。
- **云防火墙**：入方向放行 TCP `80` 和 `443`。阿里云、腾讯云等需要在实例的**安全组**中配置，与系统内的 `ufw` 无关。如果 SSH 能连接但 `curl http://example.com` 超时，通常就是安全组没有放行。
- **ICP 备案（中国内地服务器）**：内地地域的服务器用域名对外提供服务必须完成备案。未备案时云厂商会拦截 HTTP/HTTPS 请求并返回自己的 `403` 页面（阿里云为 `Server: Beaver`，标题 `Non-compliance ICP Filing`）。这无法通过 Nginx 解决，证书也无法续期；需要完成备案，或改用香港/海外地域。

### 1. 生产环境变量

在项目目录中创建或修改 `.env`：

```dotenv
DEBUG=False
SECRET_KEY=replace-with-a-long-random-secret
ALLOWED_HOSTS=example.com,www.example.com,127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com
WEB_PORT=5000
TRUST_X_FORWARDED_FOR=True
```

生成密钥：

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

- `ALLOWED_HOSTS` 中必须保留 `127.0.0.1,localhost`。容器健康检查在容器内访问 `http://127.0.0.1:8000/en/`，缺少这两项时 Django 返回 `400`，`web` 容器会一直显示 `unhealthy`。
- `WEB_PORT` 是宿主机端口，必须与两个 Nginx 文件中 `upstream` / `proxy_pass` 的端口一致。
- `TRUST_X_FORWARDED_FOR=True` 让 Django 从 Nginx 设置的 `X-Real-IP` 头读取真实客户端 IP。不开启时所有请求都显示为 Docker 网关地址：审计日志里所有人的 IP 都一样，而且登录失败锁定（5 次）会把所有用户一起锁住。只在前面有 Nginx 时开启。

构建并启动。`init` 服务会自动执行数据库迁移和 `collectstatic`（输出到宿主机的 `./staticfiles`）：

```bash
sh ./docker-up.sh
```

修改 `.env` 后，需要执行 `docker compose up -d` 重建容器才会生效。

`DEBUG=False` 时 Django 会强制跳转 HTTPS（`SECURE_SSL_REDIRECT`）。在 Nginx 启用 HTTPS 之前，所有页面都会跳转到 `https://` 并打不开，这在第 2–4 步期间属于正常现象。

### 2. 文件权限

Nginx 的运行用户 `www-data` 需要能进入家目录，才能读取 `staticfiles` 和 `media`。Ubuntu 默认的家目录权限是 `750`，会导致静态文件 403/404。授予“仅可进入”权限即可（仍不能列出目录内容）：

```bash
chmod 711 /home/homepage
namei -l /home/homepage/MyHomePage/staticfiles   # 每一级目录的 others 都需要有 x 权限
```

### 3. 临时 HTTP 站点

正式配置引用的证书文件此时还不存在，直接安装会导致 `nginx -t` 失败。因此先启用纯 HTTP 的临时配置，它同时提供证书验证目录：

```bash
sudo mkdir -p /var/www/letsencrypt
sudo cp /tmp/site.http.conf /etc/nginx/sites-available/example.com
sudo ln -sf /etc/nginx/sites-available/example.com /etc/nginx/sites-enabled/example.com
sudo nginx -t && sudo systemctl enable --now nginx
sudo systemctl reload nginx
```

在另一台机器上验证。返回 `404` 说明请求已经到达 Nginx；如果超时，请回到第 0 步检查：

```bash
curl -I http://example.com/.well-known/acme-challenge/test
```

### 4. TLS 证书

使用 webroot 方式申请，申请和续期期间 Nginx 无需停止：

```bash
sudo certbot certonly --webroot -w /var/www/letsencrypt \
  -d example.com -d www.example.com \
  --email you@example.com --agree-tos --no-eff-email
```

webroot 方式续期后不会自动重载 Nginx。添加 deploy hook 并测试续期：

```bash
printf '#!/bin/sh\nsystemctl reload nginx\n' | sudo tee /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
sudo certbot renew --dry-run
```

正式配置使用以下证书文件；如果 certbot 生成的目录名不同，请同步修改 `example.com.conf` 中的路径：

```text
/etc/letsencrypt/live/example.com/fullchain.pem
/etc/letsencrypt/live/example.com/privkey.pem
```

### 5. 正式 HTTPS 站点

先备份临时配置，再替换为正式配置：

```bash
sudo cp /etc/nginx/sites-available/example.com /etc/nginx/sites-available/example.com.bak
sudo cp /tmp/site.conf /etc/nginx/sites-available/example.com
sudo nginx -t && sudo systemctl reload nginx
```

如果 `nginx -t` 失败，恢复 `.bak` 文件即可；在检查通过并成功 reload 之前，正在运行的 Nginx 不受影响。对于使用 `/etc/nginx/conf.d` 的发行版，改为复制到该目录并命名为 `example.com.conf`。

验证：

```bash
curl -I https://example.com/en/                        # 200
curl -I https://www.example.com/                       # 301 -> https://example.com/
curl -I http://example.com/                            # 301 -> https://example.com/
curl -I https://example.com/static/css/all.min.css     # 200
docker compose ps                                      # web 变为 healthy
```

### 路由行为

| 路径 | 处理方 | 说明 |
| --- | --- | --- |
| `http://…`、`https://www.example.com` | Nginx | `301` 跳转到主域名 `https://example.com` |
| `/.well-known/acme-challenge/` | Nginx | 由 `/var/www/letsencrypt` 提供，用于证书申请和续期 |
| `/static/` | Nginx | 直接读取 `staticfiles/`，缓存 7 天 |
| `/media/`（图片） | Nginx | 个人资料、新闻、研究、论文的公开图片，直接读取 `media/`，缓存 7 天 |
| `/media/markdown_assets/`、`/media-file/`、`/publication-file/` | Django | 需要经过系统的权限检查（未启用文件、访问键），不能被绕过 |
| `/media/publication_files/` | Nginx | 始终返回 `404`；论文附件只能通过 `/publication-file/<访问键>/` 访问 |
| 其他所有请求 | Django（`127.0.0.1:5000`） | 代理超时 300 秒 |

### 上传限制与缓存

- **上传大小**：`client_max_body_size 100m` 对所有上传生效，包括 **系统备份 → 导入外部备份**。如果备份文件更大，请在两个文件中同时调大该值并重载 Nginx。
- **超时**：`proxy_read_timeout` / `proxy_send_timeout` 为 `300s`，保证新建或恢复备份、出版物同步、AI 生成等长时间操作不会被中断。站点数据很大时可以继续调大。
- **静态缓存**：`/static/` 和公开的 `/media/` 在浏览器中缓存 7 天。系统自身的 CSS/JS 地址（包括后台资源）都带有版本参数 `?v=…`，更新部署后用户无需手动清除缓存。

### 更新应用

```bash
cd ~/MyHomePage
git pull
docker compose up -d --build                   # 同时会重新执行数据库迁移和 collectstatic
sudo nginx -t && sudo systemctl reload nginx   # 仅在 Nginx 配置有变化时需要
```

`media/` 不纳入 Git 管理（只跟踪 `media/.gitkeep`），因此上传的文件在更新时保持不变。如果某次更新删除了以前被跟踪的文件，`git pull` 会把它从工作区删除；拉取这类更新前请先备份 `media/`。

### 常见问题

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| SSH 能连接，`curl http://example.com` 超时 | 云安全组未放行 80/443 | 入方向放行 TCP 80、443 |
| `403`、`Server: Beaver`、"Non-compliance ICP Filing" | 内地服务器上的域名未备案 | 完成备案或更换地域 |
| 网站无法访问，`systemctl status nginx` 显示 `inactive` | Nginx 未启动 | `sudo nginx -t && sudo systemctl enable --now nginx` |
| 只显示 Nginx 欢迎页 | 站点未链接到 `sites-enabled` | 按第 3 步创建软链接 |
| `nginx -t` 提示无法加载证书 | 证书申请前就安装了正式配置 | 先使用 `example.com.http.conf` |
| 所有页面都跳转到 `https://` 且打不开 | `DEBUG=False` 强制 HTTPS，但还没有 HTTPS 站点 | 完成第 4、5 步 |
| 页面没有样式/图片（403/404） | `www-data` 无法进入 `/home/homepage` | `chmod 711 /home/homepage` |
| `400 Bad Request` | 主机名不在 `ALLOWED_HOSTS` 中 | 修改 `.env` 后执行 `docker compose up -d` |
| `web` 容器 `unhealthy` | `ALLOWED_HOSTS` 缺少 `127.0.0.1` | 加入 `127.0.0.1,localhost` 后执行 `docker compose up -d` |
| 登录或提交表单时 `403 CSRF verification failed` | `CSRF_TRUSTED_ORIGINS` 缺少该来源 | 加入 `https://` 来源后执行 `docker compose up -d` |
| `413 Request Entity Too Large`（如导入备份时） | 上传超过 `client_max_body_size` | 调大限制并重载 Nginx |
| 长时间操作出现 `504 Gateway Timeout` | 操作超过代理超时 | 调大 `proxy_read_timeout` 并重载 Nginx |
| `502 Bad Gateway` | Django 未在 `127.0.0.1:5000` 监听 | 检查 `docker compose ps`、`docker compose logs web` 和 `WEB_PORT` |

Nginx 日志仅 root 或 `adm` 组可读：`sudo tail -50 /var/log/nginx/error.log`。
