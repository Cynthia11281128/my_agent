---
name: md-translate-pair-cn
description: Translate English Markdown files into paired Chinese Markdown files without modifying the English source. Use when the user provides or points to an English .md file and wants a sibling -CN.md file created or updated in the same directory, preserving Markdown structure while producing clear Chinese prose.
---

# Markdown Paired Chinese Translation

## Goal

Create a Chinese Markdown counterpart for an English Markdown source file. Keep the English source file unchanged and write the Chinese translation to a sibling file named `<source-stem>-CN.md`.

## Workflow

1. Identify the English source `.md` file. If the target is ambiguous, ask a focused question before editing.
2. If the provided path already ends in `-CN.md`, ask for the English source file instead.
3. Derive the output path in the same directory by appending `-CN` before the `.md` suffix, for example `README.md` -> `README-CN.md`.
4. If the output file already exists, ask before overwriting or updating it.
5. Read the whole source document before translating so terminology, tone, and repeated phrases stay consistent.
6. Write the complete Chinese Markdown document to the derived output path.
7. After editing, summarize the source and output paths and mention any content intentionally left untranslated.

## Translation Rules

- Translate English prose into natural, concise Chinese while preserving the author's meaning.
- Do not summarize, embellish, reorganize, or add new content unless explicitly requested.
- Keep established technical terms, product names, proper nouns, paths, commands, identifiers, API names, and option names stable.
- Preserve intentionally bilingual labels or glossary-style terms when both languages are needed for meaning.
- If an English phrase is ambiguous and the surrounding context does not resolve it, choose the most direct reading and note the assumption in the final response.

## Markdown Preservation

- Preserve headings, lists, tables, blockquotes, links, images, footnotes, frontmatter, HTML comments, and overall section order.
- Keep code fences, inline code, command examples, config snippets, data samples, and machine-readable blocks byte-for-byte unless prose inside comments clearly needs translation.
- Preserve link URLs and image paths exactly. Translate link text only when it is ordinary prose.
- Keep table alignment and column meanings intact while translating prose cells.
- Avoid rewrapping large sections unless necessary for readability or the existing file style already wraps prose consistently.
