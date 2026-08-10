#!/usr/bin/env python3
"""Pattern-based push safety scanner.

This scanner is intentionally conservative about output: findings include masked
snippets so running it does not re-expose complete secrets in chat or logs.
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


MAX_FILE_BYTES = 1_000_000
MAX_FINDINGS = 500
SKIP_DIR_PARTS = {
    ".git",
    ".hg",
    ".svn",
    ".cache",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    "target",
    "__pycache__",
}

SENSITIVE_FILE_RE = re.compile(
    r"(^|/)(\.env(\.|$)|id_(rsa|dsa|ecdsa|ed25519)(\.|$)|"
    r".*(credential|credentials|secret|secrets|token|tokens|password|passwd|pem|p12|pfx|keychain).*)",
    re.I,
)

PATTERNS: list[tuple[str, str, str, re.Pattern[str]]] = [
    ("secret", "high", "Private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("secret", "high", "AWS access key", re.compile(r"\b(A3T[A-Z0-9]|AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("secret", "high", "OpenAI-style API key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("secret", "high", "GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("secret", "high", "Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    (
        "secret",
        "high",
        "Credential in URL",
        re.compile(r"\b[a-z][a-z0-9+.-]{2,}://[^/\s:@]+:[^/\s:@]{6,}@[^/\s]+", re.I),
    ),
    (
        "secret",
        "medium",
        "Credential assignment",
        re.compile(
            r"(?i)\b(api[_-]?key|access[_-]?key|secret|token|password|passwd|pwd|credential|private[_-]?key)\b"
            r"\s*[:=]\s*['\"]?([^'\"\s#]{8,})"
        ),
    ),
    (
        "identity",
        "low",
        "Email address",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ),
    (
        "identity",
        "low",
        "Home directory path",
        re.compile(r"(?:(?:/Users|/home)/[A-Za-z0-9._-]+|[A-Za-z]:\\Users\\[A-Za-z0-9._-]+)"),
    ),
    (
        "infrastructure",
        "medium",
        "IP address in infrastructure context",
        re.compile(
            r"(?i)\b(?:ssh|scp|sftp|rsync|host|hostname|server|deploy|database|postgres|mysql|redis|mongo|endpoint)"
            r"\b.{0,80}\b(?:\d{1,3}\.){3}\d{1,3}\b"
        ),
    ),
    (
        "infrastructure",
        "medium",
        "Host/domain in infrastructure context",
        re.compile(
            r"(?i)\b(?:ssh|scp|sftp|rsync|host|hostname|server|deploy|database|postgres|mysql|redis|mongo|endpoint)"
            r"\b.{0,80}\b([A-Za-z0-9-]+\.)+[A-Za-z]{2,}\b"
        ),
    ),
    ("infrastructure", "medium", "SSH config host", re.compile(r"(?i)^\s*(HostName|IdentityFile|User)\s+\S+")),
]

TOKEN_RE = re.compile(r"\b[A-Za-z0-9_+/\-]{24,}={0,2}\b")


@dataclass
class Finding:
    source: str
    path: str
    line: int | None
    category: str
    severity: str
    reason: str
    snippet: str


def run_git(repo: Path, args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def mask_text(text: str) -> str:
    def mask_value(value: str) -> str:
        if len(value) <= 8:
            return "*" * len(value)
        return f"{value[:4]}...{value[-4:]}"

    def mask_match(match: re.Match[str]) -> str:
        return mask_value(match.group(0))

    masked = text.strip()
    masked = re.sub(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "-----BEGIN ... PRIVATE KEY-----", masked)
    masked = re.sub(r"([:=]\s*['\"]?)([^'\"\s#]{8,})", lambda m: m.group(1) + mask_value(m.group(2)), masked)
    masked = re.sub(r"(?<=://)([^/\s:@]+):([^/\s:@]{6,})@", lambda m: f"{m.group(1)}:****@", masked)
    masked = TOKEN_RE.sub(mask_match, masked)
    if len(masked) > 180:
        masked = masked[:177] + "..."
    return masked


def entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = {char: value.count(char) for char in set(value)}
    return -sum((count / len(value)) * math.log2(count / len(value)) for count in counts.values())


def is_probably_binary(data: bytes) -> bool:
    if b"\0" in data:
        return True
    try:
        data.decode("utf-8")
        return False
    except UnicodeDecodeError:
        return True


def should_skip_path(path: str) -> bool:
    parts = set(Path(path).parts)
    return bool(parts & SKIP_DIR_PARTS)


def listed_files(repo: Path) -> list[str]:
    proc = run_git(repo, ["ls-files", "-z", "--cached", "--modified", "--others", "--exclude-standard"])
    return sorted({p for p in proc.stdout.split("\0") if p})


def add_finding(findings: list[Finding], finding: Finding) -> None:
    if len(findings) < MAX_FINDINGS:
        findings.append(finding)


def scan_line(findings: list[Finding], source: str, path: str, line_no: int | None, line: str) -> None:
    matched_secret = False
    matched_high_secret = False
    for category, severity, reason, pattern in PATTERNS:
        if pattern.search(line):
            if reason == "Credential assignment" and matched_high_secret:
                continue
            matched_secret = matched_secret or category == "secret"
            matched_high_secret = matched_high_secret or (category == "secret" and severity == "high")
            add_finding(
                findings,
                Finding(source, path, line_no, category, severity, reason, mask_text(line)),
            )

    if matched_secret:
        return

    for token in TOKEN_RE.findall(line):
        if entropy(token) >= 4.2 and any(c.isalpha() for c in token) and any(c.isdigit() for c in token):
            add_finding(
                findings,
                Finding(source, path, line_no, "secret", "medium", "High-entropy token-like value", mask_text(line)),
            )
            break


def scan_file(repo: Path, rel_path: str, findings: list[Finding], skipped: list[dict[str, str]]) -> None:
    if should_skip_path(rel_path):
        skipped.append({"path": rel_path, "reason": "skipped directory"})
        return

    path = repo / rel_path
    if not path.is_file():
        return

    try:
        size = path.stat().st_size
    except OSError as exc:
        skipped.append({"path": rel_path, "reason": f"stat failed: {exc}"})
        return

    if size > MAX_FILE_BYTES:
        skipped.append({"path": rel_path, "reason": f"larger than {MAX_FILE_BYTES} bytes"})
        return

    try:
        data = path.read_bytes()
    except OSError as exc:
        skipped.append({"path": rel_path, "reason": f"read failed: {exc}"})
        return

    if is_probably_binary(data):
        skipped.append({"path": rel_path, "reason": "binary file"})
        return

    text = data.decode("utf-8", errors="replace")
    if SENSITIVE_FILE_RE.search(rel_path):
        add_finding(
            findings,
            Finding("working-tree", rel_path, None, "secret", "medium", "Sensitive filename", mask_text(rel_path)),
        )

    for line_no, line in enumerate(text.splitlines(), 1):
        scan_line(findings, "working-tree", rel_path, line_no, line)


def parse_patch_for_added_lines(patch: str, source: str, findings: list[Finding]) -> None:
    current_path = ""
    new_line = None
    for raw in patch.splitlines():
        if raw.startswith("+++ b/"):
            current_path = raw[6:]
            continue
        if raw.startswith("@@"):
            match = re.search(r"\+(\d+)", raw)
            new_line = int(match.group(1)) if match else None
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            content = raw[1:]
            scan_line(findings, source, current_path or "<patch>", new_line, content)
            if new_line is not None:
                new_line += 1
        elif raw.startswith("-") and not raw.startswith("---"):
            continue
        elif new_line is not None:
            new_line += 1


def upstream_name(repo: Path) -> str | None:
    proc = run_git(repo, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], check=False)
    if proc.returncode != 0:
        return None
    name = proc.stdout.strip()
    return name or None


def scan_unpushed_commits(repo: Path, findings: list[Finding], notes: list[str]) -> None:
    upstream = upstream_name(repo)
    if not upstream:
        notes.append("No upstream configured; skipped unpushed commit comparison.")
        return

    rev_range = f"{upstream}..HEAD"
    count = run_git(repo, ["rev-list", "--count", rev_range], check=False)
    if count.returncode != 0 or count.stdout.strip() in {"", "0"}:
        return

    patch = run_git(
        repo,
        ["log", "--format=commit %H", "--patch", "--unified=0", "--no-ext-diff", rev_range],
        check=False,
    )
    if patch.returncode != 0:
        notes.append(f"Could not scan unpushed commits: {patch.stderr.strip()}")
        return
    parse_patch_for_added_lines(patch.stdout, "unpushed-commit", findings)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan a Git repo for private information before push.")
    parser.add_argument("--repo", default=".", help="Repository root to scan.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    repo = Path(args.repo).resolve()
    if not (repo / ".git").exists():
        print(json.dumps({"error": f"{repo} is not a Git repository"}, indent=2))
        return 2

    findings: list[Finding] = []
    skipped: list[dict[str, str]] = []
    notes: list[str] = []

    try:
        files = listed_files(repo)
    except subprocess.CalledProcessError as exc:
        print(json.dumps({"error": exc.stderr.strip() or "git ls-files failed"}, indent=2))
        return 2

    for rel_path in files:
        scan_file(repo, rel_path, findings, skipped)

    scan_unpushed_commits(repo, findings, notes)

    result = {
        "repo": str(repo),
        "scanned_files": len(files),
        "findings_count": len(findings),
        "findings_truncated": len(findings) >= MAX_FINDINGS,
        "findings": [asdict(finding) for finding in findings],
        "skipped": skipped,
        "notes": notes,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
