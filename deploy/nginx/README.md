# Nginx deployment / Nginx 部署

The example configuration assumes:

- Domain names: `example.com` and `www.example.com`
- Project directory: `/home/homepage/MyHomePage`
- Docker publishes Django only on `127.0.0.1:8000`
- Nginx runs directly on the Linux host
- A Let's Encrypt certificate covers both domain names

示例配置假设域名为 `example.com` 和 `www.example.com`，项目位于
`/home/homepage/MyHomePage`，Nginx 直接运行在 Linux 宿主机上，Django 仅监听
宿主机的 `127.0.0.1:8000`，且 Let's Encrypt 证书同时包含两个域名。

## 1. Production environment / 生产环境变量

Update `.env` before starting Compose:

```dotenv
DEBUG=False
SECRET_KEY=replace-with-a-long-random-secret
ALLOWED_HOSTS=example.com,www.example.com
CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com
WEB_PORT=8000
```

Generate a secret key:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

Then rebuild and start the services. The initialization service automatically
runs migrations and `collectstatic`:

```bash
sh ./docker-up.sh
```

修改 `.env` 后重新构建启动。初始化服务会自动执行数据库迁移和
`collectstatic`，静态文件输出到宿主机的 `./staticfiles`。

## 2. TLS certificate / TLS 证书

Install Nginx and Certbot using the package manager for your Linux distribution.
Before enabling the HTTPS configuration, obtain a certificate containing both
names. For an initial deployment with no active site, one example is:

```bash
sudo systemctl stop nginx
sudo certbot certonly --standalone -d example.com -d www.example.com
sudo systemctl start nginx
```

The full Nginx configuration expects:

```text
/etc/letsencrypt/live/example.com/fullchain.pem
/etc/letsencrypt/live/example.com/privkey.pem
```

启用 HTTPS 配置前需要先申请同时包含两个域名的证书。申请前应确认两个域名均已
解析到当前服务器，且公网可以访问 80 端口。如果证书目录名称不同，请同步修改
`example.com.conf` 中的证书路径。

## 3. Install the site configuration / 安装站点配置

Review the project path in `example.com.conf`, then install it:

```bash
sudo cp deploy/nginx/example.com.conf /etc/nginx/sites-available/example.com.conf
sudo ln -s /etc/nginx/sites-available/example.com.conf /etc/nginx/sites-enabled/example.com.conf
sudo nginx -t
sudo systemctl reload nginx
```

For distributions that use `/etc/nginx/conf.d`, copy the file there instead.
Ensure the Nginx worker user can traverse `/home/homepage/MyHomePage` and read
the `staticfiles` and `media` directories.

对于使用 `/etc/nginx/conf.d` 的发行版，可直接复制到该目录。必须确保 Nginx
运行用户可以进入项目路径，并读取 `staticfiles` 和 `media` 目录。

## Routing behavior / 路由行为

- `http://example.com` and `http://www.example.com` redirect to HTTPS.
- `https://www.example.com` redirects to canonical `https://example.com`.
- `/static/` is served directly from `staticfiles/` by Nginx.
- Ordinary `/media/` images are served directly from `media/` by Nginx.
- `/media/markdown_assets/`, `/media-file/`, and `/publication-file/` are sent to
  Django so application permissions are not bypassed.
- Direct `/media/publication_files/` access is denied; publication files must use
  their opaque `/publication-file/<access-key>/` route.
- All other requests are proxied to Django at `127.0.0.1:8000`.

- HTTP 和 `www` 域名会跳转到主域名 HTTPS。
- `/static/` 和普通 `/media/` 资源由 Nginx 直接提供。
- 需要权限认证的 Markdown 媒体、媒体访问键和论文附件继续转发给 Django，
  不会绕过系统权限检查。
- 禁止直接访问 `/media/publication_files/`，论文文件必须使用带访问键的路由。
- 其他请求反向代理到 `127.0.0.1:8000`。

After changing static files, rebuild/restart the initialization service or run:

```bash
docker compose run --rm init python manage.py collectstatic --noinput
sudo nginx -t && sudo systemctl reload nginx
```

修改静态文件后，需要重新执行 `collectstatic`，再检查并重载 Nginx。
