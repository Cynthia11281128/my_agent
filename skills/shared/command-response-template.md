# Command Response Template

Use this template for user-facing replies after executing commands, checking local state, changing configuration, or pausing for user action when the task still needs user input or manual action.

If the task is fully complete and the user has no remaining action, do not use this template. Reply with a concise completion summary instead.

```markdown
**What I Did**
- [Actions actually completed by Codex: commands run, checks performed, files inspected, configuration changed, or verification completed.]

**What You Need To Do**
- [Actions required from the user: confirmations, browser steps, credentials, manual commands, choices, blockers, or remaining work.]

**Why This Matters**
- [Explain why the user action is needed and what Codex will do next with the confirmation, information, credential state, browser action, or command result.]
```

## Rules

- Include all three sections in this order when using the template.
- Put only actions actually completed by Codex under `What I Did`.
- Put user actions, decisions, confirmations, manual steps, credentials, blockers, and remaining work under `What You Need To Do`.
- Use `Why This Matters` to explain the purpose of the user's TODOs, such as what they unblock, what risk they avoid, or how Codex will use the user's response or completed browser action.
- Use `Nothing.` only when a section truly has no items.
- Keep the reply concise and task-focused.
- Do not claim a command was run unless it was actually run.
- Do not expose secrets, private keys, tokens, passwords, recovery codes, or credential values.
- Summarize command output instead of pasting long raw output unless the user explicitly asks for it.
