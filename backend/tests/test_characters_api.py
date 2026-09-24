from app.db.models import Character
from app.db.seed import seed_characters


def test_public_character_catalog_is_available_without_authentication(api_client) -> None:
    response = api_client.get("/api/v1/characters")
    assert response.status_code == 200
    items = response.json()
    assert {item["slug"] for item in items} == {"luna-vale", "rowan-vale", "mira-sol"}
    assert "sample_reply" not in items[0]
    assert "persona" not in items[0]


def test_character_catalog_can_return_persian_display_fields(api_client) -> None:
    response = api_client.get("/api/v1/characters?locale=fa")
    assert response.status_code == 200
    luna = next(item for item in response.json() if item["slug"] == "luna-vale")
    assert luna["locale"] == "fa"
    assert luna["name"] == "لونا ویل"
    assert luna["tagline"] == "ستاره‌شناس"


def test_character_detail_does_not_expose_internal_context(api_client) -> None:
    response = api_client.get("/api/v1/characters/luna-vale")
    assert response.status_code == 200
    body = response.json()
    assert body["greeting"]
    assert "sample_reply" not in body
    assert "soul" not in body
    assert "backstory" not in body


def test_character_seed_is_idempotent(migrated_db) -> None:
    session_factory, _ = migrated_db
    with session_factory() as session:
        assert seed_characters(session) == 0
        assert len(session.query(Character).all()) == 3


def test_hidden_characters_are_not_public(api_client, migrated_db) -> None:
    session_factory, _ = migrated_db
    with session_factory() as session:
        session.add(
            Character(
                slug="hidden-character",
                name="Hidden Character",
                description="Hidden",
                status="draft",
                tags=[],
                translations={},
            )
        )
        session.commit()

    assert api_client.get("/api/v1/characters/hidden-character").status_code == 404
    assert all(
        item["slug"] != "hidden-character"
        for item in api_client.get("/api/v1/characters").json()
    )
