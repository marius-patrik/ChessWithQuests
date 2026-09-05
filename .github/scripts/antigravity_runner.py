"""Runner script for containerized Antigravity CI agent.

Handles Google OAuth token refresh, stage dispatching (interpret, plan, implement, review, respond),
auto-labeling, and conventional commit generation.
"""

import argparse
import base64
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import uuid
from typing import Any, Dict, List, Optional, Tuple

ANTIGRAVITY_CLIENT_ID = os.environ.get("ANTIGRAVITY_CLIENT_ID", "")
ANTIGRAVITY_CLIENT_SECRET = os.environ.get("ANTIGRAVITY_CLIENT_SECRET", "")
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

TYPE_LABELS = ["feat", "bug", "chore", "refactor", "test", "ci", "docs"]
AREA_LABELS = ["area:model", "area:view", "area:controller", "area:ci", "area:docs"]


def refresh_google_oauth_token(
    refresh_token: str,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
) -> Dict[str, Any]:
    """Exchanges a Google OAuth refresh token for a fresh access token.

    Args:
        refresh_token: The long-lived Google OAuth refresh token.
        client_id: Google OAuth client ID (defaults to ANTIGRAVITY_CLIENT_ID env var).
        client_secret: Google OAuth client secret (defaults to ANTIGRAVITY_CLIENT_SECRET env var).

        client_secret: Google OAuth client secret.

    Returns:
        Dictionary containing access_token, expires_in, and token_type.

    Raises:
        RuntimeError: If the token exchange fails.
    """
    client_id = client_id or ANTIGRAVITY_CLIENT_ID or os.environ.get("ANTIGRAVITY_CLIENT_ID", "")
    client_secret = (
        client_secret
        or ANTIGRAVITY_CLIENT_SECRET
        or os.environ.get("ANTIGRAVITY_CLIENT_SECRET", "")
    )

    params = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        GOOGLE_TOKEN_ENDPOINT,
        data=params,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Google OAuth token refresh failed ({e.code}): {err_body}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error during token refresh: {e}") from e


def setup_antigravity_credentials(
    access_token: str,
    refresh_token: str,
    target_dir: Optional[str] = None,
) -> str:
    """Configures Antigravity credential files in target directory.

    Args:
        access_token: Active Google access token.
        refresh_token: Stored refresh token.
        target_dir: Destination directory (defaults to ~/.gemini/antigravity-cli).

    Returns:
        Path to configured credentials payload file.
    """
    if not target_dir:
        target_dir = os.path.expanduser("~/.gemini/antigravity-cli")
    os.makedirs(target_dir, exist_ok=True)

    token_payload = {
        "token": {
            "access_token": access_token,
            "token_type": "Bearer",
            "refresh_token": refresh_token,
            "expiry": "2099-01-01T00:00:00Z",
        },
        "auth_method": "consumer",
    }
    encoded = "go-keyring-base64:" + base64.b64encode(
        json.dumps(token_payload).encode("utf-8")
    ).decode("utf-8")

    cred_file = os.path.join(target_dir, "antigravity_token.json")
    for fname in ["antigravity_token.json", "token.json", "tokens.json"]:
        p = os.path.join(target_dir, fname)
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"raw": encoded, "payload": token_payload}, f, indent=2)

    # 1. Primary standalone file token store for Antigravity in container environments
    # (~/.gemini/jetski-standalone-oauth-token)
    gemini_base = os.path.expanduser("~/.gemini")
    os.makedirs(gemini_base, exist_ok=True)
    jetski_token_path = os.path.join(gemini_base, "jetski-standalone-oauth-token")
    with open(jetski_token_path, "w", encoding="utf-8") as f:
        json.dump(token_payload, f, indent=2)
    os.chmod(jetski_token_path, 0o600)

    # Mirror into target_dir
    mirror_path = os.path.join(target_dir, "jetski-standalone-oauth-token")
    with open(mirror_path, "w", encoding="utf-8") as f:
        json.dump(token_payload, f, indent=2)
    os.chmod(mirror_path, 0o600)

    # In Linux container environments, populate D-Bus SecretService keyring
    if sys.platform.startswith("linux"):
        try:
            if os.path.exists("/.dockerenv"):
                os.remove("/.dockerenv")
        except OSError:
            pass

        # Unlock gnome-keyring
        try:
            p_unlock = subprocess.Popen(
                ["gnome-keyring-daemon", "--unlock"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            p_unlock.communicate(input="\n")
        except Exception as e:
            print(f"gnome-keyring unlock notice: {e}", file=sys.stderr)

        # Store token via secret-tool under service 'gemini' and username 'antigravity'
        try:
            p_store = subprocess.Popen(
                [
                    "secret-tool",
                    "store",
                    "--label=Antigravity",
                    "service",
                    "gemini",
                    "username",
                    "antigravity",
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            p_store.communicate(input=encoded)
            print("Successfully populated SecretService keyring for agy CLI.")
        except Exception as e:
            print(f"secret-tool store notice: {e}", file=sys.stderr)

    return cred_file


def classify_type_and_area(text: str) -> Tuple[str, str]:
    """Classifies type and area labels from text content.

    Args:
        text: Title and body text to inspect.

    Returns:
        Tuple of (type_label, area_label).
    """
    lower = text.lower()

    # Determine type label
    t_label = "feat"
    if re.search(r"\b(fix|bug|error|crash|broken|fail)\b", lower):
        t_label = "bug"
    elif re.search(r"\b(docs|documentation|docstring|mkdocs)\b", lower):
        t_label = "docs"
    elif re.search(r"\b(refactor|clean|cleanup|simplify)\b", lower):
        t_label = "refactor"
    elif re.search(r"\b(test|pytest|testing|mock)\b", lower):
        t_label = "test"
    elif re.search(r"\b(ci|workflow|action|docker|runner)\b", lower):
        t_label = "ci"
    elif re.search(r"\b(chore|dependency|deps|bump)\b", lower):
        t_label = "chore"

    # Determine area label
    a_label = "area:ci"
    if re.search(
        r"\b(board|piece|game|rules|move|player|king|queen|rook|bishop|pawn|horse|quest|model)\b",
        lower,
    ):
        a_label = "area:model"
    elif re.search(r"\b(view|gui|window|display|render|screen|ui)\b", lower):
        a_label = "area:view"
    elif re.search(r"\b(controller|event|input|handler)\b", lower):
        a_label = "area:controller"
    elif re.search(r"\b(doc|docs|documentation|mkdocs|material)\b", lower):
        a_label = "area:docs"
    elif re.search(r"\b(ci|action|workflow|pipeline|docker|agent|runner|automation)\b", lower):
        a_label = "area:ci"

    return t_label, a_label


def format_conventional_commit(commit_type: str, scope: str, description: str) -> str:
    """Formats a commit message adhering to Conventional Commits.

    Args:
        commit_type: One of feat, bug/fix, chore, refactor, test, ci, docs.
        scope: Scope identifier (e.g. model, view, ci, docs).
        description: Brief description of the change.

    Returns:
        Formatted conventional commit title.
    """
    t = "fix" if commit_type == "bug" else commit_type
    scope_clean = scope.replace("area:", "").strip()
    desc_clean = description.strip()
    if desc_clean and desc_clean[0].isupper():
        desc_clean = desc_clean[0].lower() + desc_clean[1:]
    return f"{t}({scope_clean}): {desc_clean}"


def run_gh(args: List[str], repo: Optional[str] = None) -> str:
    """Executes a gh CLI command and returns stdout.

    Args:
        args: List of command-line arguments.
        repo: Optional repository slug.

    Returns:
        Output string.
    """
    cmd = ["gh"] + args
    if repo:
        cmd.extend(["--repo", repo])
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return res.stdout.strip()


def is_bot_or_agent_comment(user_login: str, body: str) -> bool:
    """Detects whether a comment originated from automation or the agent itself."""
    if (
        user_login.endswith("[bot]")
        or user_login == "app/github-actions"
        or user_login == "github-actions"
    ):
        return True
    lower = body.strip().lower()
    if (
        lower.startswith("### antigravity agent")
        or lower.startswith("### implementation plan")
        or lower.startswith("### implementation review")
        or "[antigravity agent" in lower
        or "autogenerated by antigravity" in lower
        or "<!-- antigravity-agent -->" in lower
    ):
        return True
    return False


def run_agy_prompt(prompt: str, model: str = "gemini-3.8-flash-high", timeout: str = "5m0s") -> str:
    """Executes a prompt non-interactively using Antigravity CLI.

    Args:
        prompt: Instruction prompt to execute.
        model: Model tier or ID to use.
        timeout: Print mode timeout (default 5m0s, use longer for implementation).

    Returns:
        Agent text output or explicit error description.
    """
    cmd = [
        "agy",
        "--print",
        prompt,
        "--model",
        model,
        "--dangerously-skip-permissions",
        "--print-timeout",
        timeout,
    ]
    env = os.environ.copy()
    env.setdefault("TERM", "xterm-256color")
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
        return res.stdout.strip()
    except FileNotFoundError:
        err = "[Antigravity Agent Execution Error]: `agy` CLI binary not found in PATH."
        print(err, file=sys.stderr)
        return err
    except subprocess.CalledProcessError as e:
        detail = e.stderr.strip() or e.stdout.strip() or str(e)
        err = f"[Antigravity Agent Execution Error]: `agy` invocation failed (exit code {e.returncode}): {detail}"
        print(err, file=sys.stderr)
        return err
    except Exception as e:
        err = f"[Antigravity Agent Execution Error]: Unexpected failure executing `agy`: {e}"
        print(err, file=sys.stderr)
        return err


def handle_interpret(issue_number: int, repo: str):
    """Generates and posts an interpretation comment on a Request issue."""
    raw_issue = run_gh(
        ["issue", "view", str(issue_number), "--json", "title,body,labels"], repo=repo
    )
    data = json.loads(raw_issue)
    title = data.get("title", "")
    body = data.get("body", "")

    t_label, a_label = classify_type_and_area(f"{title} {body}")
    run_gh(["issue", "edit", str(issue_number), "--add-label", f"{t_label},{a_label}"], repo=repo)

    prompt = (
        f"Analyze this user request issue:\nTitle: {title}\nBody: {body}\n\n"
        "Draft a structured Interpretation comment containing:\n"
        "1. Verbatim Request Summary\n"
        "2. Architectural Scope & Breakdown\n"
        "3. Proposed Verification Plan\n"
        "Keep it concise and clear."
    )
    interpretation = run_agy_prompt(prompt)

    if interpretation.startswith("[Antigravity Agent Execution Error]"):
        comment = (
            "<!-- antigravity-agent -->\n"
            f"### Antigravity Agent Execution Error\n\n"
            f"{interpretation}\n"
        )
    else:
        comment = (
            "<!-- antigravity-agent -->\n"
            f"### Antigravity Agent Interpretation\n\n"
            f"{interpretation}\n\n"
            f"---\n*Assigned Labels: `{t_label}`, `{a_label}`. Waiting for user approval (`approve`) to create branch and plan.*"
        )
    run_gh(["issue", "comment", str(issue_number), "--body", comment], repo=repo)
    print(f"Interpretation posted on issue #{issue_number}")


def create_child_plan_issue(request_number: int, repo: str) -> int:
    """Creates a child Plan issue natively linked via --parent to the Request issue."""
    req_data = json.loads(
        run_gh(["issue", "view", str(request_number), "--json", "title,body"], repo=repo)
    )
    raw_title = req_data.get("title", "")
    plan_title = f"Plan: {raw_title.removeprefix('Request: ').strip()}"
    initial_body = f"Implementation plan for Parent Request #{request_number}.\n\nLinked Parent: #{request_number}"

    # Try creating directly with --parent flag
    create_args = [
        "issue",
        "create",
        "--title",
        plan_title,
        "--body",
        initial_body,
        "--label",
        "Plan",
        "--parent",
        str(request_number),
    ]
    try:
        out = run_gh(create_args, repo=repo)
        match = re.search(r"/issues/(\d+)", out)
        if match:
            plan_num = int(match.group(1))
            print(f"Created child Plan issue #{plan_num} with parent #{request_number}")
            return plan_num
    except Exception as e:
        print(
            f"Notice: creating with --parent failed ({e}); falling back to create then edit...",
            file=sys.stderr,
        )

    # Fallback: create then link parent
    out = run_gh(
        ["issue", "create", "--title", plan_title, "--body", initial_body, "--label", "Plan"],
        repo=repo,
    )
    match = re.search(r"/issues/(\d+)", out)
    if not match:
        raise RuntimeError(f"Could not parse created issue number from output: {out}")
    plan_num = int(match.group(1))
    try:
        run_gh(["issue", "edit", str(plan_num), "--parent", str(request_number)], repo=repo)
        print(f"Linked parent #{request_number} to child Plan issue #{plan_num} via edit")
    except Exception as e:
        try:
            run_gh(
                ["issue", "edit", str(request_number), "--add-sub-issue", str(plan_num)], repo=repo
            )
            print(f"Added sub-issue #{plan_num} to parent #{request_number} via edit")
        except Exception as e2:
            print(
                f"Warning: could not link parent issue #{request_number} to #{plan_num}: {e2}",
                file=sys.stderr,
            )
    return plan_num


def handle_plan(request_number: int, plan_number: int, repo: str):
    """Generates and posts an implementation plan on the child Plan issue."""
    req_data = json.loads(
        run_gh(["issue", "view", str(request_number), "--json", "title,body"], repo=repo)
    )
    prompt = (
        f"Draft a detailed, step-by-step Implementation Plan for Request #{request_number}:\n"
        f"Title: {req_data.get('title')}\nDetails: {req_data.get('body')}\n\n"
        "Include Scope, Architectural & Code Changes, and Verification Steps."
    )
    plan_body = run_agy_prompt(prompt)

    if plan_body.startswith("[Antigravity Agent Execution Error]"):
        comment = (
            "<!-- antigravity-agent -->\n"
            f"### Antigravity Agent Execution Error\n\n"
            f"- **Parent Request**: #{request_number}\n\n"
            f"{plan_body}\n"
        )
    else:
        comment = (
            "<!-- antigravity-agent -->\n"
            "### Implementation Plan (Autogenerated by Antigravity Agent)\n\n"
            f"- **Parent Request**: #{request_number}\n\n"
            f"{plan_body}\n\n"
            "---\n*Comment `approve` to begin autonomous implementation on branch.*"
        )
    run_gh(["issue", "comment", str(plan_number), "--body", comment], repo=repo)
    print(f"Plan posted on issue #{plan_number}")


def handle_respond(issue_or_pr_num: int, comment_text: str, repo: str, is_pr: bool = False):
    """Generates a contextual agent response to human feedback."""
    prompt = (
        f"User posted the following feedback on {'PR' if is_pr else 'Issue'} #{issue_or_pr_num}:\n"
        f'"{comment_text}"\n\n'
        "Provide a direct, helpful, and concise response addressing the feedback and detailing next actions."
    )
    response = run_agy_prompt(prompt)
    if response.startswith("[Antigravity Agent Execution Error]"):
        body = f"<!-- antigravity-agent -->\n### Antigravity Agent Execution Error\n\n{response}"
    else:
        body = f"<!-- antigravity-agent -->\n### Antigravity Agent Response\n\n{response}"

    if is_pr:
        run_gh(["pr", "comment", str(issue_or_pr_num), "--body", body], repo=repo)
    else:
        run_gh(["issue", "comment", str(issue_or_pr_num), "--body", body], repo=repo)
    print(f"Responded to comment on #{issue_or_pr_num}")


MAX_REVIEW_ITERATIONS = 3
WORKSPACE_DIR = os.environ.get("GITHUB_WORKSPACE", "/workspace")


def find_parent_request_number(plan_number: int, repo: str) -> Optional[int]:
    """Finds the parent Request issue number from a Plan issue body.

    Parses the Plan issue body for a 'Parent Request: #N' reference.

    Args:
        plan_number: The Plan issue number.
        repo: Repository slug (owner/name).

    Returns:
        Parent Request issue number, or None if not found.
    """
    raw = run_gh(["issue", "view", str(plan_number), "--json", "body"], repo=repo)
    body = json.loads(raw).get("body", "")
    match = re.search(r"Parent Request:\s*#(\d+)", body)
    if match:
        return int(match.group(1))
    return None


def generate_branch_name(title: str) -> str:
    """Generates a feature branch name from a plan or request title.

    Produces lowercase, hyphenated names prefixed with 'feature/'.
    Issue number references (#N) are stripped per AGENTS.md §7.

    Args:
        title: The plan or request issue title.

    Returns:
        Branch name string (e.g. 'feature/add-link-to-docs-and-diagram').
    """
    clean = re.sub(r"^(?:Plan|Request):\s*", "", title, flags=re.IGNORECASE).strip()
    clean = re.sub(r"#\d+", "", clean).strip()
    slug = re.sub(r"[^a-z0-9]+", "-", clean.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if len(slug) > 50:
        slug = slug[:50].rstrip("-")
    return f"feature/{slug}"


def run_git(args: List[str], cwd: Optional[str] = None) -> str:
    """Executes a git command and returns stdout.

    Args:
        args: Git subcommand and arguments.
        cwd: Working directory (defaults to WORKSPACE_DIR).

    Returns:
        Command stdout stripped.

    Raises:
        subprocess.CalledProcessError: If git command fails.
    """
    cmd = ["git"] + args
    res = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=cwd or WORKSPACE_DIR)
    return res.stdout.strip()


def handle_implement(plan_number: int, request_number: int, repo: str):
    """Implements a plan: creates branch, runs agy, commits, pushes, opens PR, reviews.

    Triggered when a user comments 'approve' on a Plan issue. Executes the full
    autonomous pipeline: implement → open Draft PR → self-review → plan alignment → mark ready.

    Args:
        plan_number: The child Plan issue number.
        request_number: The parent Request issue number.
        repo: Repository slug (owner/name).
    """
    cwd = WORKSPACE_DIR

    # 1. Read plan and request content
    plan_data = json.loads(
        run_gh(["issue", "view", str(plan_number), "--json", "title,body"], repo=repo)
    )
    request_data = json.loads(
        run_gh(["issue", "view", str(request_number), "--json", "title,body"], repo=repo)
    )
    plan_title = plan_data.get("title", "")
    plan_body = plan_data.get("body", "")
    request_title = request_data.get("title", "")
    request_body = request_data.get("body", "")

    # 2. Generate branch name
    branch_name = generate_branch_name(plan_title)
    print(f"Creating branch: {branch_name}")

    # 3. Configure git identity
    try:
        run_git(["config", "user.name", "github-actions[bot]"], cwd=cwd)
        run_git(
            [
                "config",
                "user.email",
                "41898282+github-actions[bot]@users.noreply.github.com",
            ],
            cwd=cwd,
        )
    except Exception as e:
        print(f"Git config notice: {e}", file=sys.stderr)

    # 4. Create feature branch from main
    try:
        run_git(["fetch", "origin", "main"], cwd=cwd)
        run_git(["checkout", "-b", branch_name, "origin/main"], cwd=cwd)
    except subprocess.CalledProcessError as e:
        err_msg = f"Failed to create branch {branch_name}: {e.stderr or e.stdout}"
        print(err_msg, file=sys.stderr)
        run_gh(
            [
                "issue",
                "comment",
                str(plan_number),
                "--body",
                f"<!-- antigravity-agent -->\n### Antigravity Agent Execution Error\n\n{err_msg}",
            ],
            repo=repo,
        )
        return

    # 5. Run agy to implement the plan (longer timeout for implementation)
    implement_prompt = (
        f"You are implementing a plan for a code repository.\n\n"
        f"## Parent Request (#{request_number})\n"
        f"Title: {request_title}\n{request_body}\n\n"
        f"## Implementation Plan (#{plan_number})\n"
        f"Title: {plan_title}\n{plan_body}\n\n"
        f"## Instructions\n"
        f"Implement ALL changes described in the plan above. "
        f"Write production code and corresponding unit tests. "
        f"Follow existing project conventions (Google-style docstrings, PEP 484 type annotations). "
        f"Do NOT create or modify files outside the scope of the plan."
    )
    impl_result = run_agy_prompt(implement_prompt, timeout="15m0s")
    if impl_result.startswith("[Antigravity Agent Execution Error]"):
        run_gh(
            [
                "issue",
                "comment",
                str(plan_number),
                "--body",
                f"<!-- antigravity-agent -->\n### Antigravity Agent Execution Error\n\n{impl_result}",
            ],
            repo=repo,
        )
        return
    print(f"Implementation complete. Agent output:\n{impl_result[:500]}")

    # 6. Auto-format with black
    subprocess.run(["black", "."], cwd=cwd, capture_output=True, text=True)

    # 7. Run pytest; if failures, ask agent to fix once
    test_res = subprocess.run(
        ["python3", "-m", "pytest", "tests/", "-q"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if test_res.returncode != 0:
        print(f"Tests failed, asking agent to fix...\n{test_res.stdout[-500:]}")
        fix_prompt = (
            f"The following test failures occurred after implementing the plan:\n\n"
            f"```\n{test_res.stdout[-2000:]}\n{test_res.stderr[-1000:]}\n```\n\n"
            f"Fix the failures while staying within the plan scope."
        )
        fix_result = run_agy_prompt(fix_prompt, timeout="10m0s")
        if not fix_result.startswith("[Antigravity Agent Execution Error]"):
            subprocess.run(["black", "."], cwd=cwd, capture_output=True, text=True)

    # 8. Classify and commit
    t_label, a_label = classify_type_and_area(f"{plan_title} {plan_body}")
    commit_title = format_conventional_commit(
        t_label, a_label, plan_title.removeprefix("Plan: ").strip()
    )

    try:
        run_git(["add", "-A"], cwd=cwd)
        status = run_git(["status", "--porcelain"], cwd=cwd)
        if not status:
            print("No changes to commit after implementation.")
            run_gh(
                [
                    "issue",
                    "comment",
                    str(plan_number),
                    "--body",
                    "<!-- antigravity-agent -->\n### Antigravity Agent Notice\n\n"
                    "No file changes produced by implementation. Please review the plan scope.",
                ],
                repo=repo,
            )
            return
        run_git(["commit", "-m", commit_title], cwd=cwd)
        run_git(["push", "origin", branch_name], cwd=cwd)
        print(f"Pushed branch {branch_name}")
    except subprocess.CalledProcessError as e:
        err_msg = f"Git commit/push failed: {e.stderr or e.stdout}"
        print(err_msg, file=sys.stderr)
        run_gh(
            [
                "issue",
                "comment",
                str(plan_number),
                "--body",
                f"<!-- antigravity-agent -->\n### Antigravity Agent Execution Error\n\n{err_msg}",
            ],
            repo=repo,
        )
        return

    # 9. Open Draft PR via workflow dispatch
    pr_body = (
        f"## Summary of Changes\n\n"
        f"{impl_result[:2000]}\n\n"
        f"Closes #{request_number}\n"
        f"Closes #{plan_number}\n"
    )
    try:
        run_gh(
            [
                "workflow",
                "run",
                "open-pr.yml",
                "-f",
                f"branch={branch_name}",
                "-f",
                f"title={commit_title}",
                "-f",
                f"body={pr_body}",
                "-f",
                "base=main",
                "-f",
                "draft=true",
            ],
            repo=repo,
        )
        print("Dispatched open-pr.yml workflow")
    except Exception as e:
        print(f"Failed to dispatch open-pr.yml: {e}", file=sys.stderr)
        try:
            run_gh(
                [
                    "pr",
                    "create",
                    "--head",
                    branch_name,
                    "--base",
                    "main",
                    "--title",
                    commit_title,
                    "--body",
                    pr_body,
                    "--draft",
                ],
                repo=repo,
            )
        except Exception as e2:
            print(f"Direct PR creation also failed: {e2}", file=sys.stderr)
            return

    # 10. Wait for PR to appear
    pr_number = None
    for _ in range(30):
        time.sleep(2)
        try:
            pr_list = run_gh(
                [
                    "pr",
                    "list",
                    "--head",
                    branch_name,
                    "--base",
                    "main",
                    "--state",
                    "open",
                    "--json",
                    "number",
                ],
                repo=repo,
            )
            prs = json.loads(pr_list)
            if prs:
                pr_number = prs[0]["number"]
                print(f"Found PR #{pr_number}")
                break
        except Exception:
            pass

    if not pr_number:
        print("Timed out waiting for PR creation.")
        return

    # 11. Self-review loop
    handle_self_review(pr_number, plan_number, repo)

    # 12. Plan alignment gate
    handle_plan_alignment(pr_number, plan_number, request_number, repo)


def handle_self_review(pr_number: int, plan_number: int, repo: str):
    """Runs a general PR code review loop via agy.

    Reviews the PR diff for code quality issues. Posts findings and fixes as
    comments on the PR. If fixes require out-of-scope changes, posts a Plan
    Deviation comment with justification on the parent Request issue before
    updating the Plan issue scope.

    Args:
        pr_number: The pull request number.
        plan_number: The child Plan issue number.
        repo: Repository slug (owner/name).
    """
    cwd = WORKSPACE_DIR

    for iteration in range(1, MAX_REVIEW_ITERATIONS + 1):
        print(f"Self-review iteration {iteration}/{MAX_REVIEW_ITERATIONS}")

        # Get PR diff
        try:
            diff = run_gh(["pr", "diff", str(pr_number)], repo=repo)
        except Exception as e:
            print(f"Failed to get PR diff: {e}", file=sys.stderr)
            return

        # Get plan content for scope awareness
        plan_data = json.loads(
            run_gh(["issue", "view", str(plan_number), "--json", "body"], repo=repo)
        )
        plan_body = plan_data.get("body", "")

        # Review via agy
        review_prompt = (
            f"Review the following pull request diff for code quality issues.\n"
            f"Look for: bugs, edge cases, missing error handling, missing tests, "
            f"style issues, naming problems, architectural concerns.\n\n"
            f"## Plan Scope (for reference — do NOT evaluate plan alignment here)\n"
            f"{plan_body[:2000]}\n\n"
            f"## PR Diff\n```diff\n{diff[:8000]}\n```\n\n"
            f"If you find NO actionable issues, respond starting with: NO_FINDINGS\n"
            f"If you find issues, list each finding with a description and suggested fix. "
            f"For each finding, mark it WITHIN_SCOPE or OUT_OF_SCOPE relative to the plan."
        )
        review_result = run_agy_prompt(review_prompt)

        if review_result.startswith("[Antigravity Agent Execution Error]"):
            run_gh(
                [
                    "pr",
                    "comment",
                    str(pr_number),
                    "--body",
                    f"<!-- antigravity-agent -->\n### Self-Review Error (Iteration {iteration})\n\n{review_result}",
                ],
                repo=repo,
            )
            return

        # Check if clean
        if "NO_FINDINGS" in review_result.upper()[:50]:
            run_gh(
                [
                    "pr",
                    "comment",
                    str(pr_number),
                    "--body",
                    f"<!-- antigravity-agent -->\n### Self-Review Findings (Iteration {iteration})\n\n"
                    f"✅ No actionable findings. Code review passed.",
                ],
                repo=repo,
            )
            print(f"Self-review passed clean on iteration {iteration}")
            return

        # Post findings on PR
        run_gh(
            [
                "pr",
                "comment",
                str(pr_number),
                "--body",
                f"<!-- antigravity-agent -->\n### Self-Review Findings (Iteration {iteration})\n\n{review_result}",
            ],
            repo=repo,
        )

        # Handle out-of-scope findings: post deviation on Request issue
        if "OUT_OF_SCOPE" in review_result.upper():
            request_number = find_parent_request_number(plan_number, repo)
            if request_number:
                deviation_prompt = (
                    f"The self-review found out-of-scope findings that need fixing. "
                    f"Generate a concise Plan Deviation comment explaining what needs "
                    f"to change and WHY it is necessary (justification), based on:\n\n"
                    f"{review_result}"
                )
                deviation_text = run_agy_prompt(deviation_prompt)
                if not deviation_text.startswith("[Antigravity Agent Execution Error]"):
                    run_gh(
                        [
                            "issue",
                            "comment",
                            str(request_number),
                            "--body",
                            f"<!-- antigravity-agent -->\n### Plan Deviation\n\n{deviation_text}",
                        ],
                        repo=repo,
                    )
                    run_gh(
                        [
                            "issue",
                            "comment",
                            str(plan_number),
                            "--body",
                            f"<!-- antigravity-agent -->\n### Scope Amendment\n\n{deviation_text}",
                        ],
                        repo=repo,
                    )

        # Fix findings via agy
        fix_prompt = (
            f"Fix the following code review findings in the workspace:\n\n"
            f"{review_result}\n\nMake the necessary changes to resolve all findings."
        )
        fix_result = run_agy_prompt(fix_prompt, timeout="10m0s")

        if fix_result.startswith("[Antigravity Agent Execution Error]"):
            run_gh(
                [
                    "pr",
                    "comment",
                    str(pr_number),
                    "--body",
                    f"<!-- antigravity-agent -->\n### Self-Review Fix Error (Iteration {iteration})\n\n{fix_result}",
                ],
                repo=repo,
            )
            return

        # Format, commit, push
        subprocess.run(["black", "."], cwd=cwd, capture_output=True, text=True)
        try:
            run_git(["add", "-A"], cwd=cwd)
            status = run_git(["status", "--porcelain"], cwd=cwd)
            if status:
                run_git(
                    [
                        "commit",
                        "-m",
                        f"fix(review): address self-review findings (iteration {iteration})",
                    ],
                    cwd=cwd,
                )
                run_git(["push", "origin", "HEAD"], cwd=cwd)
                run_gh(
                    [
                        "pr",
                        "comment",
                        str(pr_number),
                        "--body",
                        f"<!-- antigravity-agent -->\n### Self-Review Fix (Iteration {iteration})\n\n{fix_result[:2000]}",
                    ],
                    repo=repo,
                )
                print(f"Pushed review fixes for iteration {iteration}")
            else:
                print(f"No changes after fix attempt on iteration {iteration}")
                return
        except subprocess.CalledProcessError as e:
            print(f"Git error during review fix: {e.stderr or e.stdout}", file=sys.stderr)
            return

    print(f"Self-review loop exhausted after {MAX_REVIEW_ITERATIONS} iterations")


def handle_plan_alignment(pr_number: int, plan_number: int, request_number: int, repo: str):
    """Verifies that the PR implementation matches the plan scope exactly.

    Separate step from self-review. Compares the final PR diff against the Plan
    issue scope (including any scope amendments). Posts Implementation Review on
    the Plan issue and marks PR ready for human review only if aligned.

    Args:
        pr_number: The pull request number.
        plan_number: The child Plan issue number.
        request_number: The parent Request issue number.
        repo: Repository slug (owner/name).
    """
    # Get PR diff
    try:
        diff = run_gh(["pr", "diff", str(pr_number)], repo=repo)
    except Exception as e:
        print(f"Failed to get PR diff for alignment: {e}", file=sys.stderr)
        return

    # Get plan content including scope amendments from comments
    plan_data = json.loads(
        run_gh(
            ["issue", "view", str(plan_number), "--json", "title,body,comments"],
            repo=repo,
        )
    )
    plan_body = plan_data.get("body", "")
    amendments = []
    for c in plan_data.get("comments", []):
        if "Scope Amendment" in c.get("body", ""):
            amendments.append(c["body"])

    full_plan_scope = plan_body
    if amendments:
        full_plan_scope += "\n\n## Scope Amendments\n" + "\n".join(amendments)

    # Run alignment check via agy
    alignment_prompt = (
        f"Compare this PR diff against the implementation plan scope.\n\n"
        f"## Full Plan Scope\n{full_plan_scope[:4000]}\n\n"
        f"## PR Diff\n```diff\n{diff[:8000]}\n```\n\n"
        f"Determine if the implementation matches the plan scope EXACTLY.\n"
        f"If it matches, respond starting with: MATCHES_PLAN_YES\n"
        f"If there are divergences, list each divergence with details."
    )
    alignment_result = run_agy_prompt(alignment_prompt)

    if alignment_result.startswith("[Antigravity Agent Execution Error]"):
        run_gh(
            [
                "issue",
                "comment",
                str(plan_number),
                "--body",
                f"<!-- antigravity-agent -->\n### Plan Alignment Error\n\n{alignment_result}",
            ],
            repo=repo,
        )
        return

    if "MATCHES_PLAN_YES" in alignment_result.upper()[:50]:
        # Post Implementation Review on Plan issue
        run_gh(
            [
                "issue",
                "comment",
                str(plan_number),
                "--body",
                "<!-- antigravity-agent -->\n### Implementation Review\n\n"
                "**Matches Plan**: Yes\n\nAll changes in the PR align with the plan scope.",
            ],
            repo=repo,
        )
        # Mark PR ready for human review
        try:
            run_gh(["pr", "ready", str(pr_number)], repo=repo)
            print(f"PR #{pr_number} marked ready for review")
        except Exception as e:
            print(f"Failed to mark PR ready: {e}", file=sys.stderr)
    else:
        # Post alignment divergence on Request issue with justification
        run_gh(
            [
                "issue",
                "comment",
                str(request_number),
                "--body",
                f"<!-- antigravity-agent -->\n### Plan Alignment\n\n{alignment_result}",
            ],
            repo=repo,
        )
        # Post on Plan issue
        run_gh(
            [
                "issue",
                "comment",
                str(plan_number),
                "--body",
                f"<!-- antigravity-agent -->\n### Implementation Review\n\n"
                f"**Matches Plan**: No\n\n{alignment_result}",
            ],
            repo=repo,
        )
        print(f"Plan alignment divergence detected on PR #{pr_number}")


def dispatch_event(event_path: str, event_name: str):
    """Dispatches the event to the appropriate agent handler."""
    if not os.path.exists(event_path):
        print(f"Event path {event_path} not found.")
        return

    with open(event_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    repo = payload.get("repository", {}).get("full_name", "marius-patrik/ChessWithQuests")
    refresh_tok = os.environ.get("ANTIGRAVITY_REFRESH_TOKEN")

    if refresh_tok:
        try:
            tok_res = refresh_google_oauth_token(refresh_tok)
            setup_antigravity_credentials(tok_res["access_token"], refresh_tok)
            print("Successfully refreshed Antigravity Google OAuth token!")
        except Exception as e:
            print(f"Token refresh notice: {e}", file=sys.stderr)

    if event_name == "issues":
        action = payload.get("action")
        issue = payload.get("issue", {})
        issue_num = issue.get("number")
        labels = [l.get("name") if isinstance(l, dict) else str(l) for l in issue.get("labels", [])]

        if action == "opened" and issue_num:
            # Auto-tag as Request if unlabelled
            if not any(lbl.lower() in ("request", "plan") for lbl in labels):
                run_gh(["issue", "edit", str(issue_num), "--add-label", "Request"], repo=repo)
                print(f"Auto-labeled issue #{issue_num} as Request")
            handle_interpret(issue_num, repo)

    elif event_name == "issue_comment":
        action = payload.get("action")
        comment = payload.get("comment", {})
        comment_body = comment.get("body", "").strip()
        comment_user = comment.get("user", {}).get("login", "")
        issue = payload.get("issue", {})
        issue_num = issue.get("number")
        is_pr = "pull_request" in issue

        # Only process human comments from owner/collaborators, ignore bot/agent comments
        if action == "created" and issue_num:
            if is_bot_or_agent_comment(comment_user, comment_body):
                print(f"Skipping comment on #{issue_num} authored by bot/agent ({comment_user}).")
                return

            labels = [
                l.get("name") if isinstance(l, dict) else str(l) for l in issue.get("labels", [])
            ]
            is_request = any(l.lower() == "request" for l in labels)
            is_plan = any(l.lower() == "plan" for l in labels)
            if re.search(r"(?i)^\s*(?:/approve|approve|good|lgtm)\s*$", comment_body):
                print(f"Approval comment on #{issue_num} from @{comment_user}.")
                if is_request:
                    plan_num = create_child_plan_issue(issue_num, repo)
                    handle_plan(issue_num, plan_num, repo)
                elif is_plan:
                    request_num = find_parent_request_number(issue_num, repo)
                    if request_num:
                        handle_implement(issue_num, request_num, repo)
                    else:
                        print(f"Could not find parent Request for Plan #{issue_num}")
            else:
                handle_respond(issue_num, comment_body, repo=repo, is_pr=is_pr)

    elif event_name == "pull_request_review_comment":
        action = payload.get("action")
        comment = payload.get("comment", {})
        comment_body = comment.get("body", "").strip()
        comment_user = comment.get("user", {}).get("login", "")
        pr = payload.get("pull_request", {})
        pr_num = pr.get("number")

        if action == "created" and pr_num:
            if is_bot_or_agent_comment(comment_user, comment_body):
                print(
                    f"Skipping PR review comment on #{pr_num} authored by bot/agent ({comment_user})."
                )
                return
            print(f"PR review comment on #{pr_num} from @{comment_user}: {comment_body[:80]}...")
            handle_respond(pr_num, comment_body, repo=repo, is_pr=True)


def main():
    parser = argparse.ArgumentParser(description="Antigravity CI Agent Runner")
    parser.add_argument(
        "command",
        choices=[
            "dispatch",
            "interpret",
            "plan",
            "implement",
            "self-review",
            "plan-alignment",
            "respond",
            "token-refresh",
        ],
        nargs="?",
        default="dispatch",
    )
    parser.add_argument("--issue", type=int, help="Issue number")
    parser.add_argument("--request-issue", type=int, help="Parent request issue number")
    parser.add_argument("--plan-issue", type=int, help="Child plan issue number")
    parser.add_argument("--pr-number", type=int, help="Pull request number")
    parser.add_argument(
        "--repo", default="marius-patrik/ChessWithQuests", help="Repository full name"
    )
    parser.add_argument("--comment", help="Comment body for respond command")
    parser.add_argument("--is-pr", action="store_true", help="Flag if comment is on pull request")

    args = parser.parse_args()

    if args.command == "token-refresh":
        tok = os.environ.get("ANTIGRAVITY_REFRESH_TOKEN")
        if not tok:
            print("ANTIGRAVITY_REFRESH_TOKEN not set.", file=sys.stderr)
            sys.exit(1)
        res = refresh_google_oauth_token(tok)
        print(f"Success! access_token acquired (expires_in: {res.get('expires_in')}s)")
        setup_antigravity_credentials(res["access_token"], tok)

    elif args.command == "interpret" and args.issue:
        handle_interpret(args.issue, args.repo)

    elif args.command == "plan" and args.request_issue and args.plan_issue:
        handle_plan(args.request_issue, args.plan_issue, args.repo)

    elif args.command == "implement" and args.plan_issue and args.request_issue:
        handle_implement(args.plan_issue, args.request_issue, args.repo)

    elif args.command == "self-review" and args.pr_number and args.plan_issue:
        handle_self_review(args.pr_number, args.plan_issue, args.repo)

    elif (
        args.command == "plan-alignment"
        and args.pr_number
        and args.plan_issue
        and args.request_issue
    ):
        handle_plan_alignment(args.pr_number, args.plan_issue, args.request_issue, args.repo)

    elif args.command == "respond" and args.issue:
        handle_respond(args.issue, args.comment or "", args.repo, is_pr=args.is_pr)

    elif args.command == "dispatch":
        path = os.environ.get("GITHUB_EVENT_PATH", "")
        name = os.environ.get("GITHUB_EVENT_NAME", "")
        dispatch_event(path, name)


if __name__ == "__main__":
    main()
