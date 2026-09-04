"""Verification script ensuring bound issues have an implementation plan and pre-merge review."""

import json
import os
import re
import subprocess
import sys
from typing import List, Dict, Any, Tuple, Optional

PLAN_HEADER_PATTERN = re.compile(r"(?i)#+\s*Implementation Plan|Implementation Plan:")
REVIEW_HEADER_PATTERN = re.compile(
    r"(?i)#+\s*(?:Implementation Review|Plan Alignment)|(?:Implementation Review|Plan Alignment):"
)
CLOSING_PATTERN = re.compile(
    r"(?i)\b(?:close|closes|closed|fix|fixes|fixed|resolve|resolves|resolved)\s+(?:#(\d+)|https://github\.com/[^/\s]+/[^/\s]+/issues/(\d+))\b"
)


def extract_bound_issues(pr_body: Optional[str]) -> List[int]:
    """Extract issue numbers bound to a pull request using closing keywords."""
    if not pr_body:
        return []
    matches = CLOSING_PATTERN.findall(pr_body)
    issues = set()
    for m in matches:
        num_str = m[0] or m[1]
        if num_str:
            issues.add(int(num_str))
    return sorted(issues)


def has_comprehensive_plan(comments: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """Verify whether comments include a comprehensive implementation plan."""
    for c in comments:
        body = c.get("body", "")
        if PLAN_HEADER_PATTERN.search(body):
            if len(body.strip()) >= 80:
                return True, "Valid comprehensive implementation plan found."
            else:
                return (
                    False,
                    "Implementation plan found, but it is too short to be comprehensive (minimum 80 characters required).",
                )
    return False, "No comment containing an 'Implementation Plan' section was found."


def has_valid_review_or_alignment(comments: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """Verify whether comments include an implementation review confirming plan match or approved alignment."""
    for c in comments:
        body = c.get("body", "")
        if REVIEW_HEADER_PATTERN.search(body):
            matches_exact = bool(
                re.search(
                    r"(?i)(?:matches\s+(?:the\s+)?plan|plan\s+match).*(?:yes|true|exact)",
                    body,
                    re.DOTALL,
                )
            )
            has_approved_alignment = bool(
                re.search(
                    r"(?i)(?:plan\s+alignment|deviation).*(?:approved|status\s*:\s*approved)",
                    body,
                    re.DOTALL,
                )
            )
            if matches_exact:
                return True, "Implementation review confirms implementation matches plan."
            if has_approved_alignment:
                return True, "Plan alignment comment found with approved status."
            return (
                False,
                "Review comment found, but does not explicitly confirm 'Matches Plan: Yes' or 'Status: Approved' alignment.",
            )
    return (
        False,
        "No comment containing an 'Implementation Review' or 'Plan Alignment' section was found.",
    )


def fetch_issue_comments(repo: str, issue_number: int) -> List[Dict[str, Any]]:
    """Fetch comments for an issue using gh CLI."""
    endpoint = f"repos/{repo}/issues/{issue_number}/comments"
    cmd = ["gh", "api", endpoint]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def verify_issue_plan_and_review(
    pr_body: str, repo: str, fetcher=fetch_issue_comments
) -> Tuple[bool, List[str]]:
    """Verify all bound issues in PR body have both plan and review comments."""
    issues = extract_bound_issues(pr_body)
    if not issues:
        return False, ["PR description does not bind any issue (e.g. Closes #123)."]

    errors = []
    for issue_num in issues:
        try:
            comments = fetcher(repo, issue_num)
        except Exception as e:
            errors.append(f"Failed to fetch comments for Issue #{issue_num}: {e}")
            continue

        plan_ok, plan_msg = has_comprehensive_plan(comments)
        if not plan_ok:
            errors.append(f"Issue #{issue_num}: {plan_msg}")

        rev_ok, rev_msg = has_valid_review_or_alignment(comments)
        if not rev_ok:
            errors.append(f"Issue #{issue_num}: {rev_msg}")

    return len(errors) == 0, errors


def main() -> int:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    if event_name and event_name != "pull_request":
        print(f"Skipping plan verification for non-pull_request event: {event_name}")
        return 0

    pr_body = os.environ.get("PR_BODY", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "marius-patrik/ChessWithQuests")

    print(f"Verifying implementation plan and review for PR in {repo}...")
    success, errors = verify_issue_plan_and_review(pr_body, repo)
    if not success:
        print("❌ Implementation Plan & Review Verification Failed:", file=sys.stderr)
        for err in errors:
            print(f"   - {err}", file=sys.stderr)
        print("\nRules Enforced:", file=sys.stderr)
        print(
            "   1. Every issue must have a comprehensive Implementation Plan commented before implementation begins.",
            file=sys.stderr,
        )
        print(
            "   2. Every bound issue must have an Implementation Review comment before PR merge confirming",
            file=sys.stderr,
        )
        print(
            "      either exact plan match ('Matches Plan: Yes') or approved plan alignment ('Status: Approved').",
            file=sys.stderr,
        )
        return 1

    print("✅ All bound issues verified with implementation plans and pre-merge reviews!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
