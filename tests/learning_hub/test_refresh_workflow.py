"""Execute the workflow's PR step offline with the GitHub CLI boundary stubbed."""

import json
import os
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("author", "allowed"),
    [
        ("app/github-actions", True),
        ("github-actions[bot]", True),
        ("huanyusun", False),
        ("app/dependabot", False),
    ],
)
def test_refresh_pr_author_guard(tmp_path, author, allowed):
    workflow = (ROOT / ".github/workflows/learning-hub-refresh.yml").read_text()
    step = workflow.split("      - name: Create or update single PR\n", 1)[1]
    script = step.split("        run: |\n", 1)[1].split("\n      - name:", 1)[0]
    script = "\n".join(line[10:] for line in script.splitlines())
    script = script.replace("${{ github.event.repository.default_branch }}", "main")

    gh = tmp_path / "gh"
    gh.write_text(
        '#!/bin/bash\n'
        'printf "%s\\n" "$*" >> "$MOCK_GH_CALLS"\n'
        'if [ "$1 $2" = "pr list" ]; then\n'
        '  printf "%s\\n" "$MOCK_PR_JSON"\n'
        'fi\n'
    )
    gh.chmod(0o755)
    calls = tmp_path / "calls"
    env = {
        **os.environ,
        "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}",
        "HEAD_BRANCH": "automation/learning-hub-refresh",
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary"),
        "MOCK_GH_CALLS": str(calls),
        "MOCK_PR_JSON": json.dumps([{"number": 1, "author": {"login": author}}]),
    }
    result = subprocess.run(
        ["bash", "-e", "-c", script], env=env, text=True, capture_output=True
    )
    assert result.returncode == (0 if allowed else 1), result.stdout + result.stderr
    assert ("pr edit 1 --base main --body-file learning/updates/latest.md" in calls.read_text()) == allowed
    assert "pr create" not in calls.read_text()
