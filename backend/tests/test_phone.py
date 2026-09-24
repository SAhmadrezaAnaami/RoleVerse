import pytest

from app.core.phone import mask_phone, normalize_phone


def test_phone_normalization_accepts_equivalent_formats() -> None:
    assert normalize_phone("+1 (555) 123-4567") == "+15551234567"
    assert normalize_phone("001-555-123-4567") == "+15551234567"


def test_phone_normalization_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        normalize_phone("123")
    with pytest.raises(ValueError):
        normalize_phone("+1-555-ABC-4567")


def test_phone_masking_keeps_only_the_country_and_last_digits() -> None:
    assert mask_phone("+15551234567") == "+1******4567"
