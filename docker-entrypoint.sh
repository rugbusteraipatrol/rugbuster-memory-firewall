#!/bin/sh
set -eu

mkdir -p /data /app/runtime
chown -R rugbuster:rugbuster /data /app/runtime

exec gosu rugbuster "$@"
