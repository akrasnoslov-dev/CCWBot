"""Least-privilege deploy contract and isolated, production-free behavior simulations."""

import http.server
import json
import os
import re
import shlex
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "scripts" / "ccwbot-deploy-safe.sh"
SUDOERS = ROOT / "scripts" / "ccwbot-deploy.sudoers"
OLD = "a" * 40
NEW = "b" * 40


class ContractTests(unittest.TestCase):
    def test_shell_syntax(self):
        if os.name == "nt":
            self.skipTest("Linux shell contract runs in GitHub CI")
        subprocess.run(["bash", "-n", str(WRAPPER)], check=True)

    def test_sudoers_is_narrow(self):
        text = SUDOERS.read_text(encoding="utf-8")
        self.assertEqual(text.count("ccwbot_deploy ALL="), 1)
        for bad in ("NOPASSWD: ALL", "/usr/bin/docker", "/bin/bash"):
            self.assertNotIn(bad, text)
        for action in ("status", "backup", "deploy", "rollback"):
            self.assertIn(f"/usr/local/bin/ccwbot-deploy-safe {action}", text)
        self.assertIn("env_reset", text)

    def test_security_guards_present(self):
        source = WRAPPER.read_text(encoding="utf-8")
        for needle in (
            "set -Eeuo pipefail", "umask 077", "trusted_path /opt dir",
            "trusted_path /usr/local/bin/ccwbot-deploy-safe file",
            "trusted_path /opt/backups dir", "[ ! -L /opt/backups ]",
            'trusted_path "$ROOT/.git/config" file',
            'trusted_path "$ROOT/scripts/backup_postgres.sh" file',
            'trusted_path "$ROOT/docker-compose.yml" file',
            'trusted_path /run dir', '[ ! -L "$LOCK_DIR" ]',
            'exec 9< "$LOCK_DIR"', "/usr/bin/flock -n 9",
            "compose config --format json", 'payload.get("status")=="ok"',
            'if [ "$previous" = "$candidate" ]', "deployment_noop=",
            "restore_after_failure", "gzip -t", "merge --ff-only",
            "alembic/versions/ ops_agent/",
        ):
            self.assertIn(needle, source)
        self.assertNotIn("/run/lock/", source)
        self.assertNotIn('exec 9>"', source)

    def test_root_path_guard_rejects_symlink_and_writable_file(self):
        if os.name == "nt":
            self.skipTest("POSIX mode checks run on Linux")
        source = WRAPPER.read_text(encoding="utf-8")
        guard = re.search(r"(?ms)^trusted_path\(\) \{.*?^\}", source).group()
        guard = guard.replace('= 0 ] || fail', '= "$(/usr/bin/id -u)" ] || fail')
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "trusted"
            path.write_text("untouched")
            target = Path(td) / "link"
            target.symlink_to(path)
            command = "fail() { echo \"$*\" >&2; exit 2; }\n" + guard + "\ntrusted_path \"$1\" file"
            bad_link = subprocess.run(
                ["bash", "-c", command, "bash", str(target)], capture_output=True, text=True
            )
            self.assertNotEqual(bad_link.returncode, 0)
            self.assertIn("symlinked", bad_link.stderr)
            path.chmod(0o666)
            bad_mode = subprocess.run(
                ["bash", "-c", command, "bash", str(path)], capture_output=True, text=True
            )
            self.assertNotEqual(bad_mode.returncode, 0)
            self.assertIn("writable", bad_mode.stderr)


@unittest.skipIf(os.name == "nt", "Linux-only mock service contract (runs in GitHub CI)")
class SimulatedDeployTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        self.state = self.base / "state"
        self.state.mkdir(mode=0o700)
        self.lock = self.base / "lock"
        self.git = self.base / "git-mock"
        self.docker = self.base / "docker-mock"
        self.head = self.base / "head"
        self.head.write_text(OLD)
        self.upcount = self.base / "upcount"
        self.port = 0
        self.requests = []
        self.degrade_when = ""
        test = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                test.requests.append(self.path)
                current = test.head.read_text()
                status = "degraded" if current == test.degrade_when else "ok"
                body = json.dumps({"status": status}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.compose_json = self.base / "compose.json"
        self.set_port(self.port)
        self.git.write_text(r'''#!/usr/bin/env bash
case "$1" in
  remote) echo "https://github.com/akrasnoslov-dev/CCWBot.git" ;;
  branch) echo main ;;
  status) : ;;
  rev-parse)
    if [ "$2" = HEAD ]; then cat "$TEST_HEAD"; else cat "$TEST_CANDIDATE"; fi ;;
  fetch|merge-base|cat-file) : ;;
  diff) [ "$TEST_MIGRATION" != 1 ] || echo "alembic/versions/001.py" ;;
  merge) cp "$TEST_CANDIDATE" "$TEST_HEAD" ;;
  reset) printf '%s' "$3" > "$TEST_HEAD" ;;
  *) echo "unexpected git action: $*" >&2; exit 1 ;;
esac
''')
        self.docker.write_text(r'''#!/usr/bin/env bash
case "$*" in
  "compose config --format json") cat "$TEST_COMPOSE_JSON" ;;
  "compose config -q"|"compose ps") : ;;
  "compose up -d --build")
    n=0
    [ ! -f "$TEST_UPCOUNT" ] || n=$(cat "$TEST_UPCOUNT")
    n=$((n+1)); echo "$n" > "$TEST_UPCOUNT"
    if [ "$TEST_FAIL_FIRST_UP" = 1 ] && [ "$n" = 1 ]; then exit 1; fi ;;
  *) echo "unexpected docker action: $*" >&2; exit 1 ;;
esac
''')
        self.git.chmod(0o755)
        self.docker.chmod(0o755)
        self.candidate = self.base / "candidate"
        self.candidate.write_text(NEW)
        source = WRAPPER.read_text(encoding="utf-8")
        for key, val in {
            "ROOT": self.repo, "STATE": self.state, "LOCK_DIR": self.lock,
            "GIT": self.git, "DOCKER": self.docker,
        }.items():
            source = re.sub(rf"(?m)^{key}=.*$", f"{key}={shlex.quote(str(val))}", source, count=1)
        source = source.replace('[ "$(/usr/bin/id -u)" = 0 ]', '[ 0 = 0 ]')
        source = re.sub(
            r"(?ms)^trusted_path\(\) \{.*?^\}", "trusted_path() { :; }", source, count=1
        )
        source = re.sub(
            r"(?ms)^backup\(\) \{.*?^\}",
            ('backup() { [ "$TEST_BACKUP_FAIL" != 1 ] || fail "backup command failed"; '
             'echo verified_backup=mock; }'),
            source, count=1,
        )
        source = source.replace("/usr/bin/seq 1 15", "/usr/bin/seq 1 2")
        source = source.replace("/usr/bin/sleep 2", "/usr/bin/true")
        self.script = self.base / "wrapper"
        self.script.write_text(source)
        self.env = {
            **os.environ, "TEST_HEAD": str(self.head),
            "TEST_CANDIDATE": str(self.candidate), "TEST_COMPOSE_JSON": str(self.compose_json),
            "TEST_UPCOUNT": str(self.upcount), "TEST_BACKUP_FAIL": "0",
            "TEST_MIGRATION": "0", "TEST_FAIL_FIRST_UP": "0",
        }

    def set_port(self, port, host="127.0.0.1"):
        self.compose_json.write_text(json.dumps({
            "services": {
                "bot": {"ports": [{"host_ip": host, "protocol": "tcp", "published": str(port)}]}
            }
        }))

    def run_action(self, *args, env=None):
        return subprocess.run(
            ["bash", str(self.script), *args],
            env={**self.env, **(env or {})}, capture_output=True, text=True, timeout=15,
        )

    def record(self):
        file = self.state / "last-deploy"
        file.write_text(f"{OLD}\n{NEW}\n")
        file.chmod(0o600)
        return file

    def test_noop_preserves_rollback_and_avoids_restart_backup(self):
        self.head.write_text(NEW)
        record = self.record()
        before = record.read_bytes()
        result = self.run_action("deploy")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("deployment_noop=", result.stdout)
        self.assertEqual(record.read_bytes(), before)
        self.assertNotIn("verified_backup=", result.stdout)
        self.assertFalse(self.upcount.exists())
        self.assertEqual(self.requests, ["/health"])

    def test_deploy_and_rollback_success(self):
        result = self.run_action("deploy")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.head.read_text(), NEW)
        self.assertEqual((self.state / "last-deploy").read_text(), f"{OLD}\n{NEW}\n")
        self.assertEqual((self.state / "last-deploy").stat().st_mode & 0o777, 0o600)
        rollback = self.run_action("rollback")
        self.assertEqual(rollback.returncode, 0, rollback.stderr)
        self.assertEqual(self.head.read_text(), OLD)
        self.assertFalse((self.state / "last-deploy").exists())
        self.assertNotEqual(self.run_action("rollback").returncode, 0)

    def test_http_200_degraded_triggers_restoration(self):
        self.degrade_when = NEW
        record = self.record()
        before = record.read_bytes()
        result = self.run_action("deploy")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("previous service restored", result.stderr)
        self.assertEqual(self.head.read_text(), OLD)
        self.assertEqual(record.read_bytes(), before)
        self.assertGreaterEqual(len(self.requests), 3)

    def test_failed_build_restores_checkout_and_retains_state(self):
        record = self.record()
        before = record.read_bytes()
        result = self.run_action("deploy", env={"TEST_FAIL_FIRST_UP": "1"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("previous service restored", result.stderr)
        self.assertEqual(self.head.read_text(), OLD)
        self.assertEqual(record.read_bytes(), before)
        self.assertEqual(self.upcount.read_text().strip(), "2")

    def test_failed_backup_does_not_advance_revision(self):
        result = self.run_action("deploy", env={"TEST_BACKUP_FAIL": "1"})
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.head.read_text(), OLD)
        self.assertFalse(self.upcount.exists())
        self.assertFalse((self.state / "last-deploy").exists())

    def test_failed_backup_cleans_staged_record(self):
        result = self.run_action("deploy", env={"TEST_BACKUP_FAIL": "1"})
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.head.read_text(), OLD)
        self.assertEqual(list(self.state.glob("last-deploy.*")), [])

    def test_symlinked_state_directory_fails_before_backup(self):
        self.state.rmdir()
        other = self.base / "state-target"
        other.mkdir(mode=0o700)
        self.state.symlink_to(other, target_is_directory=True)
        result = self.run_action("deploy")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlinked state directory", result.stderr)
        self.assertEqual(self.head.read_text(), OLD)
        self.assertFalse(self.upcount.exists())

    def test_rollback_failure_restores_current_revision_and_record(self):
        self.head.write_text(NEW)
        record = self.record()
        self.degrade_when = OLD
        result = self.run_action("rollback")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("previous service restored", result.stderr)
        self.assertEqual(self.head.read_text(), NEW)
        self.assertTrue(record.exists())

    def test_rejects_sudo_argument_escape_and_migrations(self):
        self.assertNotEqual(self.run_action("deploy", "--force").returncode, 0)
        self.assertNotEqual(self.run_action("arbitrary").returncode, 0)
        result = self.run_action("deploy", env={"TEST_MIGRATION": "1"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("manual deploy", result.stderr)
        self.assertFalse(self.upcount.exists())

    def test_lock_symlink_is_rejected_without_touching_target(self):
        other = self.base / "other"
        other.mkdir()
        self.lock.symlink_to(other, target_is_directory=True)
        result = self.run_action("backup")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlinked lock directory", result.stderr)

    def test_non_localhost_health_binding_is_rejected(self):
        self.head.write_text(NEW)
        self.set_port(self.port, "0.0.0.0")
        result = self.run_action("deploy")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.requests)

if __name__ == "__main__":
    unittest.main()
