#!/bin/sh
set -eu

# Bind mounts hide ownership prepared in the image. Align only the three
# writable runtime directories, then drop privileges for the application.
run_app=0
if [ "${1:-}" = "python" ] && [ "${2:-}" = "-m" ] && [ "${3:-}" = "main" ]; then
    run_app=1
fi

if [ "$(id -u)" = "0" ]; then
    for path in /app/data /app/logs /app/sessions; do
        mkdir -p "$path"
        chown -R sirius:sirius "$path"
    done
    if [ "$run_app" = "1" ]; then
        echo "[sirius] applying database migrations"
        gosu sirius alembic upgrade head
    fi
    exec gosu sirius "$@"
fi

if [ "$run_app" = "1" ]; then
    echo "[sirius] applying database migrations"
    alembic upgrade head
fi
exec "$@"
