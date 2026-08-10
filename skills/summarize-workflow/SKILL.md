---
name: summarize-workflow
description: Summarize the prior work in the current conversation into generalized, reproducible step-by-step workflow documentation written as paired English and Chinese Markdown files in a user-specified output folder. Use when the user asks to summarize what happened, produce a workflow summary, document the execution process, create handoff notes, or explain how to successfully repeat the task from the beginning. Especially use when the user wants the summary saved as Markdown, focused on the successful path rather than a chronological log, with failed attempts mentioned only briefly at the end.
---

# Summarize Workflow

## Purpose

Write paired English and Chinese Markdown workflow docs for work already performed in the current conversation. Make the result a generalized, successful, repeatable procedure rather than a chat transcript.

Default output is exactly two files in a user-specified folder: `<name>/<name>.md` in English and `<name>/<name>-CN.md` in Chinese.

## Rules

- Summarize the workflow, not the chat transcript.
- Prefer the final successful path over chronological narration.
- Include reproducible specifics: relevant files, commands, tools, inputs, verification, and final outputs.
- Ask before writing if the task is unfinished, there are multiple distinct tasks, the output folder is missing, or either target file already exists.
- Use placeholders for user-provided input files, directories, hosts, and machine-specific names, such as `<image-archive>.tar.gz`, `<project-root>`, and `<server>`.
- Preserve exact names only for generated deliverables, public IDs, commands, branches, tools, or artifact names required to reproduce the outcome.
- When placeholders are used, add a final `Placeholder Values` section mapping each placeholder to its real value from this run, using safe descriptions or redactions for sensitive values.
- Never include personal paths, usernames, home directories, temp sandbox paths, credentials, tokens, or private machine details.
- Do not put incidental auxiliary artifacts in the main workflow unless required. If they were only used for optional validation, mention them in `Settings / Inputs` or `Failed Attempts / Notes`; phrase split chunks as optional checks.
- Do not invent missing details. Mark uncertain details as not available.

## Workflow

1. Confirm the task scope is complete and unambiguous.
2. Create the output folder if needed; use its basename as `<name>` unless the user gave a different file stem.
3. Extract only actions that contributed to the selected outcome.
4. Collapse exploration into concise successful instructions.
5. Convert local details to repository-relative paths, project-relative paths, role-based names, or placeholders.
6. Put validation evidence after the workflow, not mixed into each step unless validation is part of the procedure.
7. Move failures, retries, and detours into `Failed Attempts / Notes`.
8. Write both Markdown files, then reply only with concise status, both paths, and any blocker.

## Output Contract

Use Markdown headings in both files. Translate headings and content in the Chinese file; translate `Settings / Inputs` as `设置 / 输入` and `Placeholder Values` as `占位符实际值`. Omit sections with no useful content.

```markdown
# [Workflow Title]

## Settings / Inputs

[Inputs, paths, host assumptions, adaptable settings, and placeholders.]

## Task Description

[Generalized task and intended outcome.]

## Workflow Summary

1. [Successful step from the beginning]
2. [Next successful step]

## Verification
- [Commands, checks, screenshots, tests, or manual validation performed]
- [Checks not run, if relevant]

## Final State
- [What was created, changed, deployed, or concluded]
- [Where relevant files, links, or artifacts are]

## Failed Attempts / Notes
- [Brief failures, constraints, skipped optional artifacts, or abandoned approaches]

## Placeholder Values
- `<placeholder>`: [real value from this run, or a safe description/redaction]
```

Keep `Workflow Summary` numbered and ordered by the logical successful path. Keep `Failed Attempts / Notes` short, and include failure details only when they help avoid repeating the same mistake. Omit `Placeholder Values` if no placeholders are used.
