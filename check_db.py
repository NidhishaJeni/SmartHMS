import sqlite3

# Check the current database
conn = sqlite3.connect('c:/Users/gkavi/OneDrive/Desktop/HMS_new/smart_hms.db')
cursor = conn.cursor()

# Check if users table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
if cursor.fetchone():
    print("Users table exists")
    cursor.execute("SELECT username, role, is_active FROM users")
    users = cursor.fetchall()
    print(f"Users in database: {users}")
else:
    print("Users table does not exist")
    
conn.close()

