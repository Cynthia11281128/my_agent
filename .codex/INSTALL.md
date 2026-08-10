# Installing My Agent Skills For Codex

## Install All Skills

```bash
git clone <your-repo-url> ~/.codex/my_agent
mkdir -p ~/.agents/skills
for skill in ~/.codex/my_agent/skills/*/; do
  ln -sf "$skill" ~/.agents/skills/$(basename "$skill")
done
```

Restart Codex after installing.

## Install From This Local Checkout

```bash
cd /home/cynthia/tools/my_agent
./scripts/install-skills.sh
```

## Update

If installed from a git clone:

```bash
cd ~/.codex/my_agent
git pull
```

If installed from this local checkout, symlinks already point at the latest files.

## Uninstall

```bash
for skill in ~/.agents/skills/*; do
  case "$(readlink "$skill")" in
    *my_agent*) rm "$skill" ;;
  esac
done
```
