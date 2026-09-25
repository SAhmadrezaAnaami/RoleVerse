import hashlib
import hmac
import secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.phone import mask_phone, normalize_phone
from app.db.base import utc_now
from app.db.models import User
from app.repositories import AuthRepository, UserRepository


Clock = Callable[[], datetime]
CodeGenerator = Callable[[], str]
OtpSender = Callable[[str, str], None]


class OtpServiceError(Exception):
    pass


class OtpCooldownError(OtpServiceError):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("A verification code was requested recently.")


class InvalidOtpError(OtpServiceError):
    pass


class AccountBlockedError(OtpServiceError):
    pass


@dataclass
class IssuedSession:
    user: User
    token: str = field(repr=False)
    csrf_token: str = field(repr=False)
    expires_at: datetime


def hash_secret(value: str, pepper: str) -> str:
    return hmac.new(
        pepper.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def default_otp_sender(phone: str, code: str) -> None:
    print(f"RoleVerse development OTP for {mask_phone(phone)}: {code}", flush=True)


def default_code_generator() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


class OtpService:
    def __init__(
        self,
        session: Session,
        settings: Settings,
        clock: Clock = utc_now,
        code_generator: CodeGenerator = default_code_generator,
        sender: OtpSender = default_otp_sender,
    ) -> None:
        self.session = session
        self.settings = settings
        if settings.environment.lower() == "production" and sender is default_otp_sender:
            raise RuntimeError("A production OTP delivery adapter is required.")
        self.clock = clock
        self.code_generator = code_generator
        self.sender = sender
        self.auth_repository = AuthRepository()
        self.user_repository = UserRepository()

    def request_otp(self, phone: str, request_ip: str | None) -> tuple[datetime, int]:
        normalized_phone = normalize_phone(phone)
        now = self.clock()
        latest = self.auth_repository.latest_otp(self.session, normalized_phone)
        retry_after = 0
        if latest is not None and latest.consumed_at is None:
            elapsed = int((now - as_utc(latest.created_at)).total_seconds())
            retry_after = max(
                0,
                self.settings.otp_resend_cooldown_seconds - elapsed,
            )
            if retry_after > 0:
                raise OtpCooldownError(retry_after)
            self.auth_repository.consume_otp(latest, now)
        code = self.code_generator()
        expires_at = now + timedelta(minutes=self.settings.otp_ttl_minutes)
        request_ip_hash = (
            hash_secret(request_ip, self.settings.auth_pepper)
            if request_ip
            else None
        )
        challenge = self.auth_repository.create_otp(
            self.session,
            normalized_phone,
            hash_secret(f"{normalized_phone}:{code}", self.settings.auth_pepper),
            expires_at,
            request_ip_hash,
        )
        challenge.created_at = now
        challenge.updated_at = now
        self.session.commit()
        self.sender(normalized_phone, code)
        return expires_at, retry_after

    def verify_otp(
        self,
        phone: str,
        code: str,
        user_agent: str | None = None,
    ) -> IssuedSession:
        normalized_phone = normalize_phone(phone)
        now = self.clock()
        challenge = self.auth_repository.active_otp(
            self.session,
            normalized_phone,
            now,
        )
        if challenge is None:
            raise InvalidOtpError("Invalid or expired verification code.")
        if challenge.attempts >= self.settings.otp_max_attempts:
            self.auth_repository.consume_otp(challenge, now)
            self.session.commit()
            raise InvalidOtpError("Invalid or expired verification code.")
        if not secrets.compare_digest(challenge.code_hash, hash_secret(f"{normalized_phone}:{code}", self.settings.auth_pepper)):
            self.auth_repository.increment_attempts(challenge)
            if challenge.attempts >= self.settings.otp_max_attempts:
                self.auth_repository.consume_otp(challenge, now)
            self.session.commit()
            raise InvalidOtpError("Invalid or expired verification code.")
        if not self.auth_repository.consume_otp_if_active(
            self.session,
            challenge.id,
            now,
        ):
            self.session.rollback()
            raise InvalidOtpError("Invalid or expired verification code.")
        user = self.user_repository.get_by_phone(self.session, normalized_phone)
        if user is None:
            user = self.user_repository.create(
                self.session,
                normalized_phone,
                role="admin" if self._is_god_phone(normalized_phone) else "user",
            )
            user.created_at = now
            user.updated_at = now
        elif self._is_god_phone(normalized_phone) and user.role != "admin":
            self.user_repository.set_role(self.session, user, "admin")
        if user.status != "active":
            self.session.commit()
            raise AccountBlockedError("This account is not available.")
        self.user_repository.touch_login(self.session, user, now)
        token = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        expires_at = now + timedelta(minutes=self.settings.session_ttl_minutes)
        auth_session = self.auth_repository.create_session(
            self.session,
            user.id,
            hash_secret(token, self.settings.auth_pepper),
            hash_secret(csrf_token, self.settings.auth_pepper),
            user.auth_epoch,
            expires_at,
            now,
            user_agent[:255] if user_agent else None,
        )
        auth_session.created_at = now
        auth_session.updated_at = now
        self.session.commit()
        return IssuedSession(
            user=user,
            token=token,
            csrf_token=csrf_token,
            expires_at=expires_at,
        )

    def user_from_token(self, token: str) -> User | None:
        if not token:
            return None
        now = self.clock()
        auth_session = self.auth_repository.active_session(
            self.session,
            hash_secret(token, self.settings.auth_pepper),
            now,
        )
        if auth_session is None:
            return None
        user = self.user_repository.get_by_id(self.session, auth_session.user_id)
        if user is None or user.status != "active":
            self.auth_repository.revoke_session(auth_session, now)
            self.session.commit()
            return None
        self.auth_repository.touch_session(auth_session, now)
        self.session.commit()
        return user

    def csrf_is_valid(self, session_token: str, csrf_token: str) -> bool:
        if not session_token or not csrf_token:
            return False
        auth_session = self.auth_repository.active_session(
            self.session,
            hash_secret(session_token, self.settings.auth_pepper),
            self.clock(),
        )
        if auth_session is None or auth_session.csrf_token_hash is None:
            return False
        return secrets.compare_digest(
            auth_session.csrf_token_hash,
            hash_secret(csrf_token, self.settings.auth_pepper),
        )

    def logout(self, token: str) -> None:
        if not token:
            return
        now = self.clock()
        auth_session = self.auth_repository.active_session(
            self.session,
            hash_secret(token, self.settings.auth_pepper),
            now,
        )
        if auth_session is not None:
            self.auth_repository.revoke_session(auth_session, now)
            self.session.commit()

    def logout_all(self, user_id: str) -> None:
        self.auth_repository.invalidate_user_sessions(
            self.session,
            user_id,
            self.clock(),
        )
        self.session.commit()

    def _is_god_phone(self, phone: str) -> bool:
        configured_phone = self.settings.god_user_phone.strip()
        if not configured_phone:
            return False
        try:
            return normalize_phone(configured_phone) == phone
        except ValueError:
            return False
