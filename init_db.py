import sqlite3
import os

# Get the database path
db_path = 'database.db'

# Check if database exists
if os.path.exists(db_path):
    print(f"⚠️  Database already exists at: {db_path}")
    response = input("Do you want to DELETE and recreate it? (yes/no): ")
    if response.lower() != 'yes':
        print("Aborted. Database unchanged.")
        exit()
    os.remove(db_path)


# Create new database
conn = sqlite3.connect(db_path)
c = conn.cursor()


# Users table
c.execute("""
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    face_embedding BLOB
)
""")

# Stored Passwords table
c.execute("""
CREATE TABLE passwords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    service TEXT NOT NULL,
    secret TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")


# Commit and close
conn.commit()

# Verify tables were created
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()

conn.close()
