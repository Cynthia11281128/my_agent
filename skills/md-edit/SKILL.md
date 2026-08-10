---
name: md-edit
description: Edit English Markdown files in bilingual English/Chinese documentation workflows. Use when the user asks Codex to modify Markdown content and wants Codex to update only the English source first, mark additions and deletions with md-sync-bilingual markers when a `-CN.md` pair exists, and optionally continue into `$md-sync-bilingual` to update the Chinese counterpart.
---

# Markdown Edit

## Goal

Apply requested Markdown edits to the English file first. If the English file has a paired Chinese `-CN.md` counterpart, mark the English-side changes with explicit sync markers, then ask the user whether to continue into `$md-sync-bilingual`.

## Core Rules

- Treat `name.md` and `name-CN.md` in the same folder as the default bilingual pair.
- Edit only the English Markdown file during this skill's main edit pass.
- If no Chinese counterpart exists for the target English file, edit the English file normally without adding sync markers.
- If a Chinese counterpart exists, wrap changed English content in markers so `$md-sync-bilingual` can later update the Chinese file.
- Do not edit the Chinese file directly unless the user confirms continuing into `$md-sync-bilingual`.
- Preserve Markdown structure, frontmatter, code fences, links, tables, comments, and formatting unless the user's requested edit requires changing them.
- Keep marker scopes as small as practical while still giving `$md-sync-bilingual` enough context to sync accurately.
- Do not create nested markers. If existing unresolved markers are present in the target pair, stop and ask whether to resolve them with `$md-sync-bilingual` before making new marked edits.

## Marker Syntax

- Addition: `+++new English content/+++`
- Deletion: `---old English content/---`
- Replacement: mark the old content as deletion and the new content as addition, adjacent where possible.

Examples:

```markdown
This paragraph has +++new wording/+++ inline.

---
The paragraph that should be removed later from both languages.
/---

+++
A new paragraph that should be added to the Chinese counterpart.
/+++
```

## Workflow

1. Identify the target English Markdown file or target folder from the user request. Ask for the target only if it cannot be inferred.
2. Run the existing bilingual scanner from `$md-sync-bilingual` on the containing folder:

```bash
python3 <repo-root>/skills/md-sync-bilingual/scripts/scan_bilingual_md.py <folder>
```

3. Use the scanner output to determine whether the target English file has an exact `-CN.md` pair. Do not rely on semantic comparison.
4. If there is no exact Chinese pair, apply the requested Markdown edit to the English file directly and do not add sync markers.
5. If there is an exact Chinese pair and no unresolved marker errors, apply the requested edit to the English file with markers around every changed region.
6. Summarize the English file changed, whether a Chinese pair was found, and the marker groups added.
7. Ask the user whether to continue with `$md-sync-bilingual` now.
8. If the user confirms, invoke `$md-sync-bilingual` for the same folder or pair so the Chinese counterpart can be updated and resolved markers can be removed.

## Editing Guidance

- For additions, insert only the new English content inside `+++.../+++`.
- For deletions, leave the deleted English content in place inside `---.../---` until `$md-sync-bilingual` resolves the deletion against the Chinese file.
- For replacements, avoid one large marker when separate old and new spans make the intended sync clearer.
- For reorganizations, mark moved or rewritten blocks explicitly and keep headings stable when possible.
- For code blocks, commands, links, and tables, mark the smallest complete Markdown unit that remains valid and readable.
- If the requested edit touches both paired and unpaired English files, only paired files receive markers.

## Handoff To md-sync-bilingual

When asking whether to sync, use a concise prompt such as:

```markdown
I edited `guide.md` and added 3 marker groups for `guide-CN.md`.

Should I run `$md-sync-bilingual` now to update the Chinese file and remove resolved markers?
```

If the user says yes, follow `$md-sync-bilingual` exactly. If the user says no, leave the markers in the English file and report that the Chinese file still needs syncing.
