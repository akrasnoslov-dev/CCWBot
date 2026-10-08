"""Contract checks for the installed, least-privilege production deploy wrapper."""

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "scripts" / "ccwbot-deploy-safe.sh"
SUDOERS = ROOT / "scripts" / "ccwbot-deploy.sudoers"


def test_deploy_wrapper_shell_syntax() -> None:
    subprocess.run(["bash", "-n", str(WRAPPER)], check=True)


def test_deploy_wrapper_is_narrow_and_fail_closed() -> None:
    source = WRAPPER.read_text(encoding="utf-8")
    assert "set -Eeuo pipefail" in source
    assert 'case "$1" in status|backup|deploy|rollback)' in source
    assert '"$#" = 1' in source
    assert 'clean_main' in source
    assert 'merge --ff-only' in source
    assert 'merge-base --is-ancestor' in source
    assert 'scripts/backup_postgres.sh' in source
    assert 'gzip -t' in source
    assert 'alembic/versions/ ops_agent/' in source
    assert 'health_check' in source
    assert 'last-deploy' in source


def test_deploy_sudoers_has_only_fixed_operations() -> None:
    source = SUDOERS.read_text(encoding="utf-8")
    assert source.count("ccwbot_deploy ALL=") == 1
    assert "NOPASSWD: ALL" not in source
    assert "/usr/bin/docker" not in source
    assert "/bin/bash" not in source
    for operation in ("status", "backup", "deploy", "rollback"):
        assert (
            f"/usr/local/bin/ccwbot-deploy-safe {operation}" in source
        )
