# Setup Collaboration Workflow

Use this workflow for setup and configuration tasks before applying any task-specific steps.

1. Restate the task in operational terms: desired outcome, affected system or service, current known state, constraints, and what success will look like.
2. Discover local facts before asking: inspect relevant files, command availability, existing config, service state, routes, environment variables, tool versions, logs, or documentation already present in the workspace.
3. Ask only for intent, credentials, confirmations, UI/browser actions, admin privileges, account access, or environment details that cannot be discovered safely.
4. Perform safe, scoped actions within the active sandbox, permission, network, credential, and OS limits.
5. Verify the result when possible with read-only checks, dry runs, status commands, connectivity tests, or config inspection.
6. Clearly distinguish completed Codex work from user-required work.

## Boundaries

- Do not imply that a user-side setting, browser action, credential step, privileged command, or live service change has been completed unless it actually was.
- Do not expose secrets, tokens, private keys, passwords, recovery codes, or credential values.
- Do not make destructive or broad configuration changes without explicit user direction.
- When a command is blocked by sandboxing, missing permissions, unavailable network, or missing credentials, report the blocker and the smallest next action needed.
- Prefer reversible, inspectable changes and explain any risk before asking the user to perform a privileged action.

## Response Format

For every pause or final reply after executing commands, checking local state, changing configuration, or waiting for user action, read and follow `command-response-template.md`.

If the task is fully complete and the user has no remaining action, reply with a concise completion summary instead of the template.
