#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${HOME}/.agents/skills"

mkdir -p "$TARGET"

install_dir() {
  local base="$1"
  [ -d "$base" ] || return 0

  for skill in "$base"/*/; do
    [ -d "$skill" ] || continue
    case "$(basename "$skill")" in _*) continue ;; esac
    [ -f "$skill/SKILL.md" ] || continue
    ln -sfn "$skill" "$TARGET/$(basename "$skill")"
    echo "Installed $(basename "$skill") -> $skill"
  done
}

install_dir "$ROOT/skills"
install_dir "$ROOT/private/skills"

echo "Done. Restart Codex if newly installed skills do not appear."
