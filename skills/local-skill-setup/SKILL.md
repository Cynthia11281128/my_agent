---
name: local-skill-setup
description: Set up project-local Codex skills and per-folder skill scope. Use when the user wants skills available only in one repository or folder, asks about local-only skills, project-specific CODEX_HOME, .codex-home/skills, direnv-based Codex setup, .envrc for Codex, or installing/using a skill only within the current project.
---

# Local Skill Setup

## Required Setup Workflow

Before taking setup actions, read and apply:

```text
/home/cynthia/tools/my_agent/skills/setup-collaborator/SKILL.md
```

Follow its referenced shared setup-collaboration workflow and response template whenever user action remains.

## Workflow

1. Restate the desired local skill setup in operational terms: target project folder, intended local `CODEX_HOME`, existing global Codex setup, and what success means.
2. Discover local facts before asking: inspect `.envrc`, `.codex-home/skills`, existing `CODEX_HOME`, `direnv` availability, shell hook state, and relevant shell startup files.
3. Explain each planned change before making it. Do not overwrite an existing `.envrc` or shell startup configuration without explicit approval.
4. Set the project-local Codex home to `<project>/.codex-home` and ensure `<project>/.codex-home/skills` exists.
5. When choosing the activation/login approach, ask the user to choose between the `direnv` method and the symlink method. Explain that `direnv` requires installing `direnv` and configuring a shell hook; if `direnv` is missing, sudo is required, or shell hook changes need user confirmation, give the exact user-run commands and do not claim they were completed.
6. After setup, verify with read-only checks such as `echo $CODEX_HOME`, `direnv status`, `.envrc` contents, and `.codex-home/skills` existence.
7. Clearly separate work Codex completed from user-required steps such as entering a sudo password, running `direnv allow`, restarting a shell, or starting Codex from the project folder.

## Defaults

- Use `.codex-home` as the project-local Codex home directory.
- Use `.codex-home/skills` as the local skill install location.
- Use `.envrc` with `export CODEX_HOME=<absolute-project-path>/.codex-home`.
- Keep existing non-Codex `.envrc` content unless the user explicitly wants it replaced.
- If `direnv` cannot be used, provide a project launcher command or script pattern instead of blocking the setup explanation.

## Local Profile Sign-In

- Explain that changing `CODEX_HOME` creates a separate Codex profile, so Codex may ask the user to sign in again.
- Present the choice as:
  - `direnv` method: automatic per-folder `CODEX_HOME` activation, but it requires installing `direnv` and configuring the shell hook. On Ubuntu/Debian, install it with `sudo apt-get update && sudo apt-get install -y direnv`.
  - Symlink method: no `direnv` install; launch Codex with the project-local `CODEX_HOME` manually or through a launcher, and reuse the global login by symlinking selected files from `~/.codex`.
- Before creating login-related files or symlinks, verify `.codex-home/` is gitignored and inspect only file paths or file types. Never print or inspect auth file contents.
- Do not overwrite existing `.codex-home/auth.json`, `.codex-home/accounts.json`, `.codex-home/accounts`, or `.codex-home/config.toml` without explicit user approval.
- To reuse the global login, use this pattern from the project root after `.codex-home` exists:

```bash
ln -s ~/.codex/auth.json .codex-home/auth.json
ln -s ~/.codex/accounts.json .codex-home/accounts.json
ln -s ~/.codex/accounts .codex-home/accounts
ln -s ~/.codex/config.toml .codex-home/config.toml
```
