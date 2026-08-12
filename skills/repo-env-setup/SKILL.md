---
name: repo-env-setup
description: Set up a repository environment with large files kept outside the working repo, mirrored external directory structure, symlinks back into the repo, and concise setup.md notes. Use when the user asks Codex to prepare a new repo environment, install/run examples that need large data or model files, keep large files in a specified external folder, preserve repo-relative folder structure, or record successful and failed setup attempts.
---

# Repo Environment Setup

## Workflow

Use this skill to configure a repo so the working tree stays light while large downloaded, generated, or dataset-like files live in an external data root and are linked back into the repo.

1. Inspect the repo first.
   - Read the relevant setup docs, examples, scripts, dependency manifests, and ignored paths before changing files.
   - Identify the command or example the user wants to run and the files it expects.
   - Append 1-3 concise lines to `setup.md` describing what was inspected and any important finding.

2. Confirm the external data root before setup actions.
   - Use the user-provided external folder when given.
   - If it is missing and cannot be inferred safely, ask for the folder before any install, download, generation, move, or symlink action.
   - Only read-only repo inspection may happen before this root is confirmed.
   - Put large files, datasets, model weights, videos, build artifacts that are expensive to recreate, and other bulky runtime assets under this external root.

3. Mirror repo-relative structure externally.
   - For each large path that would normally live at `repo/path/to/item`, place it at `external-root/path/to/item`.
   - Create missing parent directories under the external root so the external tree matches the repo-relative structure requested by the user.
   - Preserve existing user data. Do not overwrite or delete populated paths unless the user explicitly approves.

4. Link external files back into the repo.
   - Symlink from the expected repo path to the mirrored external path.
   - If a repo path already exists, inspect it before acting. Move only bulky local content to the mirrored external path when that is clearly part of the setup and does not discard user edits.
   - Prefer relative symlinks when they remain readable and stable from the repo location; otherwise use absolute symlinks.

5. Install and run incrementally.
   - Install dependencies using the repo's documented tooling.
   - Run the smallest relevant smoke command before attempting heavier examples.
   - When a command fails, record the command, the short failure cause, and the next attempted fix in `setup.md` before continuing.

6. Keep `setup.md` current.
   - After each meaningful setup step, append 1-3 lines covering the action, result, and next implication.
   - Include both successful steps and failed attempts.
   - Keep entries brief and reproducible: include exact commands or paths when they matter.

7. Finish with a verification summary.
   - Confirm the final command that ran successfully, if any.
   - List remaining manual blockers, missing credentials, unavailable data, or commands that still fail.
   - Point to the external data root and key symlinks created.

## Safety Rules

- Treat repo files and external data as user-owned. Inspect before moving, replacing, or linking over existing paths.
- Do not commit large files into the repo unless the user explicitly requests it.
- Do not hide failures. Record failed attempts in `setup.md` with enough detail to avoid repeating them.
- Keep the final repo structure understandable: the expected repo path should exist either as a normal small file/directory or as a symlink to the mirrored external path.
