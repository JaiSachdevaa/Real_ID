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
    print("✓ Old database deleted.")

# Create new database
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("\n🔨 Creating database tables...")

# Users table
c.execute("""
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    face_embedding BLOB
)
""")
print("✓ Created 'users' table")

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
print("✓ Created 'passwords' table")

# Commit and close
conn.commit()

# Verify tables were created
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
print("\n📋 Database tables created:")
for table in tables:
    print(f"   - {table[0]}")

conn.close()

print(f"\n✅ Database initialized successfully at: {os.path.abspath(db_path)}")
print("You can now run: python app.py")