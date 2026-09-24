from pathlib import Path

from alembic.command import downgrade, upgrade
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

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
        "generation_runs",
        "provider_connections",
        "provider_models",
        "system_settings",
        "audit_events",
    }.issubset(table_names)
    inspector = inspect(engine)
    assert "source" in {column["name"] for column in inspector.get_columns("messages")}
    generation_columns = {
        column["name"] for column in inspector.get_columns("generation_runs")
    }
    assert {
        "user_message_id",
        "assistant_message_id",
        "usage_available",
        "input_tokens",
        "output_tokens",
        "total_cost_micro",
    }.issubset(generation_columns)
    provider_columns = {
        column["name"] for column in inspector.get_columns("provider_connections")
    }
    assert {"adapter", "base_url", "secret_source", "is_default"}.issubset(provider_columns)
    model_columns = {
        column["name"] for column in inspector.get_columns("provider_models")
    }
    assert {"pricing_available", "max_output_tokens"}.issubset(model_columns)
    engine.dispose()

    downgrade(config, "base")
    engine = create_engine(database_url)
    assert "users" not in inspect(engine).get_table_names()
    engine.dispose()

    upgrade(config, "head")
    engine = create_engine(database_url)
    assert "users" in inspect(engine).get_table_names()
    engine.dispose()


def test_generation_migration_backfills_existing_message_sources(tmp_path) -> None:
    database_path = tmp_path / "populated.sqlite3"
    database_url = f"sqlite:///{database_path.as_posix()}"
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    upgrade(config, "0002_characters_chats")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (id, phone, display_name, role, status, preferred_language, created_at, updated_at) "
                "VALUES (:id, :phone, '', 'user', 'active', 'en', :now, :now)"
            ),
            {"id": "user-1", "phone": "+15550000001", "now": "2026-01-01 00:00:00"},
        )
        connection.execute(
            text(
                "INSERT INTO characters (id, slug, name, tagline, description, persona, soul, backstory, greeting, sample_reply, tags, translations, category, default_language, status, is_featured, created_at, updated_at) "
                "VALUES (:id, :slug, 'Luna', '', '', '', '', '', 'Hello', 'Reply', '[]', '{}', 'General', 'en', 'published', 0, :now, :now)"
            ),
            {"id": "character-1", "slug": "luna-test", "now": "2026-01-01 00:00:00"},
        )
        connection.execute(
            text(
                "INSERT INTO conversations (id, user_id, character_id, title, locale, status, last_message_at, created_at, updated_at) "
                "VALUES ('conversation-1', 'user-1', 'character-1', 'Chat', 'en', 'active', :now, :now, :now)"
            ),
            {"now": "2026-01-01 00:00:00"},
        )
        connection.execute(
            text(
                "INSERT INTO messages (id, conversation_id, role, content, status, position, created_at, updated_at) "
                "VALUES ('message-1', 'conversation-1', 'assistant', 'Hello', 'complete', 1, :now, :now)"
            ),
            {"now": "2026-01-01 00:00:00"},
        )
        connection.execute(
            text(
                "INSERT INTO messages (id, conversation_id, role, content, status, position, created_at, updated_at) "
                "VALUES ('message-2', 'conversation-1', 'assistant', 'Preview', 'complete', 2, :now, :now)"
            ),
            {"now": "2026-01-01 00:00:00"},
        )
    engine.dispose()
    upgrade(config, "head")
    engine = create_engine(database_url)
    with engine.connect() as connection:
        sources = dict(
            connection.execute(
                text("SELECT id, source FROM messages ORDER BY position")
            ).all()
        )
    assert sources == {"message-1": "greeting", "message-2": "preview"}
    engine.dispose()
