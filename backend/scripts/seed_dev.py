from app.db.seed import seed_admin_defaults, seed_characters
from app.db.session import SessionLocal


def main() -> None:
    with SessionLocal() as session:
        characters = seed_characters(session)
        admin = seed_admin_defaults(session)
    print(f"RoleVerse development data ready. Characters created: {characters}; admin defaults created: {admin}")


if __name__ == "__main__":
    main()
