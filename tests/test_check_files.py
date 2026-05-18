from jg_linter._internal import Violation, check_files
from jg_linter.plugin import Rule


class TestCheckFilesNoRules:
    def test_clean_file(self, tmp_project):
        root = tmp_project(files={"app.py": "x = 1\n"})
        violations = check_files([str(root)], [], str(root))
        assert violations == []

    def test_empty_file(self, tmp_project):
        root = tmp_project(files={"empty.py": ""})
        violations = check_files([str(root)], [], str(root))
        assert violations == []

    def test_nonexistent_path(self, tmp_path):
        violations = check_files([str(tmp_path / "nope")], [], str(tmp_path))
        assert violations == []

    def test_single_file_path(self, tmp_project):
        root = tmp_project(files={"one.py": "x = 1\n"})
        violations = check_files([str(root / "one.py")], [], str(root))
        assert violations == []

    def test_non_python_files_ignored(self, tmp_project):
        root = tmp_project(files={"readme.txt": "hello", "app.py": "x = 1\n"})
        violations = check_files([str(root)], [], str(root))
        assert violations == []


class TestCheckFilesExclude:
    def test_venv_excluded_by_default(self, tmp_project):
        root = tmp_project(files={".venv/lib/thing.py": "x = 1\n", "app.py": "x = 1\n"})
        violations = check_files([str(root)], [], str(root))
        assert all(".venv" not in v.file_path for v in violations)

    def test_pycache_excluded_by_default(self, tmp_project):
        root = tmp_project(files={"__pycache__/mod.py": "x = 1\n"})
        violations = check_files([str(root)], [], str(root))
        assert violations == []

    def test_custom_exclude(self, tmp_project):
        pyproject = """\
[tool.jg-linter]
exclude = ["vendor/**"]
"""
        root = tmp_project(
            pyproject=pyproject,
            files={"vendor/lib.py": "x = 1\n", "app.py": "x = 1\n"},
        )
        violations = check_files([str(root)], [], str(root))
        assert all("vendor" not in v.file_path for v in violations)


class TestCheckFilesWithPythonRules:
    def test_plugin_rule_produces_violations(self, tmp_project):
        root = tmp_project(files={"app.py": "x = 1\n"})

        class AlwaysFail(Rule):
            code = "TEST001"
            message = "always fails"

            def check(self, file_path: str, content: str) -> list:
                return [Violation(file_path, 1, 0, self.code, self.message)]

        violations = check_files([str(root)], [AlwaysFail()], str(root))
        assert len(violations) == 1
        assert violations[0].code == "TEST001"

    def test_test_only_rule_skips_non_test_files(self, tmp_path):
        # Use a subdirectory whose name won't match is_test_file heuristics
        root = tmp_path / "proj"
        root.mkdir()
        src = root / "src"
        src.mkdir()
        (src / "app.py").write_text("x = 1\n")

        class TestOnlyRule(Rule):
            code = "TST001"
            message = "test only"
            test_only = True

            def check(self, file_path: str, content: str) -> list:
                return [Violation(file_path, 1, 0, self.code, self.message)]

        violations = check_files([str(src / "app.py")], [TestOnlyRule()], str(root))
        assert violations == []

    def test_test_only_rule_runs_on_test_files(self, tmp_path):
        root = tmp_path / "proj"
        root.mkdir()
        tests_dir = root / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_app.py").write_text("x = 1\n")

        class TestOnlyRule(Rule):
            code = "TST001"
            message = "test only"
            test_only = True

            def check(self, file_path: str, content: str) -> list:
                return [Violation(file_path, 1, 0, self.code, self.message)]

        violations = check_files([str(tests_dir / "test_app.py")], [TestOnlyRule()], str(root))
        assert len(violations) == 1

    def test_multiple_rules(self, tmp_project):
        root = tmp_project(files={"app.py": "x = 1\n"})

        class RuleA(Rule):
            code = "A001"
            message = "rule a"

            def check(self, file_path: str, content: str) -> list:
                return [Violation(file_path, 1, 0, self.code, self.message)]

        class RuleB(Rule):
            code = "B001"
            message = "rule b"

            def check(self, file_path: str, content: str) -> list:
                return [Violation(file_path, 2, 0, self.code, self.message)]

        violations = check_files([str(root)], [RuleA(), RuleB()], str(root))
        codes = {v.code for v in violations}
        assert codes == {"A001", "B001"}

    def test_multiple_files(self, tmp_project):
        root = tmp_project(files={"a.py": "x = 1\n", "b.py": "y = 2\n"})

        class AlwaysFail(Rule):
            code = "F001"
            message = "fail"

            def check(self, file_path: str, content: str) -> list:
                return [Violation(file_path, 1, 0, self.code, self.message)]

        violations = check_files([str(root)], [AlwaysFail()], str(root))
        paths = {v.file_path for v in violations}
        assert len(paths) == 2

    def test_rule_receives_file_content(self, tmp_project):
        root = tmp_project(files={"app.py": "magic_string_123\n"})
        received = {}

        class Spy(Rule):
            code = "SPY001"
            message = "spy"

            def check(self, file_path: str, content: str) -> list:
                received["content"] = content
                return []

        check_files([str(root)], [Spy()], str(root))
        assert "magic_string_123" in received["content"]


class TestCheckFilesNoqa:
    def test_noqa_suppresses_violation_when_rule_opts_in(self, tmp_project):
        root = tmp_project(files={"app.py": "x = 1  # noqa: TEST001\n"})

        class AlwaysFail(Rule):
            code = "TEST001"
            message = "fail"
            allow_noqa = True

            def check(self, file_path: str, content: str) -> list:
                return [Violation(file_path, 1, 0, self.code, self.message)]

        violations = check_files([str(root)], [AlwaysFail()], str(root))
        assert violations == []

    def test_noqa_does_not_suppress_when_rule_opts_out(self, tmp_project):
        root = tmp_project(files={"app.py": "x = 1  # noqa: TEST001\n"})

        class AlwaysFail(Rule):
            code = "TEST001"
            message = "fail"

            def check(self, file_path: str, content: str) -> list:
                return [Violation(file_path, 1, 0, self.code, self.message)]

        violations = check_files([str(root)], [AlwaysFail()], str(root))
        assert len(violations) == 1

    def test_noqa_wrong_code_does_not_suppress(self, tmp_project):
        root = tmp_project(files={"app.py": "x = 1  # noqa: OTHER001\n"})

        class AlwaysFail(Rule):
            code = "TEST001"
            message = "fail"
            allow_noqa = True

            def check(self, file_path: str, content: str) -> list:
                return [Violation(file_path, 1, 0, self.code, self.message)]

        violations = check_files([str(root)], [AlwaysFail()], str(root))
        assert len(violations) == 1

    def test_noqa_multiple_codes(self, tmp_project):
        root = tmp_project(files={"app.py": "x = 1  # noqa: A001, B001\n"})

        class RuleA(Rule):
            code = "A001"
            message = "a"
            allow_noqa = True

            def check(self, file_path: str, content: str) -> list:
                return [Violation(file_path, 1, 0, self.code, self.message)]

        class RuleB(Rule):
            code = "B001"
            message = "b"
            allow_noqa = True

            def check(self, file_path: str, content: str) -> list:
                return [Violation(file_path, 1, 0, self.code, self.message)]

        class RuleC(Rule):
            code = "C001"
            message = "c"
            allow_noqa = True

            def check(self, file_path: str, content: str) -> list:
                return [Violation(file_path, 1, 0, self.code, self.message)]

        violations = check_files([str(root)], [RuleA(), RuleB(), RuleC()], str(root))
        codes = [v.code for v in violations]
        assert "A001" not in codes
        assert "B001" not in codes
        assert "C001" in codes


class TestCheckFilesConfig:
    def test_select_filters_rules(self, tmp_project):
        pyproject = """\
[tool.jg-linter]
select = ["A"]
"""
        root = tmp_project(pyproject=pyproject, files={"app.py": "x = 1\n"})

        class RuleA(Rule):
            code = "A001"
            message = "a"

            def check(self, file_path: str, content: str) -> list:
                return [Violation(file_path, 1, 0, self.code, self.message)]

        class RuleB(Rule):
            code = "B001"
            message = "b"

            def check(self, file_path: str, content: str) -> list:
                return [Violation(file_path, 1, 0, self.code, self.message)]

        violations = check_files([str(root)], [RuleA(), RuleB()], str(root))
        codes = [v.code for v in violations]
        assert "A001" in codes
        assert "B001" not in codes

    def test_ignore_filters_rules(self, tmp_project):
        pyproject = """\
[tool.jg-linter]
ignore = ["A001"]
"""
        root = tmp_project(pyproject=pyproject, files={"app.py": "x = 1\n"})

        class RuleA(Rule):
            code = "A001"
            message = "a"

            def check(self, file_path: str, content: str) -> list:
                return [Violation(file_path, 1, 0, self.code, self.message)]

        violations = check_files([str(root)], [RuleA()], str(root))
        assert violations == []

    def test_per_file_ignores(self, tmp_project):
        root = tmp_project(
            pyproject="""\
[tool.jg-linter]

[tool.jg-linter.per-file-ignores]
"**/tests/**" = ["A001"]
""",
            files={
                "tests/test_app.py": "x = 1\n",
                "src/app.py": "x = 1\n",
            },
        )

        class RuleA(Rule):
            code = "A001"
            message = "a"

            def check(self, file_path: str, content: str) -> list:
                return [Violation(file_path, 1, 0, self.code, self.message)]

        violations = check_files([str(root)], [RuleA()], str(root))
        paths = [v.file_path for v in violations]
        assert any("src/app.py" in p for p in paths)
        assert not any("tests/test_app.py" in p for p in paths)

    def test_no_config_enables_all_rules(self, tmp_project):
        root = tmp_project(files={"app.py": "x = 1\n"})

        class RuleA(Rule):
            code = "A001"
            message = "a"

            def check(self, file_path: str, content: str) -> list:
                return [Violation(file_path, 1, 0, self.code, self.message)]

        violations = check_files([str(root)], [RuleA()], str(root))
        assert len(violations) == 1
