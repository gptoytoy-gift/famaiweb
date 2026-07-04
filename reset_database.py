from pathlib import Path
from server import DB_PATH, init_db


if DB_PATH.exists():
    DB_PATH.unlink()

init_db()
print(f"Reset database: {DB_PATH}")
