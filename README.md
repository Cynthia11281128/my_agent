# My Agent Skills

[中文](README-CN.md)

Personal agent skills for reusable workflows.

## Public Skills

| Skill | Description |
| --- | --- |
| `connect-folder-to-github` | Connect a local folder to a remote GitHub repository. |
| `connect-github-account` | Set up and verify GitHub SSH access for the local machine. |
| `local-skill-creator` | Create project-local Codex skills using the upstream Skill Creator workflow. |
| `local-skill-setup` | Set up project-local Codex skills and per-folder skill scope. |
| `md-translate-inplace-eng` | Translate Chinese Markdown into English in place and lightly correct existing English grammar. |
| `md-translate-pair-cn` | Translate English Markdown into a sibling Chinese `-CN.md` file. |
| `push-safety-check` | Scan repos for private information before pushing. |
| `setup-collaborator` | Clarify and handle non-code setup and configuration tasks. |
| `summarize-workflow` | Write paired English and Chinese reusable workflow summaries. |
| `md-sync-bilingual` | Align paired English and Chinese Markdown files using explicit change markers. |
| `md-edit` | Edit English Markdown and mark changes for Chinese pair syncing. |
| `quick-data-transfer` | Download files or folders from configured servers. |
| `repo-env-setup` | Set up repo environments with external large files, mirrored paths, symlinks, and setup notes. |
| `vps-data-download` | Transfer server files through a VPS relay to local. |

## Private Skills

| Skill | Description |
| --- | --- |
| `audit-skill-index` | Check README skill indexes against public and private skill folders. |
| `my-skill-creator` | Create skills with upstream rules, public/private placement, and bilingual README indexes. |

## Install For Codex

```bash
./scripts/install-skills.sh
```

Restart Codex after installing so the skill index refreshes.

## Local Development

Public skills live under `skills/<skill-name>/`. Private skills live under `private/skills/<skill-name>/`. Every skill must include a `SKILL.md` file with YAML frontmatter:

```markdown
---
name: project-init
description: "..."
---
```

Keep `SKILL.md` concise. Put detailed reference material in `references/`, deterministic helpers in `scripts/`, and reusable templates in `assets/`.
