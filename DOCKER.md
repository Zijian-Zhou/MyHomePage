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
mode cannot print container logs automatically. Retrieve first-start credentials
with `Get-Content docker-data\superadmin-credentials.txt` on Windows,
`cat docker-data/superadmin-credentials.txt` on Linux/macOS, or
`docker compose logs init` on any platform. Delete the file after reading it.

如果直接使用 `docker compose up -d --build`，后台模式不会自动显示容器日志。
Windows 使用 `Get-Content docker-data\superadmin-credentials.txt`，Linux/macOS
使用 `cat docker-data/superadmin-credentials.txt`，也可以在任意平台使用
`docker compose logs init`。读取后请删除明文凭据文件。

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
