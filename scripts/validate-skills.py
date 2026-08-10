#!/usr/bin/env python3
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


def main() -> int:
    if not SKILLS.exists():
        print("Missing skills/ directory", file=sys.stderr)
        return 1

    ok = True
    for skill_dir in sorted(p for p in SKILLS.iterdir() if p.is_dir()):
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            print(f"{skill_dir.name}: missing SKILL.md", file=sys.stderr)
            ok = False
            continue

        text = skill_file.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            print(f"{skill_dir.name}: missing YAML frontmatter", file=sys.stderr)
            ok = False
            continue

        match = re.match(r"---\n(.*?)\n---\n", text, re.S)
        if not match:
            print(f"{skill_dir.name}: malformed YAML frontmatter", file=sys.stderr)
            ok = False
            continue

        frontmatter = match.group(1)
        if not re.search(r"^name:\s*\S+", frontmatter, re.M):
            print(f"{skill_dir.name}: missing name", file=sys.stderr)
            ok = False
        if not re.search(r"^description:\s*.+", frontmatter, re.M):
            print(f"{skill_dir.name}: missing description", file=sys.stderr)
            ok = False

    if ok:
        print("All skills passed basic validation.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
