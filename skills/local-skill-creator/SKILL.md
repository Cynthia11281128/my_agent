---
name: local-skill-creator
description: Create project-local Codex skills using the upstream Skill Creator workflow. Use when the user asks to create a skill only for the current repository or folder, create local-only skills, create project-specific skills, add a skill under .codex-home/skills, or use Skill Creator with a project-local CODEX_HOME.
---

# Local Skill Creator

## Required Upstream Workflow

Before creating or updating a local skill, read and follow:

```text
/home/cynthia/.codex/skills/.system/skill-creator/SKILL.md
```

Apply this skill as a local-scope override: the generated skill belongs in the target project's `.codex-home/skills`, not in the global Codex skill directory and not in this skill repository's public/private indexes.

## Workflow

1. Identify the target project folder. Default to the current workspace root when the user does not specify another folder.
2. Verify that `<project>/.codex-home/skills` exists. If it does not, use or recommend `$local-skill-setup` first, then continue once the local skill directory exists.
3. Understand the requested local skill with concrete examples: intended user prompts, trigger conditions, success behavior, and any resources the skill needs.
4. Choose a lowercase hyphen-case skill name from the request. Ask only when multiple plausible names would materially change the skill's trigger behavior.
5. Initialize the skill with upstream `init_skill.py` using `--path <project>/.codex-home/skills` and deterministic `agents/openai.yaml` interface values.
6. Write a concise `SKILL.md` with valid `name` and `description` frontmatter, focused body instructions, and only necessary bundled resources.
7. Validate the created skill with upstream `quick_validate.py`. If the validator cannot run because of missing environment dependencies, report the blocker and perform equivalent manual checks.
8. Verify the local skill is isolated to `<project>/.codex-home/skills/<skill-name>` and explain that Codex must be started with the project-local `CODEX_HOME` for the skill to appear.

## Boundaries

- Do not update `/home/cynthia/tools/my_agent/README.md` or `README-CN.md` for skills created inside another project's `.codex-home/skills`.
- Do not install the generated skill globally unless the user explicitly changes scope.
- Do not overwrite an existing local skill folder without explicit user approval.
- Do not create extra documentation files inside the generated skill unless they are required skill resources.
