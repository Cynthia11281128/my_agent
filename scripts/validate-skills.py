#!/usr/bin/env python3
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL_ROOTS = (ROOT / "skills", ROOT / "private" / "skills")


def validate_root(skills_root: pathlib.Path) -> bool:
    if not skills_root.exists():
        return True
    ok = True
    for skill_dir in sorted(p for p in skills_root.iterdir() if p.is_dir()):
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue

        text = skill_file.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            print(f"{skill_dir.relative_to(ROOT)}: missing YAML frontmatter", file=sys.stderr)
            ok = False
            continue

        match = re.match(r"---\n(.*?)\n---\n", text, re.S)
        if not match:
            print(f"{skill_dir.relative_to(ROOT)}: malformed YAML frontmatter", file=sys.stderr)
            ok = False
            continue

        frontmatter = match.group(1)
        if not re.search(r"^name:\s*\S+", frontmatter, re.M):
            print(f"{skill_dir.relative_to(ROOT)}: missing name", file=sys.stderr)
            ok = False
        if not re.search(r"^description:\s*.+", frontmatter, re.M):
            print(f"{skill_dir.relative_to(ROOT)}: missing description", file=sys.stderr)
            ok = False
    return ok


def main() -> int:
    if not (ROOT / "skills").exists():
        print("Missing skills/ directory", file=sys.stderr)
        return 1

    ok = True
    for skills_root in SKILL_ROOTS:
        ok = validate_root(skills_root) and ok

    if ok:
        print("All skills passed basic validation.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
