# Codex Resume Error Fix

## Settings / Inputs

This workflow applies when Codex fails to resume a session because the target thread already has an active writer.

Inputs:

- `<codex-session-jsonl>`: the session JSONL file shown in the resume error.
- `<stale-codex-pids>`: the Codex process IDs that still hold the session file open.

Required tools:

- `lsof`
- `ps`
- `kill`

## Task Description

Resolve a Codex TUI resume failure caused by a stale Codex process still holding write access to the session JSONL file, without deleting or modifying the session file.

## Workflow Summary

1. Copy the session JSONL path from the resume error.
2. Check which process is holding the session file open:

   ```bash
   lsof <codex-session-jsonl>
   ```

3. Identify the relevant Codex process IDs from the `lsof` output.
4. Inspect those processes and their parent/terminal relationship:

   ```bash
   ps -o pid,ppid,tty,stat,lstart,cmd -p <stale-codex-pids>
   ```

5. Confirm the listed processes are the stale Codex/TUI process group for the failed resume target, not the current active session.
6. Terminate only the stale writer processes with a normal termination signal:

   ```bash
   kill -TERM <stale-codex-pids>
   ```

7. Wait briefly, then confirm the process IDs have exited:

   ```bash
   ps -o pid,ppid,tty,stat,lstart,cmd -p <stale-codex-pids>
   ```

8. Confirm the session file is no longer held open:

   ```bash
   lsof <codex-session-jsonl>
   ```

9. Retry the Codex resume operation.

## Verification

- `lsof <codex-session-jsonl>` initially showed a Codex process holding the session file open.
- `ps -o pid,ppid,tty,stat,lstart,cmd -p <stale-codex-pids>` confirmed the holder belonged to the stale Codex/TUI process group.
- After `kill -TERM <stale-codex-pids>`, `ps` no longer listed those processes.
- A final `lsof <codex-session-jsonl>` produced no holder output.

## Final State

- The stale Codex writer was stopped.
- The session JSONL file was left in place and was not deleted or edited.
- The active-writer conflict was cleared, so the session could be resumed again.

## Failed Attempts / Notes

- Do not delete the session JSONL file to fix this error.
- Prefer `kill -TERM` first. Use stronger signals only if the stale process does not exit.
- Multiple Codex processes may be running; verify the exact file holder before terminating anything.

## Placeholder Values

- `<codex-session-jsonl>`: the Codex session JSONL path from the resume error, under the user's Codex sessions directory.
- `<stale-codex-pids>`: `2261371 2261378`
