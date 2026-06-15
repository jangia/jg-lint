from __future__ import annotations

import argparse
import importlib
import importlib.util
import inspect
import sys
import tomllib
from pathlib import Path
from types import ModuleType

from jg_linter._internal import Violation, check_files
from jg_linter.plugin import Rule


def _collect_rules(mod: ModuleType) -> list[Rule]:
    if hasattr(mod, "get_rules"):
        return list(mod.get_rules())
    rules: list[Rule] = []
    for _, obj in inspect.getmembers(mod, inspect.isclass):
        if obj is Rule or not issubclass(obj, Rule):
            continue
        if obj.__module__ != mod.__name__:
            continue
        try:
            rules.append(obj())
        except Exception as exc:
            print(
                f"warning: failed to instantiate {obj.__name__} from {mod.__name__}: {exc}",
                file=sys.stderr,
            )
    return rules


_PKG_NAME = "_jg_lint_user_rules"


def _import_at(name: str, path: Path) -> ModuleType | None:
    submod_search = [str(path.parent)] if path.name == "__init__.py" else None
    spec = importlib.util.spec_from_file_location(
        name, path, submodule_search_locations=submod_search
    )
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:
        print(f"warning: failed to import {path}: {exc}", file=sys.stderr)
        sys.modules.pop(name, None)
        return None
    return mod


def _load_package(rules_dir: Path) -> list[Rule]:
    pkg = _import_at(_PKG_NAME, rules_dir / "__init__.py")
    if pkg is None:
        return []
    rules: list[Rule] = []
    seen: set[type] = set()

    def add(new: list[Rule]) -> None:
        for r in new:
            if type(r) in seen:
                continue
            seen.add(type(r))
            rules.append(r)

    add(_collect_rules(pkg))
    for entry in sorted(rules_dir.iterdir()):
        if entry.name.startswith("_") or entry.suffix != ".py":
            continue
        submod_name = f"{_PKG_NAME}.{entry.stem}"
        submod = sys.modules.get(submod_name) or _import_at(submod_name, entry)
        if submod is not None:
            add(_collect_rules(submod))
    return rules


def discover_plugins(config_path: str | None = None) -> list[Rule]:
    config_dir = Path(config_path or ".").resolve()
    pyproject_path = config_dir / "pyproject.toml"
    if not pyproject_path.exists():
        return []

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    tool = data.get("tool", {})
    section = tool.get("jg-lint") or tool.get("jg-linter") or {}
    rules_path = section.get("rules_path")
    if not rules_path:
        return []

    rules_dir = (config_dir / rules_path).resolve()
    if not rules_dir.is_dir():
        raise FileNotFoundError(f"rules_path does not exist: {rules_dir}")

    if (rules_dir / "__init__.py").exists():
        return _load_package(rules_dir)

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
            try:
                mod = importlib.import_module(name)
            except Exception as exc:
                print(
                    f"warning: failed to import plugin module {name} from {rules_dir}: {exc}",
                    file=sys.stderr,
                )
                continue
            rules.extend(_collect_rules(mod))
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
    parser = argparse.ArgumentParser(prog="jg-lint", description="Extensible Python linter")
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
