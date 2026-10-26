"""Local on-call engineer: polls Grafana's alert API every minute and hands each new firing alert to Claude Code.

Run with `make on-call` (Grafana Cloud; address and token from SSM) or `make on-call ALERTS=local` (local Grafana).
For each new alert it creates a separate git worktree on a branch oncall/<time>, starting at the commit of the
alerting version, and runs `claude -p` there with docs/team/on-call-engineer.md and the alert details. The agent
may commit a fix on that branch; it may not push or deploy. Each session's full log is saved in logs/.
Stop with Ctrl+C.
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
REPOSITORY = HERE.parent
LOGS = HERE / "logs"
HANDLED = HERE / "logs" / "handled.json"  # alerts already given to the agent, so a restart does not repeat them
WORKTREES = Path.home() / ".cache" / "artmneme-oncall"
ROLE = REPOSITORY / "docs" / "team" / "on-call-engineer.md"
# Read-only view of prod (fault switch, health, app logs), from the main checkout: the worktree may be older.
PROD_STATUS = REPOSITORY / "deploy" / "prod-status.sh"
POLL_SECONDS = 60
# What the agent may do without asking: read, edit, run tests and the app through uv, use git locally, call HTTP,
# look at prod read-only.
ALLOWED_TOOLS = ["Read", "Grep", "Glob", "Edit", "Write", "Bash(uv run:*)", "Bash(uv sync:*)", "Bash(curl:*)",
                 "Bash(ls:*)", "Bash(git status:*)", "Bash(git diff:*)", "Bash(git log:*)", "Bash(git show:*)",
                 "Bash(git add:*)", "Bash(git commit:*)", f"Bash({PROD_STATUS}:*)"]


def ssm(name: str) -> str:
    return subprocess.run(
        ["aws", "ssm", "get-parameter", "--profile", os.environ.get("SSM_PROFILE", "artmneme-deploy"),
         "--with-decryption", "--name", name, "--query", "Parameter.Value", "--output", "text"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def firing_alerts(grafana: str, token: str | None) -> list[dict]:
    request = urllib.request.Request(f"{grafana}/api/prometheus/grafana/api/v1/alerts")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:
        alerts = json.load(response)["data"]["alerts"]
    return [alert for alert in alerts if alert["state"].lower() in ("alerting", "firing")]


def key(alert: dict) -> str:
    """One alert episode: the same rule and labels, firing since the same moment."""
    return json.dumps([sorted(alert["labels"].items()), alert.get("activeAt")])


def start_commit(alert: dict) -> str:
    """The commit of the alerting version (image tag YYYYMMDD-HHMMSS-shortsha), else main."""
    match = re.fullmatch(r"\d{8}-\d{6}-([0-9a-f]{7})", alert["labels"].get("service_version", ""))
    if match and subprocess.run(["git", "cat-file", "-e", f"{match[1]}^{{commit}}"], cwd=REPOSITORY).returncode == 0:
        return match[1]
    return "main"


def investigate(alert: dict) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    branch = f"oncall/{stamp}"
    worktree = WORKTREES / stamp
    commit = start_commit(alert)
    subprocess.run(["git", "worktree", "add", "-q", "-b", branch, str(worktree), commit], cwd=REPOSITORY, check=True)
    details = {key: alert.get(key) for key in ("labels", "annotations", "activeAt", "value")}
    prompt = (
        f"{ROLE.read_text()}\n\n"
        f"The alert:\n{json.dumps(details, indent=2)}\n\n"
        f"You work in a separate git worktree on the branch {branch}, at commit {commit} (the alerting version, "
        "or main if it is unknown). Commit a fix only on this branch. Do not push, do not deploy, and do not "
        "change anything outside this worktree. The backend tests run with `cd backend && uv run pytest`. "
        f"For a prod alert, `{PROD_STATUS} [LINES]` shows prod read-only: the fault switch, the health check, "
        "the running image and the last app log lines (default 100). "
        "End with a short summary: root cause, evidence, and what you changed (or why nothing)."
    )
    log = LOGS / f"{stamp}.jsonl"
    print(f"{stamp}  alert {alert['labels'].get('alertname')}: agent started on {branch}; log {log}", flush=True)
    with log.open("w") as output:
        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
             "--permission-mode", "acceptEdits", "--allowedTools", *ALLOWED_TOOLS],
            cwd=worktree, stdout=output, stderr=subprocess.STDOUT, env={**os.environ},
        )
    commits = subprocess.run(["git", "log", "--oneline", f"{commit}..{branch}"], cwd=REPOSITORY,
                             capture_output=True, text=True).stdout.strip()
    print(f"{stamp}  agent finished (exit {result.returncode}); "
          + (f"commits on {branch}:\n{commits}" if commits else f"no commits; branch {branch} has no fix"), flush=True)
    subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], cwd=REPOSITORY)


def main() -> None:
    if os.environ.get("ALERTS", "cloud") == "local":
        grafana, token = "http://localhost:3000", None
    else:
        grafana, token = ssm("/artmneme/grafana-url").rstrip("/"), ssm("/artmneme/grafana-token")
    LOGS.mkdir(exist_ok=True)
    handled = set(json.loads(HANDLED.read_text())) if HANDLED.exists() else set()
    print(f"On call: polling {grafana} every {POLL_SECONDS} s. Ctrl+C stops.", flush=True)
    while True:
        try:
            for alert in firing_alerts(grafana, token):
                if key(alert) not in handled:
                    handled.add(key(alert))
                    HANDLED.write_text(json.dumps(sorted(handled)))
                    investigate(alert)
        except (OSError, ValueError, subprocess.CalledProcessError) as error:
            print(f"Polling failed, trying again next minute: {error}", file=sys.stderr, flush=True)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOn call stopped.")
