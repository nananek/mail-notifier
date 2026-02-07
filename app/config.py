import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql://mailnotifier:password@localhost:5432/mailnotifier"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "60"))
