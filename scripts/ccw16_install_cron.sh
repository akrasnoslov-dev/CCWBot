#!/bin/sh
# Separate CCW-16 user cron; never modify or re-enable cancelled CCW-28 jobs.
set -eu
[ "$(id -un)" = "ccwbot_ops" ] || {
  echo "Must run as ccwbot_ops" >&2
  exit 1
}
BASE=/home/ccwbot_ops/ccw16_replay
[ -f "$BASE/runner.py" ] && [ -f "$BASE/ccw16_server_tick.py" ] && [ -f "$BASE/private_calls.json" ] || {
  echo "Private CCW-16 staging incomplete; no cron installed" >&2
  exit 1
}
command -v crontab >/dev/null 2>&1 || {
  echo "crontab unavailable; no cron installed" >&2
  exit 1
}
/usr/bin/python3 "$BASE/ccw16_server_tick.py" --dry-run >/dev/null
TMP=$(mktemp)
ERR=$(mktemp)
trap 'rm -f "$TMP" "$ERR"' EXIT HUP INT TERM
umask 077
if crontab -l > "$TMP" 2> "$ERR"; then
  :
elif grep -qi 'no crontab for' "$ERR"; then
  :
else
  echo "Cannot read existing crontab; refusing overwrite" >&2
  exit 1
fi
if grep -q 'CCW16_ISOLATED_PILOT' "$TMP"; then
  echo "CCW-16 schedule already present; unchanged"
  exit 0
fi
printf '%s\n' '*/10 * * * * umask 077; /usr/bin/python3 /home/ccwbot_ops/ccw16_replay/ccw16_server_tick.py --tick >> /home/ccwbot_ops/ccw16_replay/cron-status.log 2>&1 # CCW16_ISOLATED_PILOT' >> "$TMP"
crontab "$TMP"
echo "CCW-16 user cron installed: one attempt/provider every ten minutes at most"
