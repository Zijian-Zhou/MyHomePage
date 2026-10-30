# Docker Compose

## Start / 启动

Windows PowerShell:

```powershell
Copy-Item .env.example .env
.\docker-up.ps1
```

Linux/macOS:

```bash
cp .env.example .env
sh ./docker-up.sh
```

Open <http://127.0.0.1:8000/en/>. Database migrations run automatically before
the web and Celery services start. On the first start, the script creates the
`superadmin` account and prints its generated password. The password format is
`MyPageAdmin@YYYYMMDDHHMM`. Existing accounts are never reset on later starts.

If Compose is started directly with `docker compose up -d --build`, detached
mode cannot print container logs automatically. The credential file has mode
`0600` and belongs to the container's `django` user. Read and remove it through
the Web container, or inspect the initialization logs:

```bash
docker compose exec -T web cat /data/superadmin-credentials.txt
docker compose exec -T web rm -f /data/superadmin-credentials.txt
docker compose logs init
```

如果直接使用 `docker compose up -d --build`，后台模式不会自动显示容器日志。
凭据文件权限为 `0600` 且属于容器内的 `django` 用户，因此需要通过上面的
`docker compose exec` 命令读取和删除，或者使用 `docker compose logs init`。

On Linux/macOS, the initialization container temporarily starts as root to fix
ownership of the bind-mounted `/data` and `/app/media` directories, then drops
to the non-root `django` user before migrations run. If startup fails, the helper
scripts print initialization logs automatically. For direct Compose startup, run:

```bash
docker compose logs init
```

## Status and logs

```powershell
docker compose ps
docker compose logs -f web worker beat
```

## Stop / 关闭

```powershell
docker compose down
```

The SQLite database is stored in `docker-data/db.sqlite3`, uploaded media stays
in `media`, and RabbitMQ data uses the `rabbitmq-data` Docker volume. To stop and
also remove RabbitMQ data, run `docker compose down -v`. The SQLite database and
media files are not removed by that command.

To initialize Docker with an existing local database, stop the services and copy
`db.sqlite3` to `docker-data/db.sqlite3` before starting Compose.
