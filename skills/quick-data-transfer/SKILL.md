---
name: quick-data-transfer
description: Transfer, download, copy, or fetch files and folders from configured remote servers to the current laptop. Use when the user wants Codex to select among saved servers, confirm remote/local folders, ask for a target file or folder name, verify the exact remote path, and download it with rsync.
---

# Quick Data Transfer

## Workflow

Use `scripts/server_transfer.py` for server-backed downloads unless the user explicitly asks for a manual command. Run it from the target repository so the server config YAML belongs to that repo.

1. Check for the repo-local `.codex-home/quick-data-transfer.yaml`.
   - If it does not exist, run the script with `--init-config`, tell the user the template was created, and ask them to fill it for quicker transfer.
   - If it contains passwords, require `chmod 600 .codex-home/quick-data-transfer.yaml` before using it.
2. Load configured servers.
   - If multiple servers exist and the user did not name one, ask the user to select the server.
   - If exactly one server exists, use it after stating its configured name.
3. Confirm the remote base folder and local laptop folder.
   - Use configured `remote_base_dir` and `local_base_dir` when present.
   - Ask the user for any missing folder before transferring.
4. Ask the user for the target file or folder name/path.
   - Treat relative targets as exact paths under the confirmed remote base folder.
   - Treat absolute targets as exact remote paths.
   - Do not recursively search by name.
5. Verify the exact remote path exists over SSH.
   - If it does not exist, stop and tell the user the exact path was not found.
6. Download with `rsync`, preserving the remote source basename inside the local base folder.

## Script Usage

Run from the skill folder or pass explicit paths:

```bash
python scripts/server_transfer.py --init-config
python scripts/server_transfer.py --list
python scripts/server_transfer.py --server lab --target scene_001
python scripts/server_transfer.py --server lab --remote-base-dir /data/scans --local-base-dir /home/cynthia/data/scans --target scene_001
```

Use `--dry-run` before a large transfer when the user wants to verify the command. Use `--yes` only when all required values are already provided and no interactive confirmation is needed.

## Security

Prefer SSH keys when available. Plain-text passwords in `.codex-home/quick-data-transfer.yaml` are supported only for convenience; warn the user that this is sensitive local data, keep the file out of version control, and require mode `600`.
