from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from alembic.command import upgrade
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_otp_service
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.main import create_app
from app.services import OtpService

BACKEND_ROOT = Path(__file__).resolve().parents[1]


class ManualClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self.value

    def advance(self, **kwargs) -> None:
        self.value += timedelta(**kwargs)


class RecordingOtpSender:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send(self, phone: str, code: str) -> None:
        self.sent.append((phone, code))


class SequenceCodeGenerator:
    def __init__(self) -> None:
        self.count = 0

    def __call__(self) -> str:
        self.count += 1
        return f"{self.count:06d}"


@pytest.fixture
def code_generator() -> SequenceCodeGenerator:
    return SequenceCodeGenerator()


@pytest.fixture
def manual_clock() -> ManualClock:
    return ManualClock()


@pytest.fixture
def otp_sender() -> RecordingOtpSender:
    return RecordingOtpSender()


@pytest.fixture
def migrated_db(tmp_path):
    database_path = tmp_path / "roleverse.sqlite3"
    database_url = f"sqlite:///{database_path.as_posix()}"
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    upgrade(config, "head")
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    yield session_factory, database_url
    engine.dispose()


@pytest.fixture
def test_settings(migrated_db) -> Settings:
    _, database_url = migrated_db
    return Settings(
        environment="test",
        database_url=database_url,
        auth_pepper="test-auth-pepper",
        god_user_phone="+15550000000",
        otp_ttl_minutes=5,
        otp_max_attempts=3,
        otp_resend_cooldown_seconds=0,
        session_ttl_minutes=60,
        cookie_secure=False,
    )


@pytest.fixture
def application(migrated_db, test_settings, manual_clock, otp_sender, code_generator):
    session_factory, _ = migrated_db
    application = create_app(test_settings)

    def override_get_db():
        with session_factory() as session:
            yield session

    def override_get_otp_service():
        with session_factory() as session:
            yield OtpService(
                session,
                test_settings,
                clock=manual_clock.now,
                code_generator=code_generator,
                sender=otp_sender.send,
            )

    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_settings] = lambda: test_settings
    application.dependency_overrides[get_otp_service] = override_get_otp_service
    return application


@pytest.fixture
def api_client(application):
    with TestClient(application, base_url="https://testserver") as client:
        yield client
