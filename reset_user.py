import sqlite3

conn = sqlite3.connect('database.db')
c = conn.cursor()
c.execute("DELETE FROM users")
conn.commit()
conn.close()
print("✅ User table cleared.")
