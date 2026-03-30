"""
Script to add qualtrics_id column to existing users table
Run this if you have an existing database and need to add the qualtrics_id column
"""
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./memory_research.db")

# Extract database file path from SQLite URL
if DATABASE_URL.startswith("sqlite:///"):
    db_path = DATABASE_URL.replace("sqlite:///", "")
    if db_path.startswith("./"):
        db_path = os.path.join(os.path.dirname(__file__), db_path[2:])
    
    print(f"Connecting to database: {db_path}")
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        print("Run 'python init_db.py' first to create the database.")
        exit(1)
    
    # Connect to SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'qualtrics_id' in columns:
            print("Column 'qualtrics_id' already exists in users table.")
        else:
            print("Adding 'qualtrics_id' column to users table...")
            # Add the column
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN qualtrics_id VARCHAR(255) NULL
            """)
            
            # Create index for better query performance
            print("Creating index on qualtrics_id...")
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_users_qualtrics_id 
                ON users(qualtrics_id) 
                WHERE qualtrics_id IS NOT NULL
            """)
            
            conn.commit()
            print("✅ Successfully added 'qualtrics_id' column to users table!")
            print("✅ Created unique index on qualtrics_id")
    except sqlite3.Error as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()
else:
    print("This script only works with SQLite databases.")
    print(f"Your DATABASE_URL is: {DATABASE_URL}")
    print("For PostgreSQL, you'll need to run a migration manually.")
