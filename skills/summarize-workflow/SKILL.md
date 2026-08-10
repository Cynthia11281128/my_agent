---
name: summarize-workflow
description: Summarize the prior work in the current conversation into a generalized, reproducible step-by-step workflow written to a user-specified Markdown file. Use when the user asks to summarize what happened, produce a workflow summary, document the execution process, create handoff notes, or explain how to successfully repeat the task from the beginning. Especially use when the user wants the summary saved as Markdown, focused on the successful path rather than a chronological log, with failed attempts mentioned only briefly at the end.
---

# Summarize Workflow

## Goal

Produce an English Markdown file summarizing the task workflow already performed in the current conversation. Write it as a generalized, successful, repeatable procedure that another Codex instance or engineer could follow from start to finish without depending on user-specific local paths or private machine details.

The user may request this in Chinese or English. Keep skill artifacts, headings, and final summary text in English unless the user explicitly asks for another language.

## Core Rules

- Summarize the workflow, not the chat transcript.
- Prefer the final successful path over chronological narration.
- Include enough generalized concrete detail to reproduce the work: relative files touched, commands run, tools used, important inputs, verification steps, and final outputs.
- Omit routine exploration unless it materially affects the successful procedure.
- Do not interleave failed attempts into the main steps.
- Mention failed attempts, dead ends, or corrections only in a short final section.
- Preserve exact names for commands, tools, branches, public URLs, public IDs, and generated artifacts when available.
- Use repository-relative paths, project-relative paths, placeholders, or role-based names instead of absolute local paths that expose user or machine details.
- Do not include personal filesystem paths, usernames, home directories, temporary sandbox paths, private tokens, credentials, or other machine-specific private details in the workflow file.
- Do not invent details that are not present in the conversation. Mark uncertain details as not available.
- If the relevant task is unfinished, stop and ask the user to confirm whether to summarize the unfinished portion, wait until completion, or summarize a specific completed subset.
- If the current conversation contains multiple distinct tasks or task phases, stop and ask the user which task or portion to summarize before writing the workflow.
- Write the summary to a `.md` file instead of printing the full summary in chat.
- Require the user to specify the output Markdown path.
- If the user does not specify an output path, stop and ask for the exact `.md` path before writing.
- If the target file already exists, do not overwrite it or choose an alternate path automatically. Ask the user to confirm overwriting or provide another exact `.md` path.
- After writing the file, reply in chat with only a concise status, the file path, and any unresolved blocker.

## Markdown File Structure

Write this structure into the Markdown file by default:

```markdown
**Workflow Summary**

1. [Successful step from the beginning]
2. [Next successful step]
3. [Continue until the task reaches the current or final state]

**Verification**
- [Commands, checks, screenshots, tests, or manual validation performed]
- [State any checks that were not run, if relevant]

**Run-Specific Settings**
- [Briefly describe non-personal settings from this run that may need adaptation, such as sandbox limits, dependency availability, target branch, selected output path pattern, or tool availability]

**Final State**
- [What was created, changed, deployed, or concluded]
- [Where the relevant files, links, or artifacts are]

**Failed Attempts / Notes**
- [Briefly mention failures, false starts, permission issues, abandoned approaches, or constraints]
```

If a section has no useful content, omit it. Keep the main workflow numbered and ordered by the logical successful execution path, not by every event in the conversation.

## Workflow Extraction Process

1. Identify whether the conversation contains exactly one task with a completed or clearly bounded outcome.
2. If the task is unfinished, ask the user which option they want: summarize the unfinished progress, wait until the task is complete, or summarize a specific completed subset.
3. If the conversation contains multiple tasks or ambiguous phases, ask the user which task or portion to summarize.
4. If the user has not specified an output Markdown path, ask for the exact path before writing.
5. After scope and output path are confirmed, identify the selected task's original request and final intended outcome.
6. Scan the conversation for actions that contributed to the selected outcome.
7. Collapse repeated exploration into one concise successful instruction.
8. Convert tool calls and edits into reproducible, generalized steps.
9. Rewrite user-specific local details into safe generalized references, such as `<project-root>`, `<workspace>`, `<output-file>`, repository-relative paths, or neutral descriptions.
10. Move failures, retries, and detours into `Failed Attempts / Notes`.
11. Include validation evidence after the workflow, not mixed into every step unless it is part of the procedure.
12. Add a `Run-Specific Settings` section for non-personal adaptation context from this run.
13. Write the summary to the user-specified Markdown file.
14. Reply with the file path and brief status, not the full summary content.
15. End with the final state and remaining work only when the user explicitly chose to summarize unfinished progress.

## What To Include

Include:

- General repository or working directory context, without personal absolute paths.
- Important files read or edited, using repository-relative or project-relative paths when possible.
- Commands that matter for setup, generation, validation, tests, deployment, or inspection.
- Tool or connector usage that another agent would need to repeat.
- Decisions made from user preferences or environmental constraints.
- Any workaround needed because of permissions, missing dependencies, sandbox limits, failing tests, or unavailable services.
- A short `Run-Specific Settings` section that captures adaptable, non-personal facts from this run.

Do not include:

- Every `ls`, `sed`, `rg`, or exploratory read unless it teaches the repeatable path.
- Long raw command outputs.
- Internal deliberation or hidden reasoning.
- A chronological blow-by-blow transcript.
- Praise, commentary, or meta discussion about the summary itself.
- The full Markdown summary in chat unless the user explicitly asks to see it inline.
- Absolute user-specific local paths such as `/home/<user>/...`, `/Users/<user>/...`, drive-letter home paths, or sandbox temp paths unless the user explicitly asks to preserve them.

## Handling Failure And Retry History

When the conversation contains failed attempts:

- Summarize only the final working approach in the numbered workflow.
- Add a short `Failed Attempts / Notes` section with the failed approach and why it was abandoned.
- Keep each failure note to one sentence when possible.
- Mention failure details only when they would prevent another agent from repeating the same mistake.

Example:

```markdown
**Failed Attempts / Notes**
- Attempting to write to the global Codex skills directory failed because it was read-only in this environment, so the skill was created under the writable workspace instead.
```
