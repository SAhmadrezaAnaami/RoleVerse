from app.services.rate_limit import InMemoryRateLimiter


def test_rate_limiter_returns_remaining_capacity_then_blocks() -> None:
    limiter = InMemoryRateLimiter()
    first = limiter.check("user-1", 2, 60)
    second = limiter.check("user-1", 2, 60)
    blocked = limiter.check("user-1", 2, 60)

    assert first.allowed is True
    assert first.remaining == 1
    assert second.allowed is True
    assert second.remaining == 0
    assert blocked.allowed is False
    assert blocked.remaining == 0
    assert blocked.retry_after_seconds >= 1


def test_rate_limit_keys_are_isolated() -> None:
    limiter = InMemoryRateLimiter()
    limiter.check("user-1", 1, 60)
    other_user = limiter.check("user-2", 1, 60)

    assert other_user.allowed is True
    assert other_user.remaining == 0
