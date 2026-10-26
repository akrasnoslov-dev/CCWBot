#!/usr/bin/env bash
set -euo pipefail
cd /home/ccwbot_ops/ccw29_fresh200_luna
for i in {1..1440}; do
  if [[ -s openai_test_key.private ]]; then
    sleep 2
    if [[ -s openai_test_key.private ]] && [[ ! -e openai-luna-ledger.json ]]; then
      echo ISOLATED_LUNA_FRESH200_KEY_READY
      exec python3 -u openai_luna_200_runner.py
    fi
  fi
  sleep 30
done
echo FRESH200_LUNA_KEY_NOT_PROVISIONED_12H
exit 2
