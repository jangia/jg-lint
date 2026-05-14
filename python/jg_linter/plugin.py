from __future__ import annotations

from jg_linter._internal import Violation


class Rule:
    code: str = ""
    message: str = ""
    test_only: bool = False

    def check(self, file_path: str, content: str) -> list[Violation]:
        raise NotImplementedError
