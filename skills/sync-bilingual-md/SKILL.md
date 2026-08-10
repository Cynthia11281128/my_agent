---
name: sync-bilingual-md
description: Align paired English and Chinese Markdown files using explicit change markers instead of semantic comparison. Use when the user asks to sync bilingual Markdown, align English and Chinese docs, process marked additions or deletions, reconcile Markdown files where Chinese files usually use a -CN suffix, or update both sides after deciding how marked changes should be applied.
---

# Sync Bilingual Markdown

## Goal

Align English and Chinese Markdown file pairs by processing explicit user-marked change regions. Do not semantically compare unmarked content. Find marked additions and deletions, ask the user how each marked change should affect the counterpart file, then edit both files and remove resolved markers.

## Core Rules

- Prioritize the user's pairing rule: `name.md` pairs with `name-CN.md` in the same folder.
- Be slightly flexible only for discovery: propose likely pairs with normalized basenames, case-insensitive matches, or nearby folders when exact pairs are incomplete.
- Confirm detected pairs, missing counterparts, and uncertain suggested pairs with the user before reading deeply or editing.
- Use explicit markers as the only source of change intent. Do not search for or resolve unmarked semantic differences.
- Ask about one marker group at a time.
- After each user decision, update both Markdown files and remove resolved marker wrappers before moving to the next marker group.
- Do not silently choose English or Chinese as the source of truth.
- Do not drop content unless the user explicitly decides to remove it.
- Preserve Markdown structure, code fences, links, tables, frontmatter, comments, and formatting unless the user decides otherwise.
- Do not support nested markers. Treat nested markers as parse errors that must be resolved before editing that group.

## Marker Syntax

Support inline and multi-line markers:

- Addition starts with `+++` and ends with `/+++`.
- Deletion starts with `---` and ends with `/---`.

Examples:

```markdown
This line has +++new text/+++ inline.

+++
New paragraph or list item.
/+++

---
Text intended for deletion.
/---
```

Markers indicate where the user made or proposed a change in one side of a bilingual pair. The marked region is the only content that should be queued for sync decisions.

## Discovery

Run the helper script first:

```bash
python3 <skill-dir>/scripts/scan_bilingual_md.py <folder>
```

Use the script output to present:

- Exact pairs from `name.md` and `name-CN.md`.
- English files missing Chinese counterparts.
- Chinese files missing English counterparts.
- Uncertain suggested pairs from flexible matching.
- Marker groups found in each file.
- Marker parse errors, such as unclosed markers, closing markers without openers, or nested markers.

Before processing markers or editing files, ask the user to confirm the pair list. Include uncertain suggestions separately and ask whether to include or exclude them.

## Resolution Workflow

1. Identify the target folder from the user request. Ask for it if missing.
2. Run `scripts/scan_bilingual_md.py <folder>`.
3. Present exact pairs, missing counterparts, uncertain suggestions, marker counts, and parse errors to the user.
4. Wait for the user to confirm which pairs to process.
5. If confirmed pairs contain marker parse errors, ask the user how to fix those marker syntax errors before editing marked content.
6. Read each confirmed pair.
7. Create an internal queue from marker groups only.
8. Ask the user about the first unresolved marker group.
9. Offer clear choices: apply this change to the counterpart file, keep only the counterpart version and remove this marked change, merge manually with user-provided text, or skip for now.
10. Apply the user's decision to both files, translating or adapting the counterpart as needed.
11. Remove marker wrappers for resolved changes.
12. Continue one marker group at a time until all confirmed pairs are aligned or the user stops.
13. Final response: summarize changed files, skipped marker groups, missing counterparts, parse errors, and any remaining blockers.

## User Prompts

For pair confirmation, use a concise prompt:

```markdown
I found these Markdown pairs:
- `guide.md` <-> `guide-CN.md` (2 marker groups)

Missing counterparts:
- `api.md` has no `api-CN.md`

Uncertain suggested pairs:
- `setup-guide.md` <-> `setup_CN.md`

Please confirm which pairs to process.
```

For each marker group, show only enough context to decide:

```markdown
Pair: `guide.md` <-> `guide-CN.md`
File: `guide.md`
Section: `## Install`
Marker: addition
Preview:
```text
Run the setup command before starting the server.
```

How should this marked change be synced?
- Apply this change to the counterpart file
- Keep only the counterpart version and remove this marked change
- Merge manually with this text: ...
- Skip for now
```

## Editing Rules

- Use structured Markdown edits where possible.
- Keep code blocks byte-for-byte unless the user chooses to change them or the counterpart is missing the block.
- Translate only the marked content required to align the pair.
- Preserve document-specific terminology consistently across both files.
- If the user chooses to apply a marked addition, add the corresponding translated content to the counterpart file and remove the markers from the source file.
- If the user chooses to apply a marked deletion, remove or update the corresponding content in the counterpart file and remove the marked deleted content from the source file unless the user instructs otherwise.
- If the user chooses to keep the counterpart version, remove the marked source-side change or restore the source side to match the counterpart.
- If the user chooses merge, combine both meanings without duplicating content.
- If the correct alignment is unclear after the user's answer, ask a focused follow-up before editing.

## Helper Script

Use `scripts/scan_bilingual_md.py` for read-only discovery, headings, marker groups, and marker parse errors. The script does not modify files and does not perform semantic translation comparison. Codex remains responsible for reading confirmed pairs, presenting marker groups, applying user decisions, and removing resolved markers.
