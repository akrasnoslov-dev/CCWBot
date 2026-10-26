#!/usr/bin/env bash
set -euo pipefail
cd /home/ccwbot_ops/ccw29_full200_v2
for i in {1..1440}; do
  if [[ -s openai_test_key.private ]]; then
    echo KEY_FILE_PRESENT_STARTING_ISOLATED_TEST
    exec python3 -u openai_luna_200_runner.py
  fi
  sleep 30
done
echo NO_TEST_KEY_PROVISIONED_WITHIN_12H
exit 2
