---
name: connect-github-account
description: Guide and assist a user through connecting the local machine to a GitHub account with SSH. Use when the user asks to connect a GitHub account, set up GitHub SSH authentication, create or add an SSH key to GitHub, verify SSH access with GitHub, fix GitHub SSH permission errors, or prepare Git to push and pull GitHub repositories over SSH.
---

# Connect GitHub Account

## Goal

Connect the user's local machine to their GitHub account with SSH. Execute safe local inspection and setup commands when possible, and give clear user-facing instructions for steps that must happen in the GitHub website.

## Core Rules

- Prefer agent-assisted setup: run local checks and safe setup commands when they do not expose secrets or overwrite user state.
- Never print, copy, upload, summarize, or inspect private key contents.
- Only show public key contents from files ending in `.pub`.
- Never overwrite an existing SSH key.
- If usable SSH keys already exist, ask before generating a new key.
- Ask before changing existing global Git identity values.
- Do not store GitHub passwords, personal access tokens, recovery codes, or two-factor authentication secrets.
- Explain GitHub website steps clearly, because Codex cannot complete them for the user in the browser unless a connected browser tool is explicitly available.
- Treat `Permission denied (publickey)` and `Hi USERNAME! You've successfully authenticated...` as normal verification outputs, not as reasons to expose secrets.
- For every pause or final reply after running commands or waiting for user action, read and follow `../shared/command-response-template.md`.

## Step 1: Inspect Local Prerequisites

Run these local checks first:

```bash
git --version
ssh -V
git config --global --get user.name
git config --global --get user.email
ls -la ~/.ssh
```

Interpret results:

- If `git` is missing, tell the user to install Git before continuing.
- If `ssh` is missing, tell the user to install OpenSSH before continuing.
- If Git identity values are missing, ask for the user's preferred Git commit name and email before setting them.
- If Git identity values already exist, report them and do not change them unless the user asks.
- If `~/.ssh` does not exist, create it with `mkdir -p ~/.ssh && chmod 700 ~/.ssh`.

## Step 2: Choose Or Create An SSH Key

Look for existing public keys:

```bash
ls -la ~/.ssh/*.pub
```

Prefer keys in this order:

1. `id_ed25519.pub`
2. Other `*.pub` keys whose matching private key exists and is not obviously unrelated.
3. A newly generated `ed25519` key.

If an existing suitable key is present, ask whether to use it. If no suitable key exists, ask for the GitHub email address to use as the key comment, then generate:

```bash
ssh-keygen -t ed25519 -C "<github-email>"
```

Use the default key path unless the user requests a custom path. Recommend a passphrase, but allow the user to choose.

## Step 3: Start SSH Agent And Add The Key

Check the agent and loaded identities:

```bash
ssh-add -l
```

If the agent is not running, start it:

```bash
eval "$(ssh-agent -s)"
```

Add the selected private key:

```bash
ssh-add ~/.ssh/id_ed25519
```

Adjust the filename if a different key was selected. If the key has a passphrase, let the user enter it interactively.

## Step 4: Give The User The Public Key For GitHub

Show only the selected public key:

```bash
cat ~/.ssh/id_ed25519.pub
```

Then instruct the user:

1. Open GitHub in a browser.
2. Go to `Settings`.
3. Open `SSH and GPG keys`.
4. Choose `New SSH key`.
5. Use a recognizable title for this machine.
6. Paste the full public key output.
7. Save the key.

Pause until the user confirms the key was added.

## Step 5: Verify GitHub SSH Authentication

Run:

```bash
ssh -T git@github.com
```

Expected successful result:

```text
Hi <username>! You've successfully authenticated, but GitHub does not provide shell access.
```

If prompted about host authenticity, explain that `github.com` should be accepted only when the user intended to connect to GitHub, then let the user confirm.

## Step 6: Configure Git Identity When Needed

Only set missing values, or update values after user confirmation:

```bash
git config --global user.name "<name>"
git config --global user.email "<email>"
```

Verify:

```bash
git config --global --get user.name
git config --global --get user.email
```

## Step 7: Optional Repository SSH Remote Check

If the user also wants to use an existing repository over SSH, inspect its remote:

```bash
git remote -v
```

For GitHub SSH remotes, use:

```bash
git@github.com:OWNER/REPO.git
```

Do not change repository remotes unless the user asks. If they ask to connect the current folder to a GitHub repository, use the `connect-folder-to-github` skill when available.

## Troubleshooting

Use these patterns:

- `Permission denied (publickey)`: the key is not loaded, the wrong key is selected, or the public key is not added to GitHub.
- `The agent has no identities`: run `ssh-add <private-key-path>`.
- `Could not open a connection to your authentication agent`: start `ssh-agent`.
- `Repository not found`: SSH authentication may work, but the GitHub account may not have access to that repository.
- Repeated passphrase prompts: confirm the key was added to `ssh-agent`.
- Network timeout: report network or firewall limits and ask the user to retry from a network that can reach GitHub SSH.

## Final Report

After successful setup or when pausing for user action, follow `../shared/command-response-template.md`.

For this skill, include these task-specific details under `What I Did` when available:

- Whether Git and SSH are installed.
- Which public key file was used.
- Whether the key was added to `ssh-agent`.
- Whether GitHub SSH authentication succeeded.
- Whether Git identity is configured.

For this skill, include these task-specific details under `What You Need To Do` when applicable:

- GitHub website steps that the user must complete.
- Any confirmation needed before generating keys or changing existing Git config.
- Any remaining manual action or blocker.

Keep the final report concise and never include private key material.
