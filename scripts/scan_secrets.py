#!/usr/bin/env python3
"""Secrets Scanner for TinyTravel.
Scans working tree files and optionally git history for accidental secret leaks.
Checks:
  - Anthropic keys (sk-ant-...)
  - TinyFish keys (tf_...)
  - GitHub PATs / tokens (ghp_..., github_pat_...)
  - AWS Access Keys (AKIA...)
  - Google API keys (AIza...)
  - Private RSA/SSH keys (BEGIN PRIVATE KEY...)
Excludes .env (gitignored local secrets), .git, node_modules, .venv, fixtures mock data.
"""
import argparse
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

# Suspicious key regexes
PATTERNS = [
    ("Anthropic API Key", re.compile(r"sk-ant-(?:api\d{2}-)?[a-zA-Z0-9_\-]{30,}")),
    ("TinyFish API Key", re.compile(r"\btf_[a-zA-Z0-9_\-]{20,}\b")),
    ("GitHub Token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{82}\b")),
    ("AWS Access Key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Google API Key", re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b")),
    ("Private Key", re.compile(r"-----BEGIN\s+(?:RSA|OPENSSH|EC|DSA|PGP)?\s*PRIVATE KEY-----")),
]

# Patterns or values that are safe mock tokens/placeholders
SAFE_TOKENS = {
    "sk-ant-dummy",
    "sk-ant-test-key",
    "your_tinyfish_api_key_here",
    "your_anthropic_api_key_here",
    "[REDACTED]",
    "[REDACTED_API_KEY]",
}

IGNORED_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".next",
    ".gemini",
    "scratch",
}

IGNORED_FILES = {
    ".env",
    "tinytravel.db",
    "package-lock.json",
}


def is_safe_match(text: str) -> bool:
    for safe in SAFE_TOKENS:
        if safe in text:
            return True
    return False


def scan_file(path: Path) -> list[tuple[str, int, str]]:
    findings = []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings

    for line_no, line in enumerate(content.splitlines(), start=1):
        for name, pat in PATTERNS:
            matches = pat.findall(line)
            for m in matches:
                match_str = m if isinstance(m, str) else str(m)
                if not is_safe_match(match_str) and not is_safe_match(line):
                    findings.append((name, line_no, match_str[:12] + "..."))
    return findings


def scan_working_tree() -> list[tuple[str, str, int, str]]:
    all_findings = []
    for p in ROOT.rglob("*"):
        if p.is_dir():
            continue
        # Check ignored directories
        if any(ignored in p.parts for ignored in IGNORED_DIRS):
            continue
        if p.name in IGNORED_FILES or p.suffix in (".pyc", ".db", ".png", ".jpg", ".webp", ".ico"):
            continue

        file_findings = scan_file(p)
        for name, line_no, snippet in file_findings:
            rel = p.relative_to(ROOT)
            all_findings.append((str(rel), name, line_no, snippet))
    return all_findings


def scan_git_history() -> list[tuple[str, str, str]]:
    findings = []
    try:
        proc = subprocess.run(
            ["git", "log", "-p", "--all", "-n", "200"],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        if proc.returncode != 0:
            return findings

        current_commit = "HEAD"
        for line in proc.stdout.splitlines():
            if line.startswith("commit "):
                current_commit = line.split()[1][:10]
            if line.startswith("+") and not line.startswith("+++"):
                added_line = line[1:]
                for name, pat in PATTERNS:
                    matches = pat.findall(added_line)
                    for m in matches:
                        match_str = m if isinstance(m, str) else str(m)
                        if not is_safe_match(match_str) and not is_safe_match(added_line):
                            findings.append((current_commit, name, match_str[:12] + "..."))
    except Exception as e:
        print(f"Warning: git log scan encountered: {e}")
    return findings


def main():
    parser = argparse.ArgumentParser(description="Scan repository for leaked secrets and API keys.")
    parser.add_argument("--git-history", action="store_true", help="Also scan git commit log history")
    args = parser.parse_args()

    print("=" * 70)
    print("TinyTravel Secrets Scanner")
    print("=" * 70)

    print("Scanning working directory files...")
    tree_findings = scan_working_tree()

    history_findings = []
    if args.git_history:
        print("Scanning git commit history (last 200 commits)...")
        history_findings = scan_git_history()

    total_issues = len(tree_findings) + len(history_findings)

    if total_issues == 0:
        print("\n[SUCCESS] No secrets or API keys found in codebase.")
        if args.git_history:
            print("[SUCCESS] No secrets or API keys found in git history.")
        print("=" * 70)
        sys.exit(0)
    else:
        print(f"\n[ALERT] Found {total_issues} potential secret leak(s):")
        for file_path, name, line_no, snip in tree_findings:
            print(f"  - {file_path}:{line_no} [{name}]: {snip}")
        for commit, name, snip in history_findings:
            print(f"  - Commit {commit} [{name}]: {snip}")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
