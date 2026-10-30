#!/bin/sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CONTAINER_CREDENTIAL_FILE="/data/superadmin-credentials.txt"

cd "$SCRIPT_DIR"
if ! docker compose up -d --build; then
    printf '\n%s\n' 'Docker Compose failed. Initialization logs:' >&2
    docker compose logs --no-color init >&2 || true
    exit 1
fi

printf '\n'
if docker compose exec -T web test -f "$CONTAINER_CREDENTIAL_FILE"; then
    printf '%s\n' 'Default administrator credentials:'
    docker compose exec -T web cat "$CONTAINER_CREDENTIAL_FILE"
    docker compose exec -T web rm -f "$CONTAINER_CREDENTIAL_FILE"
    printf '%s\n' 'The one-time credential file has been removed.'
else
    printf '%s\n' 'Default superadmin already exists; its password was not changed.'
fi

PORT=$(docker compose port web 8000 2>/dev/null | head -n 1 | awk -F: '{print $NF}')
PORT=${PORT:-8000}
printf '\nHomepage: http://127.0.0.1:%s/en/\n' "$PORT"
printf 'Administration: http://127.0.0.1:%s/en/admin/\n' "$PORT"
