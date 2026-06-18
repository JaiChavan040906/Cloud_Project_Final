from unittest.mock import patch

from jose import jwt

from app.auth import JWT_ALGORITHM, JWT_SECRET, create_access_token, hash_password, verify_password


class TestHashPassword:
    def test_hash_password_returns_string(self):
        hashed = hash_password("test_password")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_is_different_from_plain(self):
        hashed = hash_password("test_password")
        assert hashed != "test_password"

    def test_verify_password_correct(self):
        hashed = hash_password("test_password")
        assert verify_password("test_password", hashed) is True

    def test_verify_password_incorrect(self):
        hashed = hash_password("test_password")
        assert verify_password("wrong_password", hashed) is False

    def test_verify_password_round_trip_multiple(self):
        passwords = ["admin123", "doctor123", "nurse123", "reception123"]
        for pwd in passwords:
            hashed = hash_password(pwd)
            assert verify_password(pwd, hashed) is True
            assert verify_password(pwd + "x", hashed) is False

    def test_hash_is_different_each_time(self):
        pwd = "same_password"
        hash1 = hash_password(pwd)
        hash2 = hash_password(pwd)
        assert hash1 != hash2


class TestCreateAccessToken:
    def test_token_contains_expected_claims(self):
        data = {"sub": "testuser", "role": "admin"}
        token = create_access_token(data)
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert payload["sub"] == "testuser"
        assert payload["role"] == "admin"

    def test_token_has_expiry(self):
        token = create_access_token({"sub": "user"})
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert "exp" in payload

    @patch("app.auth.jwt.encode")
    def test_token_calls_jwt_encode(self, mock_encode):
        mock_encode.return_value = "mocked_token"
        data = {"sub": "user", "role": "doctor"}
        token = create_access_token(data)
        assert token == "mocked_token"
        mock_encode.assert_called_once()
        args, kwargs = mock_encode.call_args
        assert args[0]["sub"] == "user"
        assert args[0]["role"] == "doctor"
        assert "exp" in args[0]
        assert kwargs["algorithm"] == JWT_ALGORITHM
