from jg_linter._internal import Violation


class TestViolationConstruction:
    def test_fields(self):
        v = Violation("src/app.py", 42, 5, "JG999", "bad thing")
        assert v.file_path == "src/app.py"
        assert v.line == 42
        assert v.col == 5
        assert v.code == "JG999"
        assert v.message == "bad thing"


class TestViolationDisplay:
    def test_str(self):
        v = Violation("foo.py", 10, 3, "JG001", "oops")
        assert str(v) == "foo.py:10:3: JG001 oops"

    def test_repr(self):
        v = Violation("foo.py", 10, 3, "JG001", "oops")
        assert "Violation" in repr(v)
        assert "JG001" in repr(v)
