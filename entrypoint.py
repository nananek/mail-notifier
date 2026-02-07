"""
Entrypoint script – runs Alembic migrations then starts the given command.
Used in docker-compose to ensure DB schema is up-to-date before starting
the web or worker process.
"""

import os
import subprocess
import sys
import time


def wait_for_db():
    """Wait for PostgreSQL to become reachable (TCP or Unix socket)."""
    import psycopg2

    db_url = os.environ.get("DATABASE_URL", "")

    for attempt in range(30):
        try:
            conn = psycopg2.connect(db_url)
            conn.close()
            return
        except Exception:
            print(f"Waiting for DB... attempt {attempt + 1}/30")
            time.sleep(2)

    print("Could not connect to database after 60 seconds", file=sys.stderr)
    sys.exit(1)


def run_migrations():
    """Run alembic upgrade head."""
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("Migration failed:", result.stderr, file=sys.stderr)
        sys.exit(1)
    print("Migrations applied successfully.")
    if result.stdout:
        print(result.stdout)


if __name__ == "__main__":
    wait_for_db()
    run_migrations()

    # Exec the remaining arguments (e.g. gunicorn or python worker.py)
    if len(sys.argv) > 1:
        os.execvp(sys.argv[1], sys.argv[1:])
