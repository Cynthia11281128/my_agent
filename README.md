# My Agent Skills

Personal agent skills for reusable workflows.

## Skills

| Skill | Description |
| --- | --- |


## Install For Codex

```bash
./scripts/install-skills.sh
```

Restart Codex after installing so the skill index refreshes.

## Local Development

Each skill lives under `skills/<skill-name>/` and must include a `SKILL.md` file with YAML frontmatter:

```markdown
---
name: project-init
description: "..."
---
```

Keep `SKILL.md` concise. Put detailed reference material in `references/`, deterministic helpers in `scripts/`, and reusable templates in `assets/`.
