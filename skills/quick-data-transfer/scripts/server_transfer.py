#!/usr/bin/env python3
"""Download an exact file or folder from a configured server with rsync."""

from __future__ import annotations

import argparse
import getpass
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only on missing dependency
    yaml = None


SKILL_DIR = Path(__file__).resolve().parents[1]
ASSETS_DIR = SKILL_DIR / "assets"
DEFAULT_CONFIG_PATH = Path.cwd() / ".codex-home" / "quick-data-transfer.yaml"
TEMPLATE_CONFIG_PATH = ASSETS_DIR / "server_transfer_config.template.yaml"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--init-config", action="store_true")
    parser.add_argument("--list", action="store_true", dest="list_servers")
    parser.add_argument("--server", help="Configured server name.")
    parser.add_argument("--remote-base-dir", help="Remote base directory.")
    parser.add_argument("--local-base-dir", type=Path, help="Local destination directory.")
    parser.add_argument("--target", help="Exact remote file/folder path or name.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true", help="Do not prompt for confirmation.")
    return parser.parse_args()


def copy_template_config(config_path: Path) -> None:
    """Create a user-editable config from the bundled template."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(TEMPLATE_CONFIG_PATH, config_path)
    config_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    print(f"Created config template: {config_path}")
    print("Fill it with server details for quicker transfers, then keep it private with chmod 600.")


def load_config(config_path: Path) -> dict[str, Any]:
    """Load the YAML transfer config."""
    with config_path.open("r", encoding="utf-8") as file:
        text = file.read()
    if yaml is None:
        return parse_simple_server_config(text, config_path)
    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a YAML mapping: {config_path}")
    return data


def parse_simple_server_config(text: str, config_path: Path) -> dict[str, Any]:
    """Parse the bundled server config shape without PyYAML."""
    servers: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    in_servers = False
    for raw_line in text.splitlines():
        line_without_comment = raw_line.split("#", 1)[0].rstrip()
        if not line_without_comment.strip():
            continue
        stripped = line_without_comment.strip()
        if stripped == "servers:":
            in_servers = True
            continue
        if not in_servers:
            continue
        if stripped.startswith("- "):
            current = {}
            servers.append(current)
            key, value = split_config_key_value(stripped[2:], config_path)
            if key:
                current[key] = parse_scalar_config_value(value)
            continue
        if current is None:
            raise ValueError(f"Expected a server list item before '{stripped}' in {config_path}")
        key, value = split_config_key_value(stripped, config_path)
        current[key] = parse_scalar_config_value(value)
    return {"servers": servers}


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
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    if value.isdigit():
        return int(value)
    return value


def require_private_config_if_passwords(config_path: Path, servers: list[dict[str, Any]]) -> None:
    """Require chmod 600 when stored passwords are present."""
    has_password = any(str(server.get("password") or "") for server in servers)
    if not has_password:
        return
    mode = stat.S_IMODE(config_path.stat().st_mode)
    if mode != 0o600:
        raise PermissionError(f"{config_path} contains passwords and must be chmod 600; current mode is {mode:o}.")


def get_servers(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Return validated server entries from config."""
    servers = config.get("servers", [])
    if not isinstance(servers, list):
        raise ValueError("Config field 'servers' must be a list.")
    typed_servers = [server for server in servers if isinstance(server, dict)]
    if len(typed_servers) != len(servers):
        raise ValueError("Every server entry must be a mapping.")
    return typed_servers


def choose_server(servers: list[dict[str, Any]], server_name: str | None) -> dict[str, Any]:
    """Select a configured server by name or prompt."""
    if server_name:
        for server in servers:
            if server.get("name") == server_name:
                return server
        names = ", ".join(str(server.get("name")) for server in servers)
        raise ValueError(f"Server '{server_name}' was not found. Available servers: {names}")
    if len(servers) == 1:
        return servers[0]
    if not servers:
        raise ValueError("No servers are configured.")
    print("Configured servers:")
    for index, server in enumerate(servers, start=1):
        print(f"{index}. {server.get('name')} ({server.get('username')}@{server.get('host')})")
    while True:
        selected = input("Select server number: ").strip()
        if selected.isdigit() and 1 <= int(selected) <= len(servers):
            return servers[int(selected) - 1]
        print("Enter a valid server number.")


def require_server_field(server: dict[str, Any], field_name: str) -> str:
    """Return a required server field as text."""
    value = str(server.get(field_name) or "").strip()
    if not value:
        raise ValueError(f"Server '{server.get('name')}' is missing required field: {field_name}")
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


def build_remote_target(remote_base_dir: str, target: str) -> str:
    """Build the exact remote target path."""
    target_path = target.strip()
    if not target_path:
        raise ValueError("Target file/folder name is required.")
    if target_path.startswith("/"):
        return target_path
    return str(Path(remote_base_dir) / target_path)


def get_password(server: dict[str, Any]) -> str:
    """Return configured or prompted password text."""
    password = str(server.get("password") or "")
    if password:
        return password
    if str(server.get("password_prompt") or "").lower() in {"1", "true", "yes"}:
        return getpass.getpass(f"Password for {server.get('username')}@{server.get('host')}: ")
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
    printable = " ".join(command)
    print(printable)
    if dry_run:
        return
    env = os.environ.copy()
    if password:
        env["SSHPASS"] = password
    subprocess.run(command, check=True, env=env)


def verify_remote_path_exists(server: dict[str, Any], password: str, remote_target: str, dry_run: bool) -> None:
    """Check that the exact remote path exists."""
    host = require_server_field(server, "host")
    username = require_server_field(server, "username")
    port = str(server.get("port") or 22)
    remote_test = "test -e " + shlex_quote(remote_target)
    command = ssh_prefix(password) + ["ssh", "-p", port, f"{username}@{host}", remote_test]
    print("Verifying remote path:")
    run_checked(command, dry_run=dry_run, password=password)


def rsync_remote_target(server: dict[str, Any], password: str, remote_target: str, local_base_dir: Path, dry_run: bool) -> None:
    """Download the exact remote path with rsync."""
    if shutil.which("rsync") is None:
        raise RuntimeError("rsync is required but is not installed.")
    host = require_server_field(server, "host")
    username = require_server_field(server, "username")
    port = str(server.get("port") or 22)
    local_base_dir.mkdir(parents=True, exist_ok=True)
    ssh_command = f"ssh -p {port}"
    remote_arg = f"{username}@{host}:{shlex_quote(remote_target)}"
    command = ssh_prefix(password) + ["rsync", "-avh", "--progress", "-e", ssh_command, remote_arg, str(local_base_dir)]
    if dry_run:
        command.insert(len(ssh_prefix(password)) + 2, "--dry-run")
    print("Transferring remote path:")
    run_checked(command, dry_run=dry_run, password=password)


def shlex_quote(value: str) -> str:
    """Quote text for a remote POSIX shell."""
    return "'" + value.replace("'", "'\"'\"'") + "'"


def confirm_transfer(server: dict[str, Any], remote_target: str, local_base_dir: Path, yes: bool) -> None:
    """Ask for final confirmation before transfer."""
    print(f"Server: {server.get('name')} ({server.get('username')}@{server.get('host')})")
    print(f"Remote: {remote_target}")
    print(f"Local folder: {local_base_dir}")
    if yes:
        return
    answer = input("Download this exact path? [y/N] ").strip().lower()
    if answer not in {"y", "yes"}:
        raise RuntimeError("Transfer cancelled.")


def main() -> int:
    """Run the transfer workflow."""
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
    servers = get_servers(config)
    require_private_config_if_passwords(config_path, servers)
    if args.list_servers:
        for server in servers:
            print(f"{server.get('name')} {server.get('username')}@{server.get('host')}:{server.get('port') or 22}")
        return 0
    server = choose_server(servers, args.server)
    remote_base_dir = prompt_text(args.remote_base_dir or server.get("remote_base_dir"), "Remote base directory")
    local_base_dir = prompt_path(args.local_base_dir or path_from_server(server, "local_base_dir"), "Local destination directory")
    target = prompt_text(args.target, "Exact target file/folder name or path")
    remote_target = build_remote_target(remote_base_dir, target)
    password = get_password(server)
    confirm_transfer(server, remote_target, local_base_dir, args.yes or args.dry_run)
    verify_remote_path_exists(server, password, remote_target, args.dry_run)
    rsync_remote_target(server, password, remote_target, local_base_dir, args.dry_run)
    return 0


def path_from_server(server: dict[str, Any], field_name: str) -> Path | None:
    """Return an optional path field from a server entry."""
    value = str(server.get(field_name) or "").strip()
    if not value:
        return None
    return Path(value).expanduser()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, PermissionError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)
