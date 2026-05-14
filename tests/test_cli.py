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


class TestDiscoverPlugins:
    def test_no_pyproject(self, tmp_path):
        rules = discover_plugins(str(tmp_path))
        assert rules == []

    def test_empty_plugins_list(self, tmp_project):
        root = tmp_project(pyproject="""\
[tool.jg-linter]
plugins = []
""")
        rules = discover_plugins(str(root))
        assert rules == []

    def test_missing_module_raises(self, tmp_project):
        root = tmp_project(pyproject="""\
[tool.jg-linter]
plugins = ["nonexistent_module_xyz"]
""")
        with pytest.raises(ModuleNotFoundError):
            discover_plugins(str(root))

    def test_loads_plugin_module(self, tmp_project, monkeypatch):
        root = tmp_project(pyproject="""\
[tool.jg-linter]
plugins = ["my_plugin"]
""")
        plugin_dir = root / "my_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "__init__.py").write_text("""\
from jg_linter.plugin import Rule
from jg_linter._internal import Violation

class MyRule(Rule):
    code = "MY001"
    message = "my rule"

    def check(self, file_path, content):
        return []

def get_rules():
    return [MyRule()]
""")
        monkeypatch.syspath_prepend(str(root))
        rules = discover_plugins(str(root))
        assert len(rules) == 1
        assert rules[0].code == "MY001"

    def test_module_without_get_rules_ignored(self, tmp_project, monkeypatch):
        root = tmp_project(pyproject="""\
[tool.jg-linter]
plugins = ["empty_plugin"]
""")
        plugin_dir = root / "empty_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "__init__.py").write_text("x = 1\n")
        monkeypatch.syspath_prepend(str(root))
        rules = discover_plugins(str(root))
        assert rules == []

    def test_multiple_plugins(self, tmp_project, monkeypatch):
        root = tmp_project(pyproject="""\
[tool.jg-linter]
plugins = ["plugin_a", "plugin_b"]
""")
        for name, code in [("plugin_a", "A001"), ("plugin_b", "B001")]:
            d = root / name
            d.mkdir()
            (d / "__init__.py").write_text(f"""\
from jg_linter.plugin import Rule
from jg_linter._internal import Violation

class R(Rule):
    code = "{code}"
    message = "rule"
    def check(self, file_path, content):
        return []

def get_rules():
    return [R()]
""")
        monkeypatch.syspath_prepend(str(root))
        rules = discover_plugins(str(root))
        codes = {r.code for r in rules}
        assert codes == {"A001", "B001"}


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
