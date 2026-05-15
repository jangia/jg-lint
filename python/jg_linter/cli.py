from __future__ import annotations

import argparse
import importlib
import sys
import tomllib
from pathlib import Path

from jg_linter._internal import Violation, check_files
from jg_linter.plugin import Rule


def discover_plugins(config_path: str | None = None) -> list[Rule]:
    config_dir = Path(config_path or ".").resolve()
    pyproject_path = config_dir / "pyproject.toml"
    if not pyproject_path.exists():
        return []

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    rules_path = data.get("tool", {}).get("jg-linter", {}).get("rules_path")
    if not rules_path:
        return []

    rules_dir = (config_dir / rules_path).resolve()
    if not rules_dir.is_dir():
        raise FileNotFoundError(f"rules_path does not exist: {rules_dir}")

    module_names: list[str] = []
    for entry in sorted(rules_dir.iterdir()):
        if entry.name.startswith("_"):
            continue
        if entry.is_dir() and (entry / "__init__.py").exists():
            module_names.append(entry.name)
        elif entry.is_file() and entry.suffix == ".py":
            module_names.append(entry.stem)

    rules: list[Rule] = []
    rules_dir_str = str(rules_dir)
    added_to_path = rules_dir_str not in sys.path
    if added_to_path:
        sys.path.insert(0, rules_dir_str)
    try:
        for name in module_names:
            mod = importlib.import_module(name)
            if hasattr(mod, "get_rules"):
                rules.extend(mod.get_rules())
    finally:
        if added_to_path:
            sys.path.remove(rules_dir_str)

    return rules


def format_text(violations: list[Violation]) -> str:
    if not violations:
        return "ok: all checks passed"

    lines: list[str] = []
    for v in violations:
        lines.append(f"{v.file_path}:{v.line}:{v.col}: {v.code} {v.message}")
    lines.append(f"\nFound {len(violations)} violation(s)")
    return "\n".join(lines)


def run(paths: list[str], python_rules: list[Rule], config_path: str | None) -> int:
    violations = check_files(paths, python_rules, config_path)
    print(format_text(violations))
    return 1 if violations else 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="jg-lint", description="Extensible Python linter"
    )
    sub = parser.add_subparsers(dest="command")

    check_parser = sub.add_parser("check", help="Lint Python files")
    check_parser.add_argument("paths", nargs="+", help="Files or directories to lint")
    check_parser.add_argument(
        "--config", default=None, help="Path to directory containing pyproject.toml"
    )

    args = parser.parse_args()

    if args.command != "check":
        parser.print_help()
        sys.exit(2)

    python_rules = discover_plugins(args.config)
    sys.exit(run(args.paths, python_rules, args.config))
