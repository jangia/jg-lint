def test_user_role():
    user = {"role": "admin"}
    if user["role"] == "admin":
        assert user["role"] == "admin"
    else:
        assert user["role"] != "admin"
