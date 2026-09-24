from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models import AuthSession, OtpChallenge


class AuthRepository:
    def latest_otp(self, session: Session, phone: str) -> OtpChallenge | None:
        statement = (
            select(OtpChallenge)
            .where(OtpChallenge.phone == phone)
            .order_by(OtpChallenge.created_at.desc())
            .limit(1)
        )
        return session.scalar(statement)

    def active_otp(
        self,
        session: Session,
        phone: str,
        now: datetime,
    ) -> OtpChallenge | None:
        statement = (
            select(OtpChallenge)
            .where(
                OtpChallenge.phone == phone,
                OtpChallenge.consumed_at.is_(None),
                OtpChallenge.expires_at > now,
            )
            .order_by(OtpChallenge.created_at.desc())
            .limit(1)
        )
        return session.scalar(statement)

    def create_otp(
        self,
        session: Session,
        phone: str,
        code_hash: str,
        expires_at: datetime,
        request_ip_hash: str | None,
    ) -> OtpChallenge:
        challenge = OtpChallenge(
            phone=phone,
            code_hash=code_hash,
            expires_at=expires_at,
            request_ip_hash=request_ip_hash,
        )
        session.add(challenge)
        session.flush()
        return challenge

    def increment_attempts(self, challenge: OtpChallenge) -> None:
        challenge.attempts += 1

    def consume_otp(self, challenge: OtpChallenge, consumed_at: datetime) -> None:
        challenge.consumed_at = consumed_at

    def consume_otp_if_active(
        self,
        session: Session,
        challenge_id: str,
        consumed_at: datetime,
    ) -> bool:
        statement = (
            update(OtpChallenge)
            .where(
                OtpChallenge.id == challenge_id,
                OtpChallenge.consumed_at.is_(None),
            )
            .values(consumed_at=consumed_at)
        )
        return session.execute(statement).rowcount == 1

    def create_session(
        self,
        session: Session,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
        last_seen_at: datetime,
        user_agent: str | None,
    ) -> AuthSession:
        auth_session = AuthSession(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            last_seen_at=last_seen_at,
            user_agent=user_agent,
        )
        session.add(auth_session)
        session.flush()
        return auth_session

    def active_session(
        self,
        session: Session,
        token_hash: str,
        now: datetime,
    ) -> AuthSession | None:
        statement = select(AuthSession).where(
            AuthSession.token_hash == token_hash,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
        return session.scalar(statement)

    def revoke_session(self, auth_session: AuthSession, revoked_at: datetime) -> None:
        auth_session.revoked_at = revoked_at

    def revoke_user_sessions(
        self,
        session: Session,
        user_id: str,
        revoked_at: datetime,
    ) -> None:
        statement = select(AuthSession).where(
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
        )
        for auth_session in session.scalars(statement):
            auth_session.revoked_at = revoked_at

    def touch_session(self, auth_session: AuthSession, last_seen_at: datetime) -> None:
        auth_session.last_seen_at = last_seen_at
