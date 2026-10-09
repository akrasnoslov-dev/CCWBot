#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
unset BASH_ENV ENV CDPATH GIT_DIR GIT_WORK_TREE GIT_CONFIG_GLOBAL GIT_CONFIG_SYSTEM GIT_CONFIG_COUNT DOCKER_HOST DOCKER_CONTEXT COMPOSE_FILE COMPOSE_PROJECT_NAME CCWBOT_BACKUP_DIR CCWBOT_BACKUP_RETENTION_COUNT
ROOT=/opt/CCWBot
STATE=/var/lib/ccwbot-deploy
LOCK_DIR=/run/ccwbot-deploy-safe.lock
GIT=/usr/bin/git
DOCKER=/usr/bin/docker
ORIGIN=https://github.com/akrasnoslov-dev/CCWBot.git

fail() { echo "ccwbot-deploy-safe: $*" >&2; exit 2; }
[ "$(/usr/bin/id -u)" = 0 ] || fail "root execution required"
[ "$#" = 1 ] || fail "exactly one action is required"
case "$1" in status|backup|deploy|rollback) action=$1 ;; *) fail "unsupported action" ;; esac

trusted_path() {
  local path=$1 kind=$2 mode
  [ ! -L "$path" ] || fail "symlinked trusted path: $path"
  if [ "$kind" = dir ]; then
    [ -d "$path" ] || fail "trusted directory missing: $path"
  else
    [ -f "$path" ] || fail "trusted file missing: $path"
  fi
  [ "$(/usr/bin/stat -c %u -- "$path")" = 0 ] || fail "non-root-owned trusted path: $path"
  mode=$(/usr/bin/stat -c %a -- "$path")
  (( (8#$mode & 0022) == 0 )) || fail "writable trusted path: $path"
}
trusted_path /opt dir
trusted_path "$ROOT" dir
trusted_path "$ROOT/.git" dir
trusted_path "$ROOT/.git/config" file
trusted_path "$ROOT/scripts" dir
trusted_path "$ROOT/scripts/backup_postgres.sh" file
trusted_path "$ROOT/docker-compose.yml" file
trusted_path "$ROOT/Dockerfile" file
cd "$ROOT"
[ "$("$GIT" remote get-url origin)" = "$ORIGIN" ] || fail "unexpected repository origin"

# Directory locking avoids creating, following or truncating a predictable lock file.
acquire_lock() {
  trusted_path /run dir
  [ ! -L "$LOCK_DIR" ] || fail "symlinked lock directory"
  if [ ! -e "$LOCK_DIR" ]; then
    /usr/bin/mkdir -m 700 -- "$LOCK_DIR" || fail "could not create lock directory"
  fi
  trusted_path "$LOCK_DIR" dir
  [ "$(/usr/bin/stat -c %a -- "$LOCK_DIR")" = 700 ] || fail "lock directory must be mode 700"
  exec 9< "$LOCK_DIR" || fail "cannot open deploy lock"
  /usr/bin/flock -n 9 || fail "another deploy action is running"
}
ensure_state_dir() {
  trusted_path /var dir
  trusted_path /var/lib dir
  [ ! -L "$STATE" ] || fail "symlinked state directory"
  if [ ! -e "$STATE" ]; then
    /usr/bin/mkdir -m 700 -- "$STATE" || fail "cannot create state directory"
  fi
  trusted_path "$STATE" dir
  [ "$(/usr/bin/stat -c %a -- "$STATE")" = 700 ] || fail "state directory must be mode 700"
}
check_state_file() {
  [ ! -L "$STATE/last-deploy" ] || fail "symlinked rollback record"
  trusted_path "$STATE/last-deploy" file
  [ "$(/usr/bin/stat -c %a -- "$STATE/last-deploy")" = 600 ] || fail "rollback record must be mode 600"
}
clean_main() {
  [ "$("$GIT" branch --show-current)" = main ] || fail "production checkout is not main"
  [ -z "$("$GIT" status --porcelain=v1)" ] || fail "production tracked/untracked changes present"
}
backup() {
  local before path epoch
  before=$(/usr/bin/date -u +%s)
  "$ROOT/scripts/backup_postgres.sh" || fail "backup command failed"
  path=$(/usr/bin/find /opt/backups -maxdepth 1 -type f -name 'ccwbot-postgres-*.sql.gz' -printf '%T@ %p\n' | /usr/bin/sort -rn | /usr/bin/sed -n '1p' | /usr/bin/cut -d' ' -f2-)
  [ -n "$path" ] && [ -f "$path" ] || fail "backup file missing"
  epoch=$(/usr/bin/stat -c %Y -- "$path")
  [ "$epoch" -ge "$before" ] || fail "backup is not fresh"
  /usr/bin/gzip -t -- "$path" || fail "backup gzip verification failed"
  echo "verified_backup=$path"
}
# Consume effective Compose port without printing Compose JSON or secrets.
health_port() {
  "$DOCKER" compose config --format json | /usr/bin/python3 -c '
import json, sys
try:
    config = json.load(sys.stdin)
    ports = config["services"]["bot"]["ports"]
    matches = [p for p in ports if p.get("host_ip") == "127.0.0.1"
               and p.get("protocol", "tcp") == "tcp"]
    if len(matches) != 1:
        raise ValueError("expected one localhost health binding")
    port = int(matches[0]["published"])
    if not (1 <= port <= 65535):
        raise ValueError("invalid port")
except (KeyError, TypeError, ValueError, IndexError, AttributeError):
    sys.exit(1)
print(port)
'
}
probe_health() {
  local port
  port=$(health_port) || return 1
  /usr/bin/curl --fail --silent --max-time 5 "http://127.0.0.1:${port}/health" |
    /usr/bin/python3 -c 'import json,sys
try:
    payload=json.load(sys.stdin)
    ok=isinstance(payload,dict) and payload.get("status")=="ok"
except (ValueError,TypeError):
    ok=False
sys.exit(0 if ok else 1)'
}
health_check() {
  local i
  "$DOCKER" compose ps || return 1
  for i in $(/usr/bin/seq 1 15); do
    if probe_health; then
      echo "health=ok"
      return 0
    fi
    /usr/bin/sleep 2
  done
  echo "health=failed" >&2
  return 1
}
status() {
  echo "branch=$("$GIT" branch --show-current)"
  echo "head=$("$GIT" rev-parse HEAD)"
  "$DOCKER" compose ps || return 1
  if probe_health; then echo health=ok; else echo health=failed; return 1; fi
}
restore_after_failure() {
  local target=$1 operation=$2
  echo "ccwbot-deploy-safe: $operation failed; attempting to restore prior checkout" >&2
  "$GIT" reset --hard "$target" || fail "$operation failed; manual checkout recovery required"
  if "$DOCKER" compose config -q && "$DOCKER" compose up -d --build && health_check; then
    fail "$operation failed; previous service restored; inspect before retrying"
  fi
  fail "$operation failed; automatic recovery failed; manual service recovery required"
}
if [ "$action" = status ]; then status; exit; fi
acquire_lock
clean_main
case "$action" in
  backup) backup ;;
  deploy)
    previous=$("$GIT" rev-parse HEAD)
    echo "deployment_start_utc=$(/usr/bin/date -u +%Y-%m-%dT%H:%M:%SZ)"
    "$GIT" fetch origin main
    candidate=$("$GIT" rev-parse refs/remotes/origin/main)
    "$GIT" merge-base --is-ancestor "$previous" "$candidate" || fail "origin main is not fast-forward"
    if [ "$previous" = "$candidate" ]; then
      health_check || fail "existing release is not healthy; no-op kept rollback state"
      echo "deployment_noop=$candidate"
      exit 0
    fi
    if [ -n "$("$GIT" diff --name-only "$previous" "$candidate" -- alembic/versions/ ops_agent/)" ]; then
      fail "release includes migrations or ops-agent changes; use the manual deploy runbook"
    fi
    backup
    "$GIT" merge --ff-only "$candidate" || fail "fast-forward merge failed"
    if ! { "$DOCKER" compose config -q && "$DOCKER" compose up -d --build && health_check; }; then
      restore_after_failure "$previous" "deploy"
    fi
    ensure_state_dir
    if [ -e "$STATE/last-deploy" ] || [ -L "$STATE/last-deploy" ]; then check_state_file; fi
    tmp=$(/usr/bin/mktemp "$STATE/last-deploy.XXXXXXXX") || fail "could not create rollback record"
    printf '%s\n%s\n' "$previous" "$candidate" > "$tmp"
    /usr/bin/chmod 600 "$tmp"
    /usr/bin/mv -f -- "$tmp" "$STATE/last-deploy"
    echo "deployment_head=$candidate"
    ;;
  rollback)
    ensure_state_dir
    check_state_file
    mapfile -t ver < "$STATE/last-deploy"
    [ "${#ver[@]}" = 2 ] || fail "invalid rollback state"
    previous="${ver[0]}"
    deployed="${ver[1]}"
    [[ "$previous" =~ ^[0-9a-f]{40}$ ]] && [[ "$deployed" =~ ^[0-9a-f]{40}$ ]] || fail "invalid rollback SHAs"
    "$GIT" cat-file -e "${previous}^{commit}" && "$GIT" cat-file -e "${deployed}^{commit}" || fail "missing rollback commit"
    [ "$("$GIT" rev-parse HEAD)" = "$deployed" ] || fail "current HEAD does not match last successful deploy"
    "$GIT" merge-base --is-ancestor "$previous" "$deployed" || fail "rollback target is not ancestor"
    backup
    "$GIT" reset --hard "$previous" || fail "rollback checkout failed; manual recovery required"
    if ! { "$DOCKER" compose config -q && "$DOCKER" compose up -d --build && health_check; }; then
      restore_after_failure "$deployed" "rollback"
    fi
    /usr/bin/rm -f -- "$STATE/last-deploy"
    echo "rollback_head=$previous"
    ;;
esac
