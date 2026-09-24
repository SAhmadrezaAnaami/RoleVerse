import re


def normalize_phone(value: str) -> str:
    compact = re.sub(r"[\s().-]", "", value.strip())
    if compact.startswith("00"):
        compact = f"+{compact[2:]}"
    if compact.startswith("+"):
        digits = compact[1:]
    else:
        digits = compact
    if not digits.isdigit() or not 7 <= len(digits) <= 15:
        raise ValueError("Phone number must contain 7 to 15 digits.")
    return f"+{digits}"


def mask_phone(value: str) -> str:
    if len(value) <= 7:
        return "*" * len(value)
    return f"{value[:2]}{'*' * (len(value) - 6)}{value[-4:]}"
