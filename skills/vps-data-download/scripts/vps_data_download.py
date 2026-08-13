#!/usr/bin/env python3
"""Download an exact server file or folder through a configured VPS relay."""

from __future__ import annotations

import argparse
import json
import getpass
import os
import shlex
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only on missing dependency
    yaml = None


SKILL_DIR = Path(__file__).resolve().parents[1]
ASSETS_DIR = SKILL_DIR / "assets"
DEFAULT_CONFIG_PATH = Path.cwd() / ".codex-home" / "vps-data-download.yaml"
TEMPLATE_CONFIG_PATH = ASSETS_DIR / "vps_data_download_config.template.yaml"
TRANSFER_STRATEGIES = {"auto", "rsync", "rsync-compress", "archive", "archive-compress"}
COMPRESSED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".npz", ".zip", ".gz", ".zst", ".mp4", ".mov", ".avi"}


@dataclass(frozen=True)
class TargetAnalysis:
    """Summarize the exact source target on the server."""
    exists: bool
    is_dir: bool
    file_count: int
    dir_count: int
    total_bytes: int
    median_bytes: int
    small_file_count: int
    compressed_file_count: int
    top_extensions: list[tuple[str, int]]


@dataclass(frozen=True)
class TransferPaths:
    """Hold resolved server, relay, and local transfer paths."""
    server_target: str
    vps_target: str
    vps_destination_dir: str
    local_destination_dir: Path
    local_extract_dir: Path
    relative_target: PurePosixPath | None


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--init-config", action="store_true")
    parser.add_argument("--list", action="store_true", dest="list_routes")
    parser.add_argument("--route", help="Configured route name.")
    parser.add_argument("--server-base-dir", help="Source server base directory.")
    parser.add_argument("--vps-base-dir", help="VPS relay base directory.")
    parser.add_argument("--local-base-dir", type=Path, help="Local destination directory.")
    parser.add_argument("--target", help="Exact source-server file/folder path or name.")
    parser.add_argument("--strategy", choices=sorted(TRANSFER_STRATEGIES), help="Transfer strategy override.")
    parser.add_argument("--analyze-only", action="store_true", help="Analyze the target and recommended strategy without transferring.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--preflight-only", action="store_true", help="Check all transfer channels and exit.")
    parser.add_argument("--skip-preflight", action="store_true", help="Skip route-configured preflight checks.")
    parser.add_argument("--yes", action="store_true", help="Do not prompt for confirmation.")
    parser.add_argument("--cleanup-vps-copy", action="store_true", help="Remove the VPS relay copy after download.")
    return parser.parse_args()


def copy_template_config(config_path: Path) -> None:
    """Create a user-editable config from the bundled template."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(TEMPLATE_CONFIG_PATH, config_path)
    config_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    print(f"Created config template: {config_path}")
    print("Fill it with route details for quicker transfers, then keep it private with chmod 600.")


def load_config(config_path: Path) -> dict[str, Any]:
    """Load the YAML route config."""
    with config_path.open("r", encoding="utf-8") as file:
        text = file.read()
    if yaml is None:
        return parse_simple_route_config(text, config_path)
    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a YAML mapping: {config_path}")
    return data


def parse_simple_route_config(text: str, config_path: Path) -> dict[str, Any]:
    """Parse the bundled route config shape without PyYAML."""
    routes: list[dict[str, Any]] = []
    current_route: dict[str, Any] | None = None
    current_section: str | None = None
    in_routes = False
    for raw_line in text.splitlines():
        line_without_comment = raw_line.split("#", 1)[0].rstrip()
        if not line_without_comment.strip():
            continue
        indent = len(line_without_comment) - len(line_without_comment.lstrip(" "))
        stripped = line_without_comment.strip()
        if stripped == "routes:":
            in_routes = True
            continue
        if not in_routes:
            continue
        if stripped.startswith("- "):
            current_route = {}
            current_section = None
            routes.append(current_route)
            key, value = split_config_key_value(stripped[2:], config_path)
            if key:
                current_route[key] = parse_scalar_config_value(value)
            continue
        if current_route is None:
            raise ValueError(f"Expected a route list item before '{stripped}' in {config_path}")
        if indent == 4 and stripped.endswith(":"):
            current_section = stripped[:-1]
            current_route[current_section] = {}
            continue
        key, value = split_config_key_value(stripped, config_path)
        if indent >= 6 and current_section:
            current_route[current_section][key] = parse_scalar_config_value(value)
        else:
            current_section = None
            current_route[key] = parse_scalar_config_value(value)
    return {"routes": routes}


def split_config_key_value(line: str, config_path: Path) -> tuple[str, str]:
    """Split a simple YAML key-value line."""
    if ":" not in line:
        raise ValueError(f"Expected key: value in {config_path}: {line}")
    key, value = line.split(":", 1)
    return key.strip(), value.strip()


def parse_scalar_config_value(value: str) -> Any:
    """Parse a simple YAML scalar value."""
    if value in {'""', "''"}:
        return ""
    lowered = value.lower()
    if lowered in {"true", "yes"}:
        return True
    if lowered in {"false", "no"}:
        return False
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    if value.isdigit():
        return int(value)
    return value


def parse_bool_config_value(value: Any, default: bool) -> bool:
    """Parse a boolean route config value."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    lowered = str(value).strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Expected a boolean config value, got: {value}")


def parse_strategy_config_value(value: Any, default: str) -> str:
    """Parse a transfer strategy config value."""
    strategy = str(value or default).strip()
    if strategy not in TRANSFER_STRATEGIES:
        names = ", ".join(sorted(TRANSFER_STRATEGIES))
        raise ValueError(f"Expected transfer strategy to be one of {names}, got: {strategy}")
    return strategy


def get_routes(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Return validated route entries from config."""
    routes = config.get("routes", [])
    if not isinstance(routes, list):
        raise ValueError("Config field 'routes' must be a list.")
    typed_routes = [route for route in routes if isinstance(route, dict)]
    if len(typed_routes) != len(routes):
        raise ValueError("Every route entry must be a mapping.")
    return typed_routes


def require_private_config_if_passwords(config_path: Path, routes: list[dict[str, Any]]) -> None:
    """Require chmod 600 when stored passwords are present."""
    has_password = False
    for route in routes:
        server = get_mapping(route, "server")
        vps = get_mapping(route, "vps")
        has_password = has_password or bool(str(server.get("password") or ""))
        has_password = has_password or bool(str(vps.get("password") or ""))
    if not has_password:
        return
    mode = stat.S_IMODE(config_path.stat().st_mode)
    if mode != 0o600:
        raise PermissionError(f"{config_path} contains passwords and must be chmod 600; current mode is {mode:o}.")


def choose_route(routes: list[dict[str, Any]], route_name: str | None) -> dict[str, Any]:
    """Select a configured route by name or prompt."""
    if route_name:
        for route in routes:
            if route.get("name") == route_name:
                return route
        names = ", ".join(str(route.get("name")) for route in routes)
        raise ValueError(f"Route '{route_name}' was not found. Available routes: {names}")
    if len(routes) == 1:
        return routes[0]
    if not routes:
        raise ValueError("No routes are configured.")
    print("Configured routes:")
    for index, route in enumerate(routes, start=1):
        server = get_mapping(route, "server")
        vps = get_mapping(route, "vps")
        print(f"{index}. {route.get('name')} ({server.get('host')} -> {vps.get('host')})")
    while True:
        selected = input("Select route number: ").strip()
        if selected.isdigit() and 1 <= int(selected) <= len(routes):
            return routes[int(selected) - 1]
        print("Enter a valid route number.")


def get_mapping(data: dict[str, Any], field_name: str) -> dict[str, Any]:
    """Return a nested mapping field."""
    value = data.get(field_name, {})
    if not isinstance(value, dict):
        raise ValueError(f"Field '{field_name}' must be a mapping.")
    return value


def require_field(data: dict[str, Any], field_name: str, owner: str) -> str:
    """Return a required text field."""
    value = str(data.get(field_name) or "").strip()
    if not value:
        raise ValueError(f"{owner} is missing required field: {field_name}")
    return value


def prompt_text(current: str | None, label: str) -> str:
    """Return a provided value or ask for one."""
    if current:
        return current
    value = input(f"{label}: ").strip()
    if not value:
        raise ValueError(f"{label} is required.")
    return value


def prompt_path(current: Path | None, label: str) -> Path:
    """Return a provided path or ask for one."""
    if current:
        return current.expanduser()
    value = input(f"{label}: ").strip()
    if not value:
        raise ValueError(f"{label} is required.")
    return Path(value).expanduser()


def path_from_route(route: dict[str, Any], field_name: str) -> Path | None:
    """Return an optional path field from a route entry."""
    value = str(route.get(field_name) or "").strip()
    if not value:
        return None
    return Path(value).expanduser()


def build_server_target(server_base_dir: str, target: str) -> str:
    """Build the exact source-server target path."""
    target_path = target.strip()
    if not target_path:
        raise ValueError("Target file/folder name is required.")
    if target_path.startswith("/"):
        return target_path
    return str(PurePosixPath(server_base_dir) / target_path)


def build_relative_target_path(target: str) -> PurePosixPath | None:
    """Return a safe relative target path when target is relative."""
    target_path = target.strip()
    if target_path.startswith("/"):
        return None
    relative_path = PurePosixPath(target_path)
    if any(part in {"", ".", ".."} for part in relative_path.parts):
        raise ValueError(f"Relative target path must not contain empty, '.', or '..' parts: {target}")
    return relative_path


def build_vps_target(vps_base_dir: str, server_target: str, relative_target: PurePosixPath | None) -> str:
    """Build the VPS relay target path."""
    if relative_target is not None:
        return str(PurePosixPath(vps_base_dir) / relative_target)
    basename = PurePosixPath(server_target.rstrip("/")).name
    if not basename:
        raise ValueError(f"Could not determine basename for source path: {server_target}")
    return str(PurePosixPath(vps_base_dir) / basename)


def build_parent_posix_dir(posix_path: str) -> str:
    """Return the parent directory of a POSIX path."""
    parent = PurePosixPath(posix_path).parent
    if str(parent) in {"", "."}:
        raise ValueError(f"Could not determine parent directory for path: {posix_path}")
    return str(parent)


def build_local_destination_dir(local_base_dir: Path, relative_target: PurePosixPath | None) -> Path:
    """Build the local rsync destination directory."""
    if relative_target is None or str(relative_target.parent) == ".":
        return local_base_dir
    return local_base_dir / Path(*relative_target.parent.parts)


def build_archive_vps_target(vps_base_dir: str, server_target: str, relative_target: PurePosixPath | None, compressed: bool) -> str:
    """Build the VPS archive relay file path."""
    suffix = ".tar.gz" if compressed else ".tar"
    if relative_target is not None:
        return str(PurePosixPath(vps_base_dir) / relative_target.parent / (relative_target.name + suffix))
    basename = PurePosixPath(server_target.rstrip("/")).name
    if not basename:
        raise ValueError(f"Could not determine basename for source path: {server_target}")
    return str(PurePosixPath(vps_base_dir) / (basename + suffix))


def build_transfer_paths(
    server_base_dir: str,
    vps_base_dir: str,
    local_base_dir: Path,
    target: str,
    strategy: str,
) -> TransferPaths:
    """Resolve server, relay, and local transfer paths."""
    relative_target = build_relative_target_path(target)
    server_target = build_server_target(server_base_dir, target)
    if strategy.startswith("archive"):
        vps_target = build_archive_vps_target(vps_base_dir, server_target, relative_target, strategy == "archive-compress")
        local_destination_dir = local_base_dir / ".vps-data-download-tmp"
        local_extract_dir = local_base_dir
    else:
        vps_target = build_vps_target(vps_base_dir, server_target, relative_target)
        local_destination_dir = build_local_destination_dir(local_base_dir, relative_target)
        local_extract_dir = local_destination_dir
    return TransferPaths(
        server_target=server_target,
        vps_target=vps_target,
        vps_destination_dir=build_parent_posix_dir(vps_target),
        local_destination_dir=local_destination_dir,
        local_extract_dir=local_extract_dir,
        relative_target=relative_target,
    )


def build_local_archive_path(local_archive_dir: Path, vps_archive_target: str) -> Path:
    """Build the local temporary archive path."""
    return local_archive_dir / PurePosixPath(vps_archive_target).name


def get_password(host_config: dict[str, Any], owner: str) -> str:
    """Return configured or prompted password text."""
    password = str(host_config.get("password") or "")
    if password:
        return password
    if str(host_config.get("password_prompt") or "").lower() in {"1", "true", "yes"}:
        return getpass.getpass(f"Password for {owner}: ")
    return ""


def ssh_prefix(password: str) -> list[str]:
    """Return sshpass command prefix when password auth is needed."""
    if not password:
        return []
    if shutil.which("sshpass") is None:
        raise RuntimeError("sshpass is required for configured passwords but is not installed.")
    return ["sshpass", "-e"]


def run_checked(command: list[str], dry_run: bool = False, password: str = "") -> None:
    """Run a command after printing it."""
    print(shlex.join(command))
    if dry_run:
        return
    env = os.environ.copy()
    if password:
        env["SSHPASS"] = password
    subprocess.run(command, check=True, env=env)


def run_captured(command: list[str], password: str = "") -> str:
    """Run a command and return stdout text."""
    print(shlex.join(command))
    env = os.environ.copy()
    if password:
        env["SSHPASS"] = password
    result = subprocess.run(command, check=True, env=env, stdout=subprocess.PIPE, text=True)
    return result.stdout


def run_preflight_command(label: str, command: list[str], password: str = "", dry_run: bool = False) -> None:
    """Run a preflight command with a channel-specific error."""
    try:
        run_checked(command, dry_run=dry_run, password=password)
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f"Preflight failed: {label}: {shlex.join(command)}") from error


def ssh_local_command(host_config: dict[str, Any], owner: str, remote_command: str) -> list[str]:
    """Build a local SSH command."""
    host = require_field(host_config, "host", owner)
    username = require_field(host_config, "username", owner)
    port = str(host_config.get("port") or 22)
    return ["ssh", "-p", port, f"{username}@{host}", remote_command]


def analyze_server_target(server: dict[str, Any], server_password: str, server_target: str) -> TargetAnalysis:
    """Analyze the exact source target on the server."""
    script = r"""
import json
import sys
from collections import Counter
from pathlib import Path

root = Path(sys.argv[1])
extensions = Counter()
sizes = []
dir_count = 0
total = 0
compressed_extensions = {'.jpg', '.jpeg', '.png', '.npz', '.zip', '.gz', '.zst', '.mp4', '.mov', '.avi'}
compressed_count = 0
if root.exists():
    paths = root.rglob('*') if root.is_dir() else [root]
    for path in paths:
        try:
            if path.is_dir():
                dir_count += 1
                continue
            if not path.is_file():
                continue
            size = path.stat().st_size
        except OSError:
            continue
        sizes.append(size)
        total += size
        suffix = path.suffix.lower() or '<none>'
        extensions[suffix] += 1
        if suffix in compressed_extensions:
            compressed_count += 1
sizes.sort()
median = sizes[len(sizes) // 2] if sizes else 0
small = sum(1 for size in sizes if size < 65536)
print(json.dumps({
    'exists': root.exists(),
    'is_dir': root.is_dir(),
    'file_count': len(sizes),
    'dir_count': dir_count,
    'total_bytes': total,
    'median_bytes': median,
    'small_file_count': small,
    'compressed_file_count': compressed_count,
    'top_extensions': extensions.most_common(20),
}))
"""
    remote_command = "python3 -c " + shlex_quote(script) + " " + shlex_quote(server_target)
    command = ssh_prefix(server_password) + ssh_local_command(server, "server", remote_command)
    data = json.loads(run_captured(command, password=server_password))
    return TargetAnalysis(
        exists=bool(data["exists"]),
        is_dir=bool(data["is_dir"]),
        file_count=int(data["file_count"]),
        dir_count=int(data["dir_count"]),
        total_bytes=int(data["total_bytes"]),
        median_bytes=int(data["median_bytes"]),
        small_file_count=int(data["small_file_count"]),
        compressed_file_count=int(data["compressed_file_count"]),
        top_extensions=[(str(ext), int(count)) for ext, count in data["top_extensions"]],
    )


def choose_transfer_strategy(requested_strategy: str, analysis: TargetAnalysis) -> str:
    """Choose the transfer strategy from the request and target analysis."""
    if requested_strategy != "auto":
        return requested_strategy
    if analysis.file_count > 1000 or analysis.median_bytes < 65536:
        compressed_ratio = analysis.compressed_file_count / max(analysis.file_count, 1)
        return "archive" if compressed_ratio > 0.5 else "archive-compress"
    if analysis.total_bytes > 32 * 1024 * 1024 and analysis.compressed_file_count < analysis.file_count / 2:
        return "rsync-compress"
    return "rsync"


def print_target_analysis(analysis: TargetAnalysis, requested_strategy: str, selected_strategy: str) -> None:
    """Print the target analysis and selected strategy."""
    print("Target analysis:")
    print(f"  exists: {analysis.exists}")
    print(f"  is_dir: {analysis.is_dir}")
    print(f"  files: {analysis.file_count}")
    print(f"  dirs: {analysis.dir_count}")
    print(f"  bytes: {analysis.total_bytes}")
    print(f"  median_file_bytes: {analysis.median_bytes}")
    print(f"  small_files_lt_64k: {analysis.small_file_count}")
    print(f"  compressed_like_files: {analysis.compressed_file_count}")
    print(f"  top_extensions: {analysis.top_extensions}")
    print(f"Requested strategy: {requested_strategy}")
    print(f"Selected strategy: {selected_strategy}")


def choose_server_archive_compressor(server: dict[str, Any], server_password: str, strategy: str) -> str:
    """Choose the source-server compressor for archive streaming."""
    if strategy != "archive-compress":
        return ""
    remote_command = "if command -v pigz >/dev/null; then echo pigz; elif command -v gzip >/dev/null; then echo gzip; else echo ''; fi"
    command = ssh_prefix(server_password) + ssh_local_command(server, "server", remote_command)
    compressor = run_captured(command, password=server_password).strip()
    if compressor not in {"pigz", "gzip"}:
        raise RuntimeError("archive-compress requires pigz or gzip on the source server.")
    print(f"Archive compressor: {compressor}")
    return compressor


def build_archive_compressor_pipeline(archive_compressor: str) -> str:
    """Build the remote archive compression pipeline."""
    if archive_compressor == "pigz":
        return " | pigz -1 -c"
    if archive_compressor == "gzip":
        return " | gzip -1 -c"
    return ""


def run_preflight_checks(
    server: dict[str, Any],
    vps: dict[str, Any],
    server_password: str,
    vps_password: str,
    server_target: str,
    vps_base_dir: str,
    local_base_dir: Path,
    strategy: str,
    archive_compressor: str,
    dry_run: bool,
) -> None:
    """Check all SSH, rsync, and destination channels."""
    print("Running transfer preflight checks:")
    verify_local_to_server_channel(server, server_password, server_target, strategy, archive_compressor, dry_run)
    verify_server_to_vps_channel(server, vps, server_password, vps_base_dir, strategy, dry_run)
    verify_local_to_vps_channel(vps, vps_password, vps_base_dir, dry_run)
    verify_local_base_dir_writable(local_base_dir, dry_run)
    verify_local_archive_tools(strategy)
    if dry_run:
        print("Preflight commands printed.")
        return
    print("Preflight checks passed.")


def verify_local_to_server_channel(
    server: dict[str, Any],
    server_password: str,
    server_target: str,
    strategy: str,
    archive_compressor: str,
    dry_run: bool,
) -> None:
    """Check local SSH access to the source server."""
    tool_check = "command -v rsync >/dev/null"
    if strategy.startswith("archive"):
        tool_check = "command -v tar >/dev/null"
        if archive_compressor:
            tool_check += " && command -v " + shlex.quote(archive_compressor) + " >/dev/null"
    remote_command = tool_check + " && test -e " + shlex_quote(server_target)
    command = ssh_prefix(server_password) + ssh_local_command(server, "server", remote_command)
    run_preflight_command("local -> server SSH, tools, or source path check failed", command, server_password, dry_run)


def verify_server_to_vps_channel(
    server: dict[str, Any],
    vps: dict[str, Any],
    server_password: str,
    vps_base_dir: str,
    strategy: str,
    dry_run: bool,
) -> None:
    """Check source server SSH access to the VPS relay."""
    vps_host = require_field(vps, "host", "vps")
    vps_username = require_field(vps, "username", "vps")
    vps_port = str(vps.get("port") or 22)
    vps_login = shlex.quote(f"{vps_username}@{vps_host}")
    tool_check = "command -v rsync >/dev/null && " if strategy.startswith("rsync") else ""
    vps_command = tool_check + "mkdir -p " + shlex_quote(vps_base_dir) + " && test -w " + shlex_quote(vps_base_dir)
    remote_command = "ssh -p " + shlex.quote(vps_port) + " " + vps_login + " " + shlex_quote(vps_command)
    command = ssh_prefix(server_password) + ssh_local_command(server, "server", remote_command)
    run_preflight_command("server -> VPS SSH, tools, or relay write check failed", command, server_password, dry_run)


def verify_local_to_vps_channel(vps: dict[str, Any], vps_password: str, vps_base_dir: str, dry_run: bool) -> None:
    """Check local SSH access to the VPS relay."""
    remote_command = "command -v rsync >/dev/null && mkdir -p " + shlex_quote(vps_base_dir) + " && test -w " + shlex_quote(vps_base_dir)
    command = ssh_prefix(vps_password) + ssh_local_command(vps, "vps", remote_command)
    run_preflight_command("local -> VPS SSH, rsync, or relay write check failed", command, vps_password, dry_run)


def verify_local_base_dir_writable(local_base_dir: Path, dry_run: bool) -> None:
    """Check that the local destination directory is writable."""
    print(f"Checking local destination is writable: {local_base_dir}")
    if dry_run:
        return
    local_base_dir.mkdir(parents=True, exist_ok=True)
    if not os.access(local_base_dir, os.W_OK):
        raise RuntimeError(f"Preflight failed: local destination is not writable: {local_base_dir}")


def verify_local_archive_tools(strategy: str) -> None:
    """Check local archive tools needed by the selected strategy."""
    if strategy.startswith("archive") and shutil.which("tar") is None:
        raise RuntimeError("Preflight failed: local tar is required for archive extraction but is not installed.")


def verify_server_path_exists(server: dict[str, Any], server_password: str, server_target: str, dry_run: bool) -> None:
    """Check that the exact source-server path exists."""
    remote_test = "test -e " + shlex_quote(server_target)
    command = ssh_prefix(server_password) + ssh_local_command(server, "server", remote_test)
    print("Verifying source-server path:")
    run_checked(command, dry_run=dry_run, password=server_password)


def transfer_server_to_vps(
    server: dict[str, Any],
    vps: dict[str, Any],
    server_password: str,
    server_target: str,
    vps_destination_dir: str,
    compress: bool,
    dry_run: bool,
) -> None:
    """Push the exact source path from server to VPS."""
    vps_host = require_field(vps, "host", "vps")
    vps_username = require_field(vps, "username", "vps")
    vps_port = str(vps.get("port") or 22)
    rsync_flags = ["-avh", "--progress", "--partial", "--append-verify"]
    if compress:
        rsync_flags.insert(0, "-z")
    if dry_run:
        rsync_flags.insert(0, "--dry-run")
    vps_login = shlex.quote(f"{vps_username}@{vps_host}")
    remote_command = " ".join(
        [
            "ssh",
            "-p",
            shlex.quote(vps_port),
            vps_login,
            "mkdir -p",
            shlex_quote(vps_destination_dir),
            "&&",
            "rsync",
            *rsync_flags,
            "-e",
            shlex_quote(f"ssh -p {vps_port}"),
            shlex_quote(server_target),
            f"{vps_username}@{vps_host}:{shlex_quote(vps_destination_dir)}",
        ]
    )
    command = ssh_prefix(server_password) + ssh_local_command(server, "server", remote_command)
    print("Transferring source-server path to VPS relay:")
    run_checked(command, dry_run=dry_run, password=server_password)


def verify_vps_path_exists(vps: dict[str, Any], vps_password: str, vps_target: str, dry_run: bool) -> None:
    """Check that the VPS relay path exists."""
    remote_test = "test -e " + shlex_quote(vps_target)
    command = ssh_prefix(vps_password) + ssh_local_command(vps, "vps", remote_test)
    print("Verifying VPS relay path:")
    run_checked(command, dry_run=dry_run, password=vps_password)


def rsync_vps_target(
    vps: dict[str, Any],
    vps_password: str,
    vps_target: str,
    local_base_dir: Path,
    compress: bool,
    dry_run: bool,
) -> None:
    """Download the VPS relay path with rsync."""
    if shutil.which("rsync") is None:
        raise RuntimeError("rsync is required but is not installed.")
    host = require_field(vps, "host", "vps")
    username = require_field(vps, "username", "vps")
    port = str(vps.get("port") or 22)
    if not dry_run:
        local_base_dir.mkdir(parents=True, exist_ok=True)
    ssh_command = f"ssh -p {port}"
    remote_arg = f"{username}@{host}:{vps_target}"
    rsync_flags = ["-avh", "--progress", "--partial", "--append-verify"]
    if compress:
        rsync_flags.insert(0, "-z")
    command = ssh_prefix(vps_password) + [
        "rsync",
        *rsync_flags,
        "-e",
        ssh_command,
        remote_arg,
        str(local_base_dir),
    ]
    if dry_run:
        command.insert(len(ssh_prefix(vps_password)) + 1, "--dry-run")
    print("Downloading VPS relay path to local:")
    run_checked(command, dry_run=dry_run, password=vps_password)


def build_tar_source_parts(server_base_dir: str, server_target: str, relative_target: PurePosixPath | None) -> tuple[str, str]:
    """Return tar base directory and member path for the source target."""
    if relative_target is not None:
        return server_base_dir, str(relative_target)
    source_path = PurePosixPath(server_target.rstrip("/"))
    return str(source_path.parent), source_path.name


def transfer_archive_server_to_vps(
    server: dict[str, Any],
    vps: dict[str, Any],
    server_password: str,
    server_base_dir: str,
    server_target: str,
    relative_target: PurePosixPath | None,
    vps_archive_target: str,
    archive_compressor: str,
    dry_run: bool,
) -> None:
    """Stream a tar archive from server to VPS."""
    vps_host = require_field(vps, "host", "vps")
    vps_username = require_field(vps, "username", "vps")
    vps_port = str(vps.get("port") or 22)
    tar_base_dir, tar_member = build_tar_source_parts(server_base_dir, server_target, relative_target)
    vps_archive_dir = build_parent_posix_dir(vps_archive_target)
    compressor = build_archive_compressor_pipeline(archive_compressor)
    remote_command = " ".join(
        [
            "tar",
            "-C",
            shlex_quote(tar_base_dir),
            "-cf",
            "-",
            shlex_quote(tar_member),
            compressor,
            "|",
            "ssh",
            "-p",
            shlex.quote(vps_port),
            shlex.quote(f"{vps_username}@{vps_host}"),
            shlex_quote("mkdir -p " + shlex_quote(vps_archive_dir) + " && cat > " + shlex_quote(vps_archive_target)),
        ]
    )
    command = ssh_prefix(server_password) + ssh_local_command(server, "server", remote_command)
    print("Streaming source-server archive to VPS relay:")
    run_checked(command, dry_run=dry_run, password=server_password)


def download_vps_archive(vps: dict[str, Any], vps_password: str, vps_archive_target: str, local_archive_dir: Path, dry_run: bool) -> Path:
    """Download the VPS archive file to a local temp folder."""
    local_archive_path = build_local_archive_path(local_archive_dir, vps_archive_target)
    rsync_vps_target(vps, vps_password, vps_archive_target, local_archive_dir, False, dry_run)
    return local_archive_path


def extract_local_archive(local_archive_path: Path, local_extract_dir: Path, compressed: bool, dry_run: bool) -> None:
    """Extract a local archive into the local base folder."""
    if not dry_run:
        local_extract_dir.mkdir(parents=True, exist_ok=True)
    tar_flags = "-xzf" if compressed else "-xf"
    command = ["tar", tar_flags, str(local_archive_path), "-C", str(local_extract_dir)]
    print("Extracting local archive:")
    run_checked(command, dry_run=dry_run)


def cleanup_local_archive(local_archive_path: Path, dry_run: bool) -> None:
    """Remove the local temporary archive."""
    print(f"Local archive cleanup target: {local_archive_path}")
    if dry_run:
        return
    local_archive_path.unlink(missing_ok=True)


def cleanup_vps_archive(vps: dict[str, Any], vps_password: str, vps_archive_target: str, dry_run: bool) -> None:
    """Remove the VPS archive relay file."""
    remote_remove = "rm -f -- " + shlex_quote(vps_archive_target)
    command = ssh_prefix(vps_password) + ssh_local_command(vps, "vps", remote_remove)
    print("Removing VPS archive relay file:")
    run_checked(command, dry_run=dry_run, password=vps_password)


def cleanup_vps_target(vps: dict[str, Any], vps_password: str, vps_target: str, dry_run: bool, yes: bool) -> None:
    """Remove the VPS relay path after a successful download."""
    if is_dangerous_remote_delete(vps_target):
        raise ValueError(f"Refusing to delete unsafe VPS relay path: {vps_target}")
    print(f"VPS cleanup target: {vps_target}")
    if not yes and not dry_run:
        answer = input("Remove this VPS relay copy? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            raise RuntimeError("VPS cleanup cancelled.")
    remote_remove = "rm -rf -- " + shlex_quote(vps_target)
    command = ssh_prefix(vps_password) + ssh_local_command(vps, "vps", remote_remove)
    print("Removing VPS relay copy:")
    run_checked(command, dry_run=dry_run, password=vps_password)


def is_dangerous_remote_delete(remote_path: str) -> bool:
    """Return whether a remote deletion target is unsafe."""
    stripped = remote_path.strip().rstrip("/")
    if stripped in {"", ".", "/"}:
        return True
    path = PurePosixPath(stripped)
    return path.name in {"", ".", ".."}


def shlex_quote(value: str) -> str:
    """Quote text for a remote POSIX shell."""
    return "'" + value.replace("'", "'\"'\"'") + "'"


def confirm_transfer(
    route: dict[str, Any],
    server_target: str,
    vps_target: str,
    local_destination_dir: Path,
    local_extract_dir: Path,
    strategy: str,
    yes: bool,
) -> None:
    """Ask for final confirmation before transfer."""
    server = get_mapping(route, "server")
    vps = get_mapping(route, "vps")
    print(f"Route: {route.get('name')} ({server.get('host')} -> {vps.get('host')} -> local)")
    print(f"Strategy: {strategy}")
    print(f"Server source: {server_target}")
    print(f"VPS relay: {vps_target}")
    if strategy.startswith("archive"):
        print(f"Local temp folder: {local_destination_dir}")
        print(f"Local extract folder: {local_extract_dir}")
    else:
        print(f"Local folder: {local_destination_dir}")
    if yes:
        return
    answer = input("Transfer this exact path through the VPS relay? [y/N] ").strip().lower()
    if answer not in {"y", "yes"}:
        raise RuntimeError("Transfer cancelled.")


def print_routes(routes: list[dict[str, Any]]) -> None:
    """Print configured route summaries."""
    for route in routes:
        server = get_mapping(route, "server")
        vps = get_mapping(route, "vps")
        print(f"{route.get('name')} {server.get('username')}@{server.get('host')} -> {vps.get('username')}@{vps.get('host')}")


def main() -> int:
    """Run the relay transfer workflow."""
    args = parse_args()
    config_path = args.config.expanduser()
    if args.init_config:
        if config_path.exists():
            print(f"Config already exists: {config_path}")
            return 0
        copy_template_config(config_path)
        return 0
    if not config_path.exists():
        copy_template_config(config_path)
        return 1
    config = load_config(config_path)
    routes = get_routes(config)
    require_private_config_if_passwords(config_path, routes)
    if args.list_routes:
        print_routes(routes)
        return 0
    route = choose_route(routes, args.route)
    server = get_mapping(route, "server")
    vps = get_mapping(route, "vps")
    server_base_dir = prompt_text(args.server_base_dir or server.get("remote_base_dir"), "Source server base directory")
    vps_base_dir = prompt_text(args.vps_base_dir or vps.get("relay_base_dir"), "VPS relay base directory")
    local_base_dir = prompt_path(args.local_base_dir or path_from_route(route, "local_base_dir"), "Local destination directory")
    target = prompt_text(args.target, "Exact target file/folder name or path")
    requested_strategy = parse_strategy_config_value(args.strategy or route.get("transfer_strategy"), "auto")
    server_target = build_server_target(server_base_dir, target)
    server_password = get_password(server, "server")
    vps_password = get_password(vps, "vps")
    analysis = analyze_server_target(server, server_password, server_target)
    selected_strategy = choose_transfer_strategy(requested_strategy, analysis)
    print_target_analysis(analysis, requested_strategy, selected_strategy)
    if not analysis.exists:
        raise ValueError(f"Source-server path was not found: {server_target}")
    if args.analyze_only:
        return 0
    archive_compressor = choose_server_archive_compressor(server, server_password, selected_strategy)
    paths = build_transfer_paths(server_base_dir, vps_base_dir, local_base_dir, target, selected_strategy)
    route_preflight = parse_bool_config_value(route.get("preflight"), False)
    should_preflight = args.preflight_only or (route_preflight and not args.skip_preflight)
    confirm_transfer(
        route,
        paths.server_target,
        paths.vps_target,
        paths.local_destination_dir,
        paths.local_extract_dir,
        selected_strategy,
        args.yes or args.dry_run or args.preflight_only,
    )
    if should_preflight:
        run_preflight_checks(
            server,
            vps,
            server_password,
            vps_password,
            paths.server_target,
            paths.vps_destination_dir,
            paths.local_extract_dir,
            selected_strategy,
            archive_compressor,
            args.dry_run and not args.preflight_only,
        )
    if args.preflight_only:
        return 0
    verify_server_path_exists(server, server_password, paths.server_target, args.dry_run)
    if selected_strategy.startswith("rsync"):
        compress = selected_strategy == "rsync-compress"
        cleanup_vps_copy = args.cleanup_vps_copy or parse_bool_config_value(route.get("cleanup_vps_copy"), False)
        transfer_server_to_vps(server, vps, server_password, paths.server_target, paths.vps_destination_dir, compress, args.dry_run)
        verify_vps_path_exists(vps, vps_password, paths.vps_target, args.dry_run)
        rsync_vps_target(vps, vps_password, paths.vps_target, paths.local_destination_dir, compress, args.dry_run)
        if cleanup_vps_copy:
            cleanup_vps_target(vps, vps_password, paths.vps_target, args.dry_run, args.yes)
        return 0
    transfer_archive_server_to_vps(
        server,
        vps,
        server_password,
        server_base_dir,
        paths.server_target,
        paths.relative_target,
        paths.vps_target,
        archive_compressor,
        args.dry_run,
    )
    verify_vps_path_exists(vps, vps_password, paths.vps_target, args.dry_run)
    local_archive_path = download_vps_archive(vps, vps_password, paths.vps_target, paths.local_destination_dir, args.dry_run)
    extract_local_archive(local_archive_path, paths.local_extract_dir, selected_strategy == "archive-compress", args.dry_run)
    cleanup_local_archive(local_archive_path, args.dry_run)
    cleanup_vps_archive(vps, vps_password, paths.vps_target, args.dry_run)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, PermissionError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)
