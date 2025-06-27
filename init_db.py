import sqlite3

conn = sqlite3.connect('database.db')
c = conn.cursor()

# Drop old tables if any
c.execute("DROP TABLE IF EXISTS users")
c.execute("DROP TABLE IF EXISTS files")
c.execute("DROP TABLE IF EXISTS passwords")

# Users table
c.execute("""
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE,
    name TEXT,
    face_embedding BLOB
)
""")

# Uploaded Files table
c.execute("""
CREATE TABLE files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT,
    filename TEXT,
    filepath TEXT
)
""")

# Stored Passwords table
c.execute("""
CREATE TABLE passwords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT,
    service TEXT,
    secret TEXT
)
""")

conn.commit()
conn.close()

print("Database initialized.")
