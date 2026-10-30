# Nginx deployment / Nginx 部署

The example configuration assumes:

- Domain names: `example.com` and `www.example.com`
- Project directory: `/home/homepage/MyHomePage`
- Docker publishes Django only on `127.0.0.1:8000`
- Nginx runs directly on the Linux host (Ubuntu paths are used below)
- A Let's Encrypt certificate covers both domain names

示例配置假设域名为 `example.com` 和 `www.example.com`，项目位于
`/home/homepage/MyHomePage`，Nginx 直接运行在 Linux 宿主机上（下文使用 Ubuntu
路径），Django 仅监听宿主机的 `127.0.0.1:8000`，且 Let's Encrypt 证书同时包含
两个域名。

Files / 文件：

| File | Purpose |
| --- | --- |
| `example.com.http.conf` | Temporary HTTP-only site used to obtain the certificate / 申请证书前使用的临时 HTTP 配置 |
| `example.com.conf` | Final HTTPS site / 正式 HTTPS 配置 |

Replace the domain in both files before installing them:

```bash
sed 's/example\.com/your-domain.com/g' deploy/nginx/example.com.http.conf > /tmp/site.http.conf
sed 's/example\.com/your-domain.com/g' deploy/nginx/example.com.conf > /tmp/site.conf
```

安装前先用上面的命令把两个文件中的 `example.com` 替换为实际域名。

## 0. Prerequisites / 前置条件

- **DNS**: both `example.com` and `www.example.com` resolve to the server.
- **Cloud firewall**: inbound TCP `80` and `443` are allowed. On Alibaba Cloud,
  Tencent Cloud, etc., this is the instance *security group*, which is separate
  from `ufw`. If `ssh` works but `curl http://example.com` times out, the
  security group is the usual cause.
- **ICP filing (mainland China servers)**: domains served from mainland-China
  regions must have an ICP filing. Without it the provider intercepts HTTP/HTTPS
  requests and returns its own `403` page (for Alibaba Cloud: `Server: Beaver`,
  title `Non-compliance ICP Filing`). This cannot be fixed in Nginx, and it also
  breaks certificate renewal. Either complete the filing or use a Hong Kong /
  overseas region.

- **DNS**：`example.com` 和 `www.example.com` 都解析到当前服务器。
- **云防火墙**：入方向放行 TCP `80` 和 `443`。阿里云、腾讯云等需要在实例的
  **安全组**中配置，与系统内的 `ufw` 无关。如果 SSH 可以连接但
  `curl http://example.com` 超时，通常就是安全组未放行。
- **ICP 备案（中国内地服务器）**：内地地域的服务器使用域名对外提供 80/443
  服务必须完成备案。未备案时云厂商会拦截请求并返回自己的 `403` 页面（阿里云为
  `Server: Beaver`，标题 `Non-compliance ICP Filing`）。该问题无法通过 Nginx
  配置解决，并且会导致证书无法续期；需要完成备案，或改用香港/海外地域服务器。

## 1. Production environment / 生产环境变量

Update `.env` before starting Compose:

```dotenv
DEBUG=False
SECRET_KEY=replace-with-a-long-random-secret
ALLOWED_HOSTS=example.com,www.example.com,127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com
WEB_PORT=8000
```

Keep `127.0.0.1,localhost` in `ALLOWED_HOSTS`: the container health check
requests `http://127.0.0.1:8000/en/`, and without them Django returns `400` and
the `web` container stays `unhealthy`.

`ALLOWED_HOSTS` 中需要保留 `127.0.0.1,localhost`：容器健康检查访问的是
`http://127.0.0.1:8000/en/`，缺少这两项时 Django 返回 `400`，`web` 容器会一直
显示 `unhealthy`。

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
`collectstatic`，静态文件输出到宿主机的 `./staticfiles`。修改 `.env` 后需要执行
`docker compose up -d` 重建容器才会生效。

With `DEBUG=False`, Django forces HTTPS (`SECURE_SSL_REDIRECT`). Until Nginx
serves HTTPS, every page redirects to `https://` and fails. This is expected
during steps 2–3.

`DEBUG=False` 时 Django 会强制跳转 HTTPS。在 Nginx 启用 HTTPS 之前，所有页面都会
跳转到 `https://` 并无法打开，这在第 2、3 步期间属于正常现象。

## 2. File permissions / 文件权限

The Nginx worker (`www-data`) must be able to traverse the home directory to
read `staticfiles` and `media`. Ubuntu creates home directories as `750`, which
blocks it. Grant traverse-only permission (directory listing remains denied):

```bash
chmod 711 /home/homepage
namei -l /home/homepage/MyHomePage/staticfiles   # every level needs x for others
```

Nginx 运行用户 `www-data` 需要能进入家目录才能读取 `staticfiles` 和 `media`。
Ubuntu 默认家目录权限为 `750`，会导致静态文件 403/404，需要授予仅进入权限
（仍不能列出目录内容）。

## 3. Temporary HTTP site / 临时 HTTP 站点

The final configuration references certificate files that do not exist yet, so
`nginx -t` would fail. Start with the HTTP-only site, which also serves the ACME
challenge directory:

```bash
sudo mkdir -p /var/www/letsencrypt
sudo cp /tmp/site.http.conf /etc/nginx/sites-available/example.com
sudo ln -sf /etc/nginx/sites-available/example.com /etc/nginx/sites-enabled/example.com
sudo nginx -t && sudo systemctl enable --now nginx
sudo systemctl reload nginx
```

Verify from another machine (a `404` for the challenge path means Nginx answered):

```bash
curl -I http://example.com/.well-known/acme-challenge/test
```

正式配置引用的证书文件此时还不存在，直接安装会导致 `nginx -t` 失败。因此先启用
临时 HTTP 配置，它同时提供证书验证目录。用其他机器访问验证路径返回 `404`，说明
请求已到达 Nginx；如果超时，请检查第 0 步的安全组。

## 4. TLS certificate / TLS 证书

Use the webroot method so Nginx keeps running during issuance and renewal:

```bash
sudo certbot certonly --webroot -w /var/www/letsencrypt \
  -d example.com -d www.example.com \
  --email you@example.com --agree-tos --no-eff-email
```

The webroot method does not reload Nginx after renewal. Add a deploy hook:

```bash
printf '#!/bin/sh\nsystemctl reload nginx\n' | sudo tee /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
sudo certbot renew --dry-run
```

The final configuration expects:

```text
/etc/letsencrypt/live/example.com/fullchain.pem
/etc/letsencrypt/live/example.com/privkey.pem
```

使用 webroot 方式申请证书，申请和续期期间 Nginx 无需停止。webroot 方式续期后
不会自动重载 Nginx，因此需要添加上面的 deploy hook。如果证书目录名称不同，请同步
修改 `example.com.conf` 中的证书路径。

## 5. Final HTTPS site / 正式 HTTPS 站点

Replace the temporary site with the final configuration, keeping a backup:

```bash
sudo cp /etc/nginx/sites-available/example.com /etc/nginx/sites-available/example.com.bak
sudo cp /tmp/site.conf /etc/nginx/sites-available/example.com
sudo nginx -t && sudo systemctl reload nginx
```

If `nginx -t` fails, restore the `.bak` file; the running Nginx is not affected
until a successful reload.

For distributions that use `/etc/nginx/conf.d`, copy the file there as
`example.com.conf` instead.

先备份临时配置再替换为正式配置。`nginx -t` 失败时恢复 `.bak` 即可，检查通过并
reload 之前不会影响正在运行的 Nginx。对于使用 `/etc/nginx/conf.d` 的发行版，
可直接复制到该目录并以 `.conf` 结尾。

Verify / 验证：

```bash
curl -I https://example.com/en/            # 200
curl -I https://www.example.com/           # 301 -> https://example.com/
curl -I http://example.com/                # 301 -> https://example.com/
curl -I https://example.com/static/css/all.min.css   # 200
docker compose ps                          # web should become healthy
```

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

## Troubleshooting / 常见问题

| Symptom / 现象 | Cause / 原因 | Fix / 处理 |
| --- | --- | --- |
| `ssh` works, `curl http://example.com` times out | Cloud security group blocks 80/443 / 安全组未放行 | Allow inbound TCP 80 and 443 / 入方向放行 80、443 |
| `403`, `Server: Beaver`, "Non-compliance ICP Filing" | Domain lacks ICP filing on a mainland-China server / 域名未备案 | Complete ICP filing or move region / 备案或更换地域 |
| Site unreachable, `systemctl status nginx` shows `inactive` | Nginx not started / Nginx 未启动 | `sudo nginx -t && sudo systemctl enable --now nginx` |
| Only the Nginx welcome page | Site not linked into `sites-enabled` / 站点未启用 | Create the symlink in step 3 / 按第 3 步创建软链接 |
| `nginx -t`: cannot load certificate | Final config installed before issuance / 证书未申请 | Use `example.com.http.conf` first / 先使用临时 HTTP 配置 |
| Every page redirects to `https://` and fails | `DEBUG=False` forces HTTPS, but no HTTPS site yet / 尚未启用 HTTPS | Finish steps 4–5 / 完成第 4、5 步 |
| Pages load without CSS/images (403/404) | `www-data` cannot traverse `/home/homepage` / 家目录权限 | `chmod 711 /home/homepage` |
| `400 Bad Request` | Host missing from `ALLOWED_HOSTS` / 主机名未加入 | Update `.env`, then `docker compose up -d` |
| `web` container `unhealthy` | `127.0.0.1` missing from `ALLOWED_HOSTS` / 缺少 `127.0.0.1` | Add `127.0.0.1,localhost`, then `docker compose up -d` |
| `403 CSRF verification failed` on login/forms | Origin missing from `CSRF_TRUSTED_ORIGINS` / 未配置可信来源 | Add `https://` origins, then `docker compose up -d` |
| `502 Bad Gateway` | Django container not running on `127.0.0.1:8000` / 后端未运行 | `docker compose ps`, `docker compose logs web` |

Nginx logs are readable only by root/`adm`: `sudo tail -50 /var/log/nginx/error.log`.

Nginx 日志仅 root 或 `adm` 组可读：`sudo tail -50 /var/log/nginx/error.log`。
