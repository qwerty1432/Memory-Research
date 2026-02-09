"""
Quick utility to list users and their sessions from the database
"""
from app.database import SessionLocal
from app.models import User, Session, Message
from sqlalchemy import desc

def list_users():
    """List all users with their IDs and conditions"""
    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.created_at.desc()).all()
        
        print("=" * 80)
        print("USERS")
        print("=" * 80)
        
        if not users:
            print("No users found.")
            return
        
        for user in users:
            print(f"\nUsername: {user.username}")
            print(f"  User ID: {user.user_id}")
            print(f"  Condition: {user.condition_id}")
            print(f"  Created: {user.created_at}")
            
            # Get sessions for this user
            sessions = db.query(Session).filter(
                Session.user_id == user.user_id
            ).order_by(desc(Session.started_at)).all()
            
            print(f"  Sessions: {len(sessions)}")
            for i, session in enumerate(sessions[:3], 1):  # Show last 3 sessions
                msg_count = db.query(Message).filter(
                    Message.session_id == session.session_id
                ).count()
                status = "Active" if session.ended_at is None else "Ended"
                print(f"    {i}. Session ID: {session.session_id}")
                print(f"       Status: {status}, Messages: {msg_count}")
                print(f"       Started: {session.started_at}")
        
        print("\n" + "=" * 80)
        
    finally:
        db.close()

def get_user_details(user_id: str = None, username: str = None):
    """Get detailed info about a specific user"""
    db = SessionLocal()
    try:
        if user_id:
            user = db.query(User).filter(User.user_id == user_id).first()
        elif username:
            user = db.query(User).filter(User.username == username).first()
        else:
            print("Please provide either user_id or username")
            return
        
        if not user:
            print("User not found.")
            return
        
        print("=" * 80)
        print(f"USER DETAILS: {user.username}")
        print("=" * 80)
        print(f"User ID: {user.user_id}")
        print(f"Condition: {user.condition_id}")
        print(f"Created: {user.created_at}")
        
        # Get all sessions
        sessions = db.query(Session).filter(
            Session.user_id == user.user_id
        ).order_by(desc(Session.started_at)).all()
        
        print(f"\nTotal Sessions: {len(sessions)}")
        print("-" * 80)
        
        for i, session in enumerate(sessions, 1):
            messages = db.query(Message).filter(
                Message.session_id == session.session_id
            ).order_by(Message.created_at).all()
            
            status = "🟢 Active" if session.ended_at is None else "🔴 Ended"
            print(f"\nSession {i}: {session.session_id}")
            print(f"  Status: {status}")
            print(f"  Started: {session.started_at}")
            if session.ended_at:
                print(f"  Ended: {session.ended_at}")
            print(f"  Messages: {len(messages)}")
            
            if messages:
                print(f"  Last message: {messages[-1].content[:50]}...")
        
        print("=" * 80)
        
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Get specific user details
        arg = sys.argv[1]
        if len(arg) == 36 and '-' in arg:  # Looks like a UUID
            get_user_details(user_id=arg)
        else:
            get_user_details(username=arg)
    else:
        # List all users
        list_users()
        
    print("\nUsage:")
    print("  python list_users.py                    # List all users")
    print("  python list_users.py <username>         # Get user by username")
    print("  python list_users.py <user_id>          # Get user by ID")


