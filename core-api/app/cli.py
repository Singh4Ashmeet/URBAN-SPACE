from __future__ import annotations

import argparse
from app.db import Base, SessionLocal, engine, DB_PATH


def migrate_database() -> None:
    """Run Alembic migrations to upgrade database to head."""
    from alembic.config import Config
    from alembic import command
    from pathlib import Path
    
    app_dir = Path(__file__).resolve().parent
    core_api_dir = app_dir.parent
    ini_path = core_api_dir / "alembic.ini"
    
    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("script_location", str(core_api_dir / "alembic"))
    alembic_cfg.set_main_option("configure_logging", "false")
    command.upgrade(alembic_cfg, "head")


def seed_database(force: bool = False) -> None:
    """Seed demo data into the database."""
    from app.main import _seed_if_empty
    _seed_if_empty()


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage UrbanShield core API local persistence.")
    parser.add_argument("command", choices=["migrate", "seed", "reset"])
    parser.add_argument("--yes", action="store_true", help="Confirm destructive reset.")
    args = parser.parse_args()

    if args.command == "migrate":
        migrate_database()
        print(f"Applied core-api SQLite migrations at {DB_PATH}")
    elif args.command == "seed":
        seed_database(force=False)
        print(f"Seeded core-api development data at {DB_PATH}")
    elif args.command == "reset":
        if not args.yes:
            raise SystemExit("Refusing to reset without --yes")
        import shutil
        from pathlib import Path
        backup = Path(str(DB_PATH) + ".backup")
        if DB_PATH.exists():
            shutil.copy2(DB_PATH, backup)
            print(f"Backed up database to {backup}")
            DB_PATH.unlink()
        migrate_database()
        seed_database(force=True)
        print(f"Reset and seeded core-api development data at {DB_PATH}")


if __name__ == "__main__":
    main()
