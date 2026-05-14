from pathlib import Path

import pytest


@pytest.fixture
def tmp_project(tmp_path: Path):
    """Create a temporary project directory with a pyproject.toml."""

    def _make(
        *,
        pyproject: str = "",
        files: dict[str, str] | None = None,
    ) -> Path:
        if pyproject:
            (tmp_path / "pyproject.toml").write_text(pyproject)
        for name, content in (files or {}).items():
            p = tmp_path / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
        return tmp_path

    return _make
