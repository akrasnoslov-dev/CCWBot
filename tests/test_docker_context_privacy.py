"""Guard the production Docker build against packaging host-only files."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_docker_build_context_excludes_operator_secrets_and_research():
    rules = {
        line.strip()
        for line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    # The bot Dockerfile copies the build context; without these exclusions,
    # root-only host credentials and historic experiment data enter the image.
    required = {
        ".env",
        ".env.*",
        ".ops-agent.env",
        ".ops-agent.env.*",
        "logs/",
        "reports/",
        "graphify-out/",
    }
    missing = required - rules
    assert not missing, f"Missing Docker context exclusions: {sorted(missing)}"
