from pathlib import Path

from alembic.command import downgrade, upgrade
from alembic.config import Config
from sqlalchemy import create_engine, inspect

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_initial_migration_round_trip(tmp_path) -> None:
    database_path = tmp_path / "migration.sqlite3"
    database_url = f"sqlite:///{database_path.as_posix()}"
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)

    upgrade(config, "head")
    engine = create_engine(database_url)
    table_names = set(inspect(engine).get_table_names())
    assert {
        "users",
        "otp_challenges",
        "auth_sessions",
        "characters",
        "conversations",
        "messages",
    }.issubset(table_names)
    engine.dispose()

    downgrade(config, "base")
    engine = create_engine(database_url)
    assert "users" not in inspect(engine).get_table_names()
    engine.dispose()

    upgrade(config, "head")
    engine = create_engine(database_url)
    assert "users" in inspect(engine).get_table_names()
    engine.dispose()
