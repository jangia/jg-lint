# jg-lint

Extensible Python linter with a Rust core.

## Installation

Requires Python 3.14+.

```bash
uv add jg-lint
```

or with pip:

```bash
pip install jg-lint
```

or with Poetry:

```bash
poetry add jg-lint
```

### Development install

To build from source, you need [Maturin](https://www.maturin.rs/) and a Rust toolchain:

```bash
git clone https://github.com/jangia/jg-lint.git
cd jg-lint
uv sync
uv run maturin develop
```

## Usage

```bash
jg-lint check <paths...>
```

Lint one or more files or directories:

```bash
jg-lint check src/
jg-lint check src/ lib/ main.py
jg-lint check --config path/to/project src/
```

The `--config` flag points to the directory containing `pyproject.toml` (defaults to `.`).

### Built-in rules

| Code  | Description                                         |
|-------|-----------------------------------------------------|
| JG001 | Imports must be at module top level                 |
| JG002 | `if` statements are not allowed in test functions (any function or method whose name starts with `test_`) |

All built-in rules are **enabled by default**. When `select` is empty (or omitted), every implemented built-in rule runs alongside any plugin rules. To narrow what runs, list rule codes explicitly in `select` (e.g. `select = ["JG001"]`) or silence individual rules via `ignore` / `per-file-ignores`.

If both `select` and `ignore` end up filtering out every rule, `jg-lint` prints a warning on stderr so you know nothing was actually checked.

Output looks like:

```
src/app.py:12:1: MY001 TODO comments should be tracked as issues
src/app.py:45:1: MY001 TODO comments should be tracked as issues

Found 2 violation(s)
```

Exit code is `1` if any violations are found, `0` otherwise.

### Inline suppression

Some rules opt in to per-line suppression via `# noqa`:

```python
x = something()  # noqa: MY001
y = another()  # noqa: MY001, MY002
```

By design, `# noqa` is **not** honored by default — rules must explicitly set `allow_noqa = True` to allow it. This keeps suppression intentional and reserved for cases where the rule author has decided it's acceptable.

## Configuration

All configuration lives in `pyproject.toml` under `[tool.jg-lint]` (the legacy `[tool.jg-linter]` section is still read as a fallback for backwards compatibility):

```toml
[tool.jg-lint]
select = ["MY001", "JG*"]    # rules to enable (see "Selecting rules" below)
ignore = ["MY002"]           # skip these rules globally
exclude = [".venv/**", "build/**"]
rules_path = "./rules"       # directory containing your custom rule modules

[tool.jg-lint.per-file-ignores]
"tests/**" = ["MY001"]       # skip MY001 in test files
```

### Selecting rules

Each entry in `select`, `ignore`, and `per-file-ignores` is matched against a rule's code with the following pattern semantics:

- `"*"` — matches every code.
- `"JG*"` — matches every code starting with `JG` (e.g. `JG001`, `JG042`).
- `"JG001"` — exact match.

Defaults when `select` is empty:

- **Every implemented built-in rule** (e.g. `JG001`, `JG002`) is enabled.
- **Every plugin rule** loaded from `rules_path` is enabled.

Use `ignore` (or `per-file-ignores`) to turn rules off, or set `select` explicitly to opt into a narrower subset.

## Writing custom rules

### 1. Create a rule module

Put it inside the directory you've configured as `rules_path` (e.g. `./rules/no_todo.py` or `./rules/no_todo/__init__.py`).

```python
from jg_linter import Rule, Violation


class NoTodoComments(Rule):
    code = "MY001"
    message = "TODO comments should be tracked as issues"

    def check(self, file_path: str, content: str) -> list[Violation]:
        violations = []
        for i, line in enumerate(content.splitlines(), 1):
            if "# TODO" in line:
                violations.append(
                    Violation(file_path, i, 1, self.code, self.message)
                )
        return violations


def get_rules() -> list[Rule]:
    return [NoTodoComments()]
```

Each rule needs:

- `code` -- unique identifier (e.g. `MY001`)
- `message` -- human-readable description
- `check(file_path, content)` -- returns a list of `Violation` objects

Set `test_only = True` on a rule to run it only against test files (files named `test_*.py`, `*_test.py`, or inside a `tests/` directory).

Set `allow_noqa = True` on a rule to allow inline `# noqa: CODE` suppression. Without this, the rule cannot be silenced per-line and can only be turned off project-wide via `ignore` or `per-file-ignores`.

### 2. Point `jg-lint` at the rules folder

```toml
[tool.jg-lint]
rules_path = "./rules"
```

Every top-level `.py` file and package inside `rules_path` is imported automatically; any module exposing `get_rules()` contributes rules. Files and folders starting with `_` are skipped. The rules directory is prepended to `sys.path` during loading, so no `PYTHONPATH` setup is needed.

### 3. Run

```bash
jg-lint check src/
```

```
src/app.py:3:1: MY001 TODO comments should be tracked as issues
src/utils.py:17:1: MY001 TODO comments should be tracked as issues

Found 2 violation(s)
```

## Contributing

You need a Rust toolchain (stable), Python 3.14+, and [`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/jangia/jg-lint.git
cd jg-lint
uv sync
uv run maturin develop
```

### Tests

```bash
cargo test                 # Rust unit tests
uv run pytest              # Python tests (rebuild with `maturin develop` if Rust changed)
bash scripts/e2e.sh        # CLI smoke test against fixtures in examples/
```

`examples/` contains one folder per built-in rule. Each folder has its own `pyproject.toml` that selects only that rule, plus `bad*.py` fixtures that must be flagged and `good*.py` fixtures that must not. `scripts/e2e.sh` greps the CLI output to confirm both halves; CI runs it on every push.

### Linting and formatting

Before opening a PR, run the same checks CI does:

```bash
# Rust
cargo fmt --all -- --check          # formatting
cargo clippy --all-targets -- -D warnings   # lints (fails on any warning)
cargo audit                          # CVEs in dependencies (install with `cargo install cargo-audit`)

# Python
uv run ruff check .                  # lint
uv run ruff format --check .         # format check
```

To auto-fix:

```bash
cargo fmt --all
cargo clippy --fix --all-targets
uv run ruff check --fix .
uv run ruff format .
```

### Releasing

Releases are driven by git tags of the form `vX.Y.Z`. To cut one:

1. Bump `version` in `pyproject.toml`, commit, and merge to `main`.
2. Tag `main` and push: `git tag vX.Y.Z && git push origin vX.Y.Z`.

Pushing the tag triggers `.github/workflows/release.yml`, which verifies the tag matches the `pyproject.toml` version, builds the sdist + wheels for all platforms, publishes to PyPI, and creates a GitHub Release with the artifacts and auto-generated notes attached. If the tag/version check fails the run aborts before anything is published.

## License

MIT — see [LICENSE](LICENSE).
