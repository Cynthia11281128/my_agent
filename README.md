# My Agent Skills

[中文](README-CN.md)

Personal agent skills for reusable workflows.

## Public Skills

| Skill | Description |
| --- | --- |
| `connect-folder-to-github` | Connect a local folder to a remote GitHub repository. |
| `connect-github-account` | Set up and verify GitHub SSH access for the local machine. |
| `push-safety-check` | Scan repos for private information before pushing. |
| `summarize-workflow` | Write paired English and Chinese reusable workflow summaries. |
| `sync-bilingual-md` | Align paired English and Chinese Markdown files using explicit change markers. |

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
