def test_user_role():
    user = {"role": "admin"}
    if user["role"] == "admin":
        assert True
    else:
        assert False
