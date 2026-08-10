---
name: connect-folder-to-github
description: Connect the current local folder to a remote GitHub repository. Use when the user asks to link, attach, bind, connect, or publish the current directory to GitHub; add or fix a GitHub remote; initialize Git for the current folder; set origin or upstream; or prepare a local project folder so it tracks a GitHub repo.
---

# Connect Folder To GitHub

## Goal

Connect the current local folder to a GitHub repository while preserving local files and Git history. Establish the correct Git remote and branch tracking state, then push only when the user has clearly requested it or confirms it.

## Core Rules

- Treat the current working directory as the folder to connect unless the user gives another path.
- Protect local files and existing Git history. Do not reset, clean, overwrite, or discard changes.
- Ask for the target GitHub repository URL or `owner/repo` when it is not provided or cannot be inferred safely.
- If the folder is already a Git repository, inspect it before changing remotes.
- If `origin` already exists and points somewhere else, stop and ask before replacing it.
- If the target GitHub repository may contain existing commits, stop and ask whether to merge histories, push a new branch, or use a fresh empty repo.
- Do not push code, create a repository, change visibility, or force-push unless the user explicitly requests that action.
- Prefer SSH or HTTPS remote format based on the URL the user provided. Do not silently switch protocols unless needed and explained.
- Respect sandbox, network, and credential limits. If GitHub access is blocked, report the exact blocker and provide the next required input.

## Workflow

1. Confirm the local folder and target GitHub repository:

```bash
pwd
git rev-parse --show-toplevel
git status --short
git remote -v
git branch --show-current
```

2. If `git rev-parse --show-toplevel` fails, initialize Git in the current folder only after confirming this is the intended project root:

```bash
git init
```

3. Inspect existing repository state:

- Current branch name.
- Whether the worktree has uncommitted changes.
- Existing remotes and whether `origin` already exists.
- Whether commits already exist locally.

Useful commands:

```bash
git status --short
git branch --show-current
git remote -v
git rev-list --count HEAD
```

4. Normalize the target GitHub remote from user input:

- `https://github.com/OWNER/REPO.git`
- `git@github.com:OWNER/REPO.git`
- `OWNER/REPO` converted to a GitHub remote only after confirming protocol preference or using the user's existing convention.

5. Add or update the remote:

```bash
git remote add origin <github-remote-url>
```

Use this only after confirmation when replacing an existing mismatched remote:

```bash
git remote set-url origin <github-remote-url>
```

6. Verify the remote:

```bash
git remote -v
git ls-remote origin
```

If `git ls-remote origin` fails, identify whether the issue is network access, authentication, repository existence, or protocol mismatch.

7. Prepare branch tracking when pushing is requested:

```bash
git branch --show-current
git push -u origin <branch>
```

If there is no current branch name, ask what branch to use or use the repository's established default branch only when it is clear from context.

## GitHub Repository Creation

If the target repository does not exist:

- Do not create it unless the user explicitly asks to create a GitHub repo.
- Ask for required creation details: repository name, owner or organization, visibility, and whether to initialize it empty.
- Prefer creating an empty remote repository when connecting an existing local folder, so local history can push cleanly.
- After creation, add it as `origin` and verify with `git ls-remote origin`.

## Existing Remote Handling

When `origin` already exists:

- If it matches the target, keep it and continue.
- If it differs from the target, report both URLs and ask whether to replace it.
- If another remote already points to the target, ask whether to keep that remote name or rename/add `origin`.

Never silently replace remotes.

## Existing Remote History Handling

When the GitHub repository is not empty:

- Fetching or pushing may require reconciling unrelated histories.
- Stop and ask whether the user wants to pull/merge remote history, push the local branch under a new branch name, or use a different empty repo.
- Do not use `--force`, `--force-with-lease`, or `--allow-unrelated-histories` without explicit instruction.

## Final Report

After connecting, report:

- Local folder path.
- Git repository root.
- Current branch.
- `origin` URL.
- Whether branch upstream is set.
- Whether anything was pushed.
- Any remaining manual step, credential issue, or confirmation needed.

Keep the report concise and include exact commands only when the user needs to repeat them.
