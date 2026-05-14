from __future__ import annotations

import argparse
import importlib
import sys
import tomllib
from pathlib import Path

from jg_linter._internal import Violation, check_files
from jg_linter.plugin import Rule


def discover_plugins(config_path: str | None = None) -> list[Rule]:
    pyproject_path = Path(config_path or ".") / "pyproject.toml"
    if not pyproject_path.exists():
        return []

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    plugin_modules = data.get("tool", {}).get("jg-linter", {}).get("plugins", [])
    rules: list[Rule] = []
    for module_path in plugin_modules:
        mod = importlib.import_module(module_path)
        if hasattr(mod, "get_rules"):
            rules.extend(mod.get_rules())

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
