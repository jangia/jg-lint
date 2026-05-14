try:
    from jg_linter._internal import Violation
except ImportError:
    raise ImportError(
        "jg-linter's Rust extension is not built. Run 'maturin develop' to build it."
    ) from None

from jg_linter.plugin import Rule

__all__ = ["Rule", "Violation"]
