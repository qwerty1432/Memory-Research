"""
Database initialization script
Run this to set up the database schema and optionally seed test data
"""
from app.database import init_db, SessionLocal
from app.models import User, Session, Message, Memory, Event
from app import auth
import uuid

def seed_test_data():
    """Seed database with test users and data"""
    db = SessionLocal()
    try:
        # Create test users for each condition
        conditions = ["SESSION_AUTO", "SESSION_USER", "PERSISTENT_AUTO", "PERSISTENT_USER"]
        
        for i, condition in enumerate(conditions):
            username = f"test_{condition.lower()}"
            # Check if user already exists
            existing = db.query(User).filter(User.username == username).first()
            if not existing:
                user = User(
                    user_id=uuid.uuid4(),
                    username=username,
                    password_hash=auth.get_password_hash("testpass123"),
                    condition_id=condition
                )
                db.add(user)
                print(f"Created test user: {username} (condition: {condition})")
        
        db.commit()
        print("Database seeded successfully!")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Database initialized!")
    
    # Uncomment to seed test data
    # seed_test_data()

