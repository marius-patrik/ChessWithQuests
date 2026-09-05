"""Runner script for containerized Antigravity CI agent.

Handles Google OAuth token refresh, stage dispatching (interpret, plan, implement, review, respond),
auto-labeling, and conventional commit generation.
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
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
        "auth_method": "oauth",
    }
    encoded = "go-keyring-base64:" + base64.b64encode(
        json.dumps(token_payload).encode("utf-8")
    ).decode("utf-8")

    cred_file = os.path.join(target_dir, "antigravity_token.json")
    with open(cred_file, "w", encoding="utf-8") as f:
        json.dump({"raw": encoded, "payload": token_payload}, f, indent=2)

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


def run_agy_prompt(prompt: str, model: str = "gemini-3.8-flash-high") -> str:
    """Executes a prompt non-interactively using Antigravity CLI.

    Args:
        prompt: Instruction prompt to execute.
        model: Model tier or ID to use.

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
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
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
            if re.search(r"(?i)^\s*(?:/approve|approve|good|lgtm)\s*$", comment_body):
                print(f"Approval comment on #{issue_num} from @{comment_user}.")
                if is_request:
                    plan_num = create_child_plan_issue(issue_num, repo)
                    handle_plan(issue_num, plan_num, repo)
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
        choices=["dispatch", "interpret", "plan", "respond", "token-refresh"],
        nargs="?",
        default="dispatch",
    )
    parser.add_argument("--issue", type=int, help="Issue number")
    parser.add_argument("--request-issue", type=int, help="Parent request issue number")
    parser.add_argument("--plan-issue", type=int, help="Child plan issue number")
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

    elif args.command == "respond" and args.issue:
        handle_respond(args.issue, args.comment or "", args.repo, is_pr=args.is_pr)

    elif args.command == "dispatch":
        path = os.environ.get("GITHUB_EVENT_PATH", "")
        name = os.environ.get("GITHUB_EVENT_NAME", "")
        dispatch_event(path, name)


if __name__ == "__main__":
    main()
