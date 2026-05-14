<p>
  <img src="assets/images/logo.png" alt="jg-lint" width="100">
</p>

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
git clone https://github.com/giacosoft/jg-lint.git
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

Output looks like:

```
src/app.py:12:1: MY001 TODO comments should be tracked as issues
src/app.py:45:1: MY001 TODO comments should be tracked as issues

Found 2 violation(s)
```

Exit code is `1` if any violations are found, `0` otherwise.

### Inline suppression

Suppress specific rules on a line with `# noqa`:

```python
x = something()  # noqa: MY001
y = another()  # noqa: MY001, MY002
```

## Configuration

All configuration lives in `pyproject.toml` under `[tool.jg-lint]`:

```toml
[tool.jg-lint]
select = ["MY"]              # only run rules matching these prefixes (empty = all)
ignore = ["MY002"]           # skip these rules globally
exclude = [".venv/**", "build/**"]
plugins = ["my_rules"]       # Python modules containing custom rules

[tool.jg-lint.per-file-ignores]
"tests/**" = ["MY001"]       # skip MY001 in test files
```

## Writing custom rules

### 1. Create a rule module

```python
# my_rules.py (or my_rules/__init__.py)
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

### 2. Register the plugin

Add the module to `pyproject.toml`:

```toml
[tool.jg-lint]
plugins = ["my_rules"]
```

Make sure the module is importable (installed or on `PYTHONPATH`).

### 3. Run

```bash
jg-lint check src/
```

```
src/app.py:3:1: MY001 TODO comments should be tracked as issues
src/utils.py:17:1: MY001 TODO comments should be tracked as issues

Found 2 violation(s)
```
