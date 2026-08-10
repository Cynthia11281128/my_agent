---
name: push-safety-check
description: Scan a Git repository before pushing to find private information that should not be published. Use when the user asks to check a repo for secrets, credentials, tokens, private keys, personal paths, usernames, emails, server IPs/domains, SSH config, database URLs, cloud credentials, or other sensitive information before committing or pushing, and wants findings reported for manual handling choices.
---

# Push Safety Check

## Goal

Check the current repository for private information that should not be pushed, then report every finding in a way that lets the user choose how to handle it. Do not modify files, delete content, rewrite history, or change ignore rules unless the user explicitly chooses a specific follow-up action.

## Core Rules

- Start with `git status --short --branch` to identify branch state, upstream, and staged/unstaged/untracked files.
- Default scan scope is the Git push view:
  - tracked, staged, unstaged, and untracked files from `git ls-files --cached --modified --others --exclude-standard`
  - current branch commits relative to upstream using `@{u}..HEAD`
- If no upstream exists, report that upstream commit comparison is unavailable and continue with the working tree scan.
- Respect `.gitignore`; do not scan ignored files unless the user explicitly asks for a broader scan.
- Treat binary files, very large files, dependency folders, caches, and `.git/` as skipped inputs and mention skips in the summary when relevant.
- Report findings with file, line when available, category, severity, reason, and a masked snippet. Never print a complete secret, private key, token, password, or credential value.
- After reporting, present handling choices per finding or group: keep, redact, remove, move to ignored local config, replace with an example/env reference, rotate credential, or rewrite Git history when the finding exists in commits.

## Workflow

1. Inspect Git state:
   - `git status --short --branch`
   - `git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || true`
2. Run the bundled scanner from the repository root:
   - `python3 skills/push-safety-check/scripts/scan_push_safety.py --repo .`
3. Read the JSON output and summarize it for the user:
   - group by severity, then category
   - call out whether each finding is in the working tree, untracked files, staged/tracked files, or unpushed commits
   - include skipped-file and no-upstream notes
4. Ask the user how to handle the findings. Do not edit anything until the user chooses a concrete action.

## Sensitive Categories

Flag likely push blockers in these categories:

- Secrets and credentials: API keys, tokens, passwords, private keys, cloud access keys, database URLs, credential files, `.env` files.
- Identity and local machine data: emails, usernames, home-directory paths, local absolute paths.
- Infrastructure: server IPs, hostnames/domains in SSH/deploy/database contexts, SSH config, cloud resource identifiers.

Use judgment in the final report: clearly label high-confidence secrets as urgent, and label identity/infrastructure matches as review-needed when they may be intentional documentation.

## Reporting Format

Keep the report concise and actionable:

- `High`: likely valid credential, private key, password, token, or secret-bearing URL.
- `Medium`: credential-like assignment, sensitive file name, SSH/database/cloud host reference, public IP in deploy context.
- `Low`: personal path, username, email, or context-dependent infrastructure clue.

For each finding, include:

```text
severity | category | location | reason | masked snippet
```

If there are no findings, say that no push-blocking private information was detected by the configured checks, and mention that pattern-based scanners can miss secrets.
