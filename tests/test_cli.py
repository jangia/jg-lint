import subprocess
import sys

import pytest

from jg_linter._internal import Violation
from jg_linter.cli import discover_plugins, format_text, run


class TestFormatText:
    def test_no_violations(self):
        assert format_text([]) == "ok: all checks passed"

    def test_single_violation(self):
        v = Violation("foo.py", 1, 0, "JG001", "bad")
        output = format_text([v])
        assert "foo.py:1:0: JG001 bad" in output
        assert "Found 1 violation(s)" in output

    def test_multiple_violations(self):
        vs = [
            Violation("a.py", 1, 0, "JG001", "bad"),
            Violation("b.py", 2, 0, "JG002", "worse"),
        ]
        output = format_text(vs)
        assert "a.py:1:0: JG001 bad" in output
        assert "b.py:2:0: JG002 worse" in output
        assert "Found 2 violation(s)" in output


RULE_TEMPLATE = """\
from jg_linter.plugin import Rule

class R(Rule):
    code = "{code}"
    message = "rule"
    def check(self, file_path, content):
        return []

def get_rules():
    return [R()]
"""


class TestDiscoverPlugins:
    def test_no_pyproject(self, tmp_path):
        rules = discover_plugins(str(tmp_path))
        assert rules == []

    def test_no_rules_path_configured(self, tmp_project):
        root = tmp_project(pyproject="[tool.jg-linter]\n")
        assert discover_plugins(str(root)) == []

    def test_rules_path_missing_raises(self, tmp_project):
        root = tmp_project(pyproject="""\
[tool.jg-linter]
rules_path = "./nope"
""")
        with pytest.raises(FileNotFoundError):
            discover_plugins(str(root))

    def test_loads_top_level_py_file(self, tmp_project):
        root = tmp_project(pyproject="""\
[tool.jg-linter]
rules_path = "rules"
""")
        rules_dir = root / "rules"
        rules_dir.mkdir()
        (rules_dir / "my_rule.py").write_text(RULE_TEMPLATE.format(code="MY001"))

        rules = discover_plugins(str(root))
        assert [r.code for r in rules] == ["MY001"]
        assert str(rules_dir.resolve()) not in sys.path

    def test_loads_package(self, tmp_project):
        root = tmp_project(pyproject="""\
[tool.jg-linter]
rules_path = "rules"
""")
        pkg = root / "rules" / "my_pkg"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text(RULE_TEMPLATE.format(code="PKG001"))

        rules = discover_plugins(str(root))
        assert [r.code for r in rules] == ["PKG001"]

    def test_loads_multiple_modules(self, tmp_project):
        root = tmp_project(pyproject="""\
[tool.jg-linter]
rules_path = "rules"
""")
        rules_dir = root / "rules"
        rules_dir.mkdir()
        (rules_dir / "a.py").write_text(RULE_TEMPLATE.format(code="A001"))
        (rules_dir / "b.py").write_text(RULE_TEMPLATE.format(code="B001"))

        codes = {r.code for r in discover_plugins(str(root))}
        assert codes == {"A001", "B001"}

    def test_skips_underscore_prefixed(self, tmp_project):
        root = tmp_project(pyproject="""\
[tool.jg-linter]
rules_path = "rules"
""")
        rules_dir = root / "rules"
        rules_dir.mkdir()
        (rules_dir / "_helpers.py").write_text("x = 1\n")
        (rules_dir / "real.py").write_text(RULE_TEMPLATE.format(code="R001"))

        rules = discover_plugins(str(root))
        assert [r.code for r in rules] == ["R001"]

    def test_module_without_get_rules_ignored(self, tmp_project):
        root = tmp_project(pyproject="""\
[tool.jg-linter]
rules_path = "rules"
""")
        rules_dir = root / "rules"
        rules_dir.mkdir()
        (rules_dir / "empty.py").write_text("x = 1\n")
        assert discover_plugins(str(root)) == []


class TestRun:
    def test_returns_zero_no_violations(self, tmp_project, capsys):
        root = tmp_project(files={"app.py": "x = 1\n"})
        code = run([str(root)], [], str(root))
        assert code == 0
        assert "all checks passed" in capsys.readouterr().out

    def test_returns_one_with_violations(self, tmp_project, capsys):
        root = tmp_project(files={"app.py": "x = 1\n"})

        from jg_linter.plugin import Rule

        class Fail(Rule):
            code = "F001"
            message = "fail"

            def check(self, file_path, content):
                return [Violation(file_path, 1, 0, self.code, self.message)]

        code = run([str(root)], [Fail()], str(root))
        assert code == 1
        assert "F001" in capsys.readouterr().out


class TestMainEntrypoint:
    def test_no_command_exits_2(self):
        result = subprocess.run(
            [sys.executable, "-m", "jg_linter"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 2

    def test_check_clean_file(self, tmp_project):
        root = tmp_project(files={"app.py": "x = 1\n"})
        result = subprocess.run(
            [sys.executable, "-m", "jg_linter", "check", str(root)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "all checks passed" in result.stdout
