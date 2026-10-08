#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
unset BASH_ENV ENV CDPATH GIT_DIR GIT_WORK_TREE GIT_CONFIG_GLOBAL GIT_CONFIG_SYSTEM GIT_CONFIG_COUNT DOCKER_HOST DOCKER_CONTEXT COMPOSE_FILE COMPOSE_PROJECT_NAME CCWBOT_BACKUP_DIR CCWBOT_BACKUP_RETENTION_COUNT
ROOT=/opt/CCWBot
STATE=/var/lib/ccwbot-deploy
LOCK=/run/lock/ccwbot-deploy-safe.lock
GIT=/usr/bin/git
DOCKER=/usr/bin/docker
ORIGIN=https://github.com/akrasnoslov-dev/CCWBot.git

fail() { echo "ccwbot-deploy-safe: $*" >&2; exit 2; }
[ "$(/usr/bin/id -u)" = 0 ] || fail "root execution required"
[ "$#" = 1 ] || fail "exactly one action is required"
case "$1" in status|backup|deploy|rollback) action=$1 ;; *) fail "unsupported action" ;; esac
[ -d "$ROOT/.git" ] || fail "repository missing"
[ "$(/usr/bin/stat -c %u "$ROOT")" = 0 ] || fail "repository must be root-owned"
[ "$(/usr/bin/stat -c %u "$ROOT/.git")" = 0 ] || fail "git directory must be root-owned"
cd "$ROOT"
[ "$("$GIT" remote get-url origin)" = "$ORIGIN" ] || fail "unexpected repository origin"

status() {
  echo "branch=$("$GIT" branch --show-current)"
  echo "head=$("$GIT" rev-parse HEAD)"
  "$DOCKER" compose ps
  if /usr/bin/curl --fail --silent --show-error --max-time 5 --output /dev/null http://127.0.0.1:8080/health; then
    echo health=ok
  else
    echo health=failed
    return 1
  fi
}
clean_main() {
  [ "$("$GIT" branch --show-current)" = main ] || fail "production checkout is not main"
  [ -z "$("$GIT" status --porcelain=v1)" ] || fail "production tracked/untracked changes present"
}
backup() {
  local before path epoch
  before=$(/usr/bin/date -u +%s)
  "$ROOT/scripts/backup_postgres.sh"
  path=$(/usr/bin/find /opt/backups -maxdepth 1 -type f -name 'ccwbot-postgres-*.sql.gz' -printf '%T@ %p\n' | /usr/bin/sort -rn | /usr/bin/head -n 1 | /usr/bin/cut -d' ' -f2-)
  [ -n "$path" ] && [ -f "$path" ] || fail "backup file missing"
  epoch=$(/usr/bin/stat -c %Y "$path")
  [ "$epoch" -ge "$before" ] || fail "backup is not fresh"
  /usr/bin/gzip -t "$path" || fail "backup gzip verification failed"
  echo "verified_backup=$path"
}
health_check() {
  local i
  "$DOCKER" compose ps
  for i in $(/usr/bin/seq 1 15); do
    if /usr/bin/curl --fail --silent --max-time 5 --output /dev/null http://127.0.0.1:8080/health; then
      echo "health=ok"
      return 0
    fi
    /usr/bin/sleep 2
  done
  fail "health check failed after restart"
}
if [ "$action" = status ]; then status; exit; fi
exec 9>"$LOCK"
/usr/bin/flock -n 9 || fail "another deploy action is running"
clean_main
case "$action" in
  backup)
    backup
    ;;
  deploy)
    previous=$("$GIT" rev-parse HEAD)
    echo "deployment_start_utc=$(/usr/bin/date -u +%Y-%m-%dT%H:%M:%SZ)"
    "$GIT" fetch origin main
    candidate=$("$GIT" rev-parse refs/remotes/origin/main)
    "$GIT" merge-base --is-ancestor "$previous" "$candidate" || fail "origin main is not fast-forward"
    if [ "$previous" != "$candidate" ]; then
      if [ -n "$("$GIT" diff --name-only "$previous" "$candidate" -- alembic/versions/ ops_agent/)" ]; then
        fail "release includes migrations or ops-agent changes; use the manual deploy runbook"
      fi
    fi
    backup
    "$GIT" merge --ff-only "$candidate"
    "$DOCKER" compose config -q
    "$DOCKER" compose up -d --build
    health_check
    /usr/bin/install -d -o root -g root -m 700 "$STATE"
    printf '%s\n%s\n' "$previous" "$candidate" > "$STATE/last-deploy.tmp"
    /usr/bin/chmod 600 "$STATE/last-deploy.tmp"
    /usr/bin/mv -f "$STATE/last-deploy.tmp" "$STATE/last-deploy"
    echo "deployment_head=$candidate"
    ;;
  rollback)
    [ -r "$STATE/last-deploy" ] || fail "no verified previous deploy"
    mapfile -t ver < "$STATE/last-deploy"
    [ "${#ver[@]}" = 2 ] || fail "invalid rollback state"
    previous="${ver[0]}"
    deployed="${ver[1]}"
    [ "$("$GIT" rev-parse HEAD)" = "$deployed" ] || fail "current HEAD does not match last successful deploy"
    "$GIT" merge-base --is-ancestor "$previous" "$deployed" || fail "rollback target is not ancestor"
    backup
    "$GIT" reset --hard "$previous"
    "$DOCKER" compose config -q
    "$DOCKER" compose up -d --build
    health_check
    /usr/bin/rm -f "$STATE/last-deploy"
    echo "rollback_head=$previous"
    ;;
esac
