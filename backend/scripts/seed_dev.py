from app.db.seed import seed_characters
from app.db.session import SessionLocal


def main() -> None:
    with SessionLocal() as session:
        created = seed_characters(session)
    print(f"RoleVerse development characters ready. Created: {created}")


if __name__ == "__main__":
    main()
