import pytest


@pytest.mark.parametrize("role,expected", [("admin", True), ("user", False)])
def test_user_role(role, expected):
    assert (role == "admin") is expected
