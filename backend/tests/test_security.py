from app.services.otp_service import default_code_generator, hash_secret


def test_auth_hash_is_bound_to_the_server_pepper() -> None:
    first = hash_secret("123456", "pepper-a")
    second = hash_secret("123456", "pepper-b")
    assert first != second
    assert len(first) == 64


def test_development_code_generator_preserves_six_digits() -> None:
    code = default_code_generator()
    assert len(code) == 6
    assert code.isdigit()
