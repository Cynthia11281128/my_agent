---
name: vps-data-download
description: Download, copy, fetch, or transfer exact files and folders from a configured source server to the current laptop or current machine through a configured VPS relay. Use when the user wants Codex to verify an exact server path, inspect target file characteristics, transfer server data to a VPS first, then download from the VPS to local while preserving folder structure.
---

# VPS Data Download

## Workflow

Use `scripts/vps_data_download.py` for relay-backed downloads unless the user explicitly asks for a manual command. Run it from the target repository so the route config YAML belongs to that repo.

1. Check for the repo-local `.codex-home/vps-data-download.yaml`.
   - If it does not exist, run the script with `--init-config`, tell the user the template was created, and ask them to fill it for quicker transfer.
   - If it contains passwords, require `chmod 600 .codex-home/vps-data-download.yaml` before using it.
2. Load configured routes.
   - If multiple routes exist and the user did not name one, ask the user to select the route.
   - If exactly one route exists, use it after stating its configured name.
3. Confirm the server source folder, VPS relay folder, and local laptop folder.
   - Use configured `server.remote_base_dir`, `vps.relay_base_dir`, and `local_base_dir` when present.
   - Ask the user for any missing folder before transferring.
4. Ask the user for the target file or folder name/path.
   - Treat relative targets as exact paths under the confirmed server source folder.
   - Treat absolute targets as exact source-server paths.
   - Do not recursively search by name.
5. Analyze the exact source-server target before transferring.
   - Print whether it exists, whether it is a directory, file/dir counts, total bytes, median file size, small-file count, compressed-like file count, and top extensions.
   - Use `transfer_strategy: auto` unless the user explicitly requests `rsync`, `rsync-compress`, `archive`, or `archive-compress`.
   - Prefer archive transfer for many small files. Prefer compression only when the target does not already look compressed.
   - Use `--analyze-only` when the user wants to inspect the true file situation and selected strategy without transferring.
6. Preserve relative server folder structure locally.
   - A relative target such as `insta360/r04/room_segmentation` must land under `LOCAL_BASE/insta360/r04/room_segmentation`.
   - An absolute target preserves only the source basename under the local base folder.
7. If the selected route has `preflight: true`, run preflight checks before transferring.
   - Check local-to-server SSH, required server-side tools, and the exact source path.
   - Check server-to-VPS SSH, required VPS-side tools, and relay folder writability.
   - Check local-to-VPS SSH, VPS-side `rsync`, local folder writability, and local archive tools when needed.
   - Use `--skip-preflight` only when the user explicitly wants to bypass this configured check.
8. Verify the exact source-server path exists over SSH.
   - If it does not exist, stop and tell the user the exact path was not found.
9. Transfer with the selected strategy.
   - `rsync`: push the exact source path from server to VPS, then download it from VPS to local with resumable `rsync`.
   - `rsync-compress`: same as `rsync`, with `-z` compression on both hops.
   - `archive`: stream `tar` from server to a VPS archive, download the archive, extract it locally, then clean the temporary archive files after successful extraction.
   - `archive-compress`: same as `archive`, using `pigz` first and `gzip` as fallback on the source server.
10. Leave rsync-style VPS relay copies in place unless the user explicitly asks for cleanup. Archive relay files are temporary and should be cleaned after successful extraction.

## Script Usage

Run from the skill folder or pass explicit paths:

```bash
python scripts/vps_data_download.py --init-config
python scripts/vps_data_download.py --list
python scripts/vps_data_download.py --route lab-vps --target scene_001
python scripts/vps_data_download.py --route lab-vps --server-base-dir /data/scans --vps-base-dir /tmp/relay/scans --local-base-dir /home/cynthia/data/scans --target scene_001
python scripts/vps_data_download.py --route lab-vps --target scene_001 --analyze-only
python scripts/vps_data_download.py --route lab-vps --target scene_001 --strategy archive
python scripts/vps_data_download.py --route lab-vps --target scene_001 --preflight-only
python scripts/vps_data_download.py --route lab-vps --target scene_001 --skip-preflight
python scripts/vps_data_download.py --route lab-vps --target scene_001 --cleanup-vps-copy
```

Use `--dry-run` before a large transfer when the user wants to verify the command. Use `--yes` only when all required values are already provided and no interactive confirmation is needed.

Set `transfer_strategy: auto` on a route to inspect the real target shape and choose the fastest available strategy. Use `--strategy` to override it for a single run.

Set `preflight: true` on a route to check all SSH channels, required remote tools, relay writability, source path existence, and local folder writability before transfer. Use `--preflight-only` to run those checks without transferring.

Use `--cleanup-vps-copy` only when the user explicitly asks to remove the VPS relay copy after the local download succeeds.

## Transfer Topology

The default first hop is server-push-to-VPS: Codex SSHes from local to the source server, then pushes the target into the VPS relay folder with the selected strategy. The source server must be able to SSH to the VPS, usually with an SSH key already configured on the source server.

The second hop is VPS-to-local: Codex runs local `rsync` from the VPS relay path into the local base folder. Archive strategies download a single archive and extract it under the local base folder so relative target paths keep the same folder structure as the server.

## Security

Prefer SSH keys when available. Plain-text passwords in `.codex-home/vps-data-download.yaml` are supported only for local-to-server and local-to-VPS SSH convenience; warn the user that this is sensitive local data, keep the file out of version control, and require mode `600`. Do not put the source server's VPS password in the config; configure server-to-VPS SSH keys instead.
