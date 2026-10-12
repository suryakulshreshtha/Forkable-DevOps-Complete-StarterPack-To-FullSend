#!/usr/bin/env python3
"""Parse every YAML and JSON file in the repository and report syntax errors.

Helm templates are skipped because they contain Go template syntax and only
become YAML after `helm template` renders them (CI does that step).

Usage: python scripts/validate_files.py [root]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

SKIP_DIRS = {".git", ".venv", "venv", "node_modules", ".cache", ".terraform", "__pycache__"}
SKIP_PARTS = ("/templates/",)  # Helm templates


def iter_files(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    found = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in suffixes:
            continue
        if SKIP_DIRS.intersection(path.relative_to(root).parts):
            continue
        if any(part in path.as_posix() for part in SKIP_PARTS):
            continue
        found.append(path)
    return sorted(found)


def check(root: Path) -> list[str]:
    errors: list[str] = []
    for path in iter_files(root, (".yml", ".yaml")):
        try:
            list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
        except yaml.YAMLError as exc:
            errors.append(f"{path.relative_to(root)}: {exc}")
    for path in iter_files(root, (".json",)):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{path.relative_to(root)}: {exc}")
    return errors


def main(argv: list[str]) -> int:
    root = Path(argv[0] if argv else ".").resolve()
    errors = check(root)
    yaml_count = len(iter_files(root, (".yml", ".yaml")))
    json_count = len(iter_files(root, (".json",)))
    for e in errors:
        print(f"✗ {e}")
    print(f"checked {yaml_count} YAML and {json_count} JSON files: {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
