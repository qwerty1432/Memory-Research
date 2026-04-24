"""
One-time migration helper for condition cleanup.

Maps legacy SESSION_USER rows to PERSISTENT_USER so old participants remain valid
after the condition set is reduced to three arms.
"""
from app.database import SessionLocal
from app.models import User


def migrate_legacy_conditions() -> None:
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.condition_id == "SESSION_USER").all()
        for user in users:
            user.condition_id = "PERSISTENT_USER"
        db.commit()
        print(f"Updated {len(users)} users from SESSION_USER to PERSISTENT_USER.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate_legacy_conditions()
