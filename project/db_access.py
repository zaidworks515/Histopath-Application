import sqlite3
from flask_bcrypt import Bcrypt, check_password_hash
from flask import Flask

app = Flask(__name__)
bcrypt = Bcrypt(app)

def init_db():
    conn = sqlite3.connect('database/db.sqlite')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        password TEXT NOT NULL
    )
    ''')
    conn.commit()
    conn.close()

init_db()


def register_user(username, password):
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    conn = sqlite3.connect('database/db.sqlite')
    cursor = conn.cursor()
    
    # Check if username already exists
    cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
    existing_user = cursor.fetchone()
    if existing_user:
        conn.close()
        return False  # Username already exists
    
    # Insert new user
    try:
        cursor.execute('''
        INSERT INTO users (username, password)
        VALUES (?, ?)
        ''', (username, hashed_password))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return False  # Integrity error, though this should not happen due to previous check
    conn.close()
    return True

# Example usage
# register_user('testuser', 'testuser@gmail.com', 'password123')

def verify_user(username, password):
    conn = sqlite3.connect('database/db.sqlite')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT username, password FROM users WHERE username = ?
    ''', (username,))
    user = cursor.fetchone()
    conn.close()
    if user and check_password_hash(user[1], password):
        return {'username': user[0]}  # Return user dictionary with username
    return None

# Example usage
# username = verify_user('testuser@gmail.com', 'password123')
# if username:
#     print(f'Logged in as {username}')
# else:
#     print('Login failed')
