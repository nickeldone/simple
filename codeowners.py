#!/usr/bin/env python3
"""
codeowners - Fetch and display CODEOWNERS rules for a GitHub repository.

Usage:
    python codeowners.py <owner/repo>
    GITHUB_TOKEN=<token> python codeowners.py <owner/repo>

Required token scopes:
    - 'repo' for private repositories
    - No token required for public repositories (but rate limits apply)
"""

import argparse
import base64
import fnmatch
import json
import os
import re
import sys
from typing import Optional
import urllib.error
import urllib.request


# Common locations where CODEOWNERS files may be found, in order of precedence
CODEOWNERS_PATHS = [
    ".github/CODEOWNERS",
    "CODEOWNERS",
    "docs/CODEOWNERS",
]

GITHUB_API_BASE = "https://api.github.com"


def fetch_file(owner: str, repo: str, path: str, token: Optional[str]) -> Optional[str]:
    """
    Fetch the raw content of a file from the GitHub API.

    Returns the decoded file content if the file exists, or None if the file
    is not found (HTTP 404).
    Raises RuntimeError on HTTP 401/403 (permission errors) or other HTTP errors.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "codeowners-cli/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data.get("encoding") == "base64":
                return base64.b64decode(data["content"]).decode("utf-8")
            return data.get("content", "")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        if exc.code in (401, 403):
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"HTTP {exc.code} accessing {owner}/{repo}.\n"
                "You do not have permission to read this repository.\n\n"
                "To fix this:\n"
                "  1. Create a personal access token at https://github.com/settings/tokens\n"
                "  2. Grant the 'repo' scope for private repositories\n"
                "  3. Set the token via: export GITHUB_TOKEN=<your-token>\n"
                f"\nAPI response: {body}"
            ) from exc
        raise RuntimeError(f"HTTP {exc.code} fetching {path} from {owner}/{repo}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error fetching {path}: {exc.reason}") from exc


def find_codeowners(owner: str, repo: str, token: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """
    Try each standard CODEOWNERS location in precedence order.

    Returns a tuple of (path, content) for the first file found,
    or (None, None) if none exist.
    Raises RuntimeError if the API returns a permission error or other
    non-404 HTTP/network failure (propagated from fetch_file).
    """
    for path in CODEOWNERS_PATHS:
        content = fetch_file(owner, repo, path, token)
        if content is not None:
            return path, content
    return None, None


def parse_codeowners(content: str) -> list[dict]:
    """
    Parse a CODEOWNERS file and return a list of rules.

    Each rule is a dict with:
      - 'pattern': the file path pattern (str)
      - 'owners': list of owner strings (e.g. '@user', '@org/team', 'user@example.com')
      - 'line': the original source line (str)
      - 'line_number': 1-based line number (int)

    Blank lines and comment-only lines are skipped.
    """
    rules = []
    for line_number, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        # Skip blank lines and comments
        if not line or line.startswith("#"):
            continue
        # Inline comments: strip everything after an unquoted '#'
        if " #" in line:
            line = line[: line.index(" #")].rstrip()
        parts = line.split()
        pattern = parts[0]
        owners = parts[1:]
        rules.append({
            "pattern": pattern,
            "owners": owners,
            "line": raw_line,
            "line_number": line_number,
        })
    return rules


def match_path(file_path: str, pattern: str) -> bool:
    """
    Determine whether *file_path* matches a CODEOWNERS *pattern*.

    Implements a subset of the gitignore / CODEOWNERS pattern rules:
      - Leading '/' anchors the pattern to the root of the repository.
      - A trailing '/' matches directories and their contents.
      - '**' matches any number of path segments.
      - '*' matches anything within a single segment (no '/').
      - '?' matches any single character except '/'.
      - All other characters match literally.
    """
    # Normalise: strip leading slash from pattern for matching purposes
    anchored = pattern.startswith("/")
    pat = pattern.lstrip("/")

    # Trailing slash: match directory and contents
    if pat.endswith("/"):
        pat = pat + "**"

    # Normalise the file path (no leading slash)
    fp = file_path.lstrip("/")

    if "**" in pat:
        # Replace '**/' with a placeholder, then translate
        # We handle '**' by checking prefix/suffix semantics manually
        parts_pat = pat.split("**")
        # Simple approach: convert ** to a regex via fnmatch-like translation
        regex_parts = [re.escape(p).replace(r"\*", "[^/]*").replace(r"\?", "[^/]") for p in parts_pat]
        regex = ".*".join(regex_parts)
        if anchored:
            regex = "^" + regex + "$"
        else:
            regex = "(^|.*?/)" + regex + "$"
        return bool(re.match(regex, fp))
    else:
        if anchored:
            return fnmatch.fnmatch(fp, pat)
        else:
            # Pattern without anchor matches in any subdirectory
            return fnmatch.fnmatch(fp, pat) or fnmatch.fnmatch(fp, "*/" + pat)


def owners_for_path(file_path: str, rules: list[dict]) -> list[str]:
    """
    Return the list of owners for the given file path based on CODEOWNERS rules.

    CODEOWNERS uses last-match-wins semantics: the last matching rule takes
    precedence, so we iterate in reverse and return the first match.
    """
    for rule in reversed(rules):
        if match_path(file_path, rule["pattern"]):
            return rule["owners"]
    return []


def print_rules(rules: list[dict], codeowners_path: str) -> None:
    """Pretty-print the parsed CODEOWNERS rules to stdout."""
    print(f"CODEOWNERS file: {codeowners_path}")
    print(f"{'─' * 60}")
    if not rules:
        print("(no rules found)")
        return
    for rule in rules:
        owners_str = "  ".join(rule["owners"]) if rule["owners"] else "(no owners — unowned)"
        print(f"  {rule['pattern']:<40} {owners_str}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="codeowners",
        description="Fetch and display CODEOWNERS rules for a GitHub repository.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python codeowners.py github/github\n"
            "  GITHUB_TOKEN=ghp_... python codeowners.py my-org/my-private-repo\n\n"
            "Required token scopes:\n"
            "  Public repos  : no token needed (anonymous API calls)\n"
            "  Private repos : token with 'repo' scope\n"
            "  Fine-grained  : 'Contents' read permission on the target repo\n"
        ),
    )
    parser.add_argument(
        "repo",
        metavar="owner/repo",
        help="Repository to inspect, e.g. 'github/github'",
    )
    parser.add_argument(
        "--token",
        metavar="TOKEN",
        default=os.environ.get("GITHUB_TOKEN"),
        help="GitHub personal access token (default: $GITHUB_TOKEN)",
    )
    parser.add_argument(
        "--path",
        metavar="FILE",
        help="Check which owners apply to a specific file path within the repo",
    )

    args = parser.parse_args(argv)

    # Validate owner/repo format
    if "/" not in args.repo or args.repo.count("/") != 1:
        parser.error("Repository must be in 'owner/repo' format, e.g. 'github/github'")

    owner, repo = args.repo.split("/", 1)

    try:
        codeowners_path, content = find_codeowners(owner, repo, args.token)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if content is None:
        print(
            f"No CODEOWNERS file found in {owner}/{repo}.\n"
            "Checked:\n" + "\n".join(f"  - {p}" for p in CODEOWNERS_PATHS),
            file=sys.stderr,
        )
        if not args.token:
            print(
                "\nIf the repository is private, set a GitHub token:\n"
                "  export GITHUB_TOKEN=<your-token>\n"
                "and re-run.  The token needs the 'repo' scope.",
                file=sys.stderr,
            )
        return 1

    rules = parse_codeowners(content)
    print_rules(rules, codeowners_path)

    if args.path:
        owners = owners_for_path(args.path, rules)
        print()
        if owners:
            print(f"Owners for '{args.path}': {', '.join(owners)}")
        else:
            print(f"No owners defined for '{args.path}'.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
