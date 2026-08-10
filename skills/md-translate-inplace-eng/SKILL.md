---
name: md-translate-inplace-eng
description: Translate Chinese prose in Markdown files into English in place and lightly correct existing English grammar. Use when the user provides or points to .md content and wants the original Markdown file edited directly, converting Chinese portions to concise, clear, mostly literal English while only fixing English text that is grammatically wrong, awkward, or unclear without broad rewriting.
---

# Markdown In-Place English Translation

## Goal

Convert Markdown content to clean English in the original file while preserving the document's structure and intent. Translate Chinese prose directly, concisely, and clearly. For existing English prose, only fix grammar, fluency, and obvious wording problems.

## Workflow

1. Identify the target Markdown file or pasted Markdown content. If the target is ambiguous, ask a focused question before editing.
2. Read the whole document before changing it so terminology, tone, and repeated phrases stay consistent.
3. Translate Chinese prose into English in place.
4. Lightly correct existing English only where it is ungrammatical, awkward, or unclear.
5. Preserve Markdown formatting and non-prose content unless the user explicitly asks to change it.
6. After editing, summarize the files changed and mention any content intentionally left untouched.

## Translation Rules

- Keep Chinese-to-English translation mostly literal, but make the English concise and clear.
- Do not embellish, summarize, reorganize, or change the author's meaning.
- Do not apply broad style rewrites to English that is already acceptable.
- Keep established technical terms, product names, proper nouns, paths, commands, identifiers, API names, and option names stable.
- Preserve intentionally bilingual labels or glossary-style terms when both languages are needed for meaning.
- If a Chinese phrase is ambiguous and the surrounding context does not resolve it, choose the most direct reading and note the assumption in the final response.

## Markdown Preservation

- Preserve headings, lists, tables, blockquotes, links, images, footnotes, frontmatter, HTML comments, and overall section order.
- Keep code fences, inline code, command examples, config snippets, and data samples byte-for-byte unless surrounding prose inside comments clearly needs translation.
- Preserve link URLs and image paths exactly. Translate link text only when it is ordinary prose.
- Keep table alignment and column meanings intact while translating prose cells.
- Avoid rewrapping large sections unless necessary for readability or the existing file style already wraps prose consistently.
