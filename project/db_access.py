import sqlite3
from flask import Flask
from flask_bcrypt import Bcrypt, check_password_hash

# Initialize Flask and Bcrypt
app = Flask(__name__)
bcrypt = Bcrypt(app)

# Function to initialize database with tables
def init_db():
    conn = sqlite3.connect('database/db.sqlite')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT NOT NULL
    )
    ''')
    
    # Create pdf_files table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pdf_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        filename TEXT NOT NULL,
        pdf BLOB NOT NULL,
        FOREIGN KEY (username) REFERENCES users (username)
    )
    ''')
    
    conn.commit()
    conn.close()

# Call init_db() to create tables if they don't exist
init_db()


def insert_pdf(db_path, username, filename, pdf_data):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if the filename already exists for the user
    cursor.execute("SELECT COUNT(*) FROM pdf_files WHERE username = ? AND filename = ?", (username, filename))
    count = cursor.fetchone()[0]

    if count > 0:
        # If filename exists, update it with a counter
        base, extension = filename.rsplit('.', 1)
        counter = 1
        new_filename = f"{base}_{counter}.{extension}"
        while True:
            cursor.execute("SELECT COUNT(*) FROM pdf_files WHERE username = ? AND filename = ?", (username, new_filename))
            count = cursor.fetchone()[0]
            if count == 0:
                break
            counter += 1
            new_filename = f"{base}_{counter}.{extension}"
        filename = new_filename

    # Insert the PDF into the database
    cursor.execute("INSERT INTO pdf_files (username, filename, pdf) VALUES (?, ?, ?)", (username, filename, pdf_data))
    conn.commit()
    conn.close()



def retrieve_pdf(db_path, username, pdf_id=None, search_term=None):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    if pdf_id:
        cursor.execute("SELECT id, filename FROM pdf_files WHERE id = ? AND username = ?", (pdf_id, username))
    elif search_term:
        cursor.execute("SELECT id, filename FROM pdf_files WHERE username = ? AND filename LIKE ? ORDER BY id DESC", (username, f"%{search_term}%"))
    else:
        cursor.execute("SELECT id, filename FROM pdf_files WHERE username = ? ORDER BY id DESC", (username,))

    rows = cursor.fetchall()
    conn.close()
    return rows




def delete_pdf(db_path, username, pdf_ids):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    affected_rows = 0
    
    try:
        for pdf_id in pdf_ids:
            cursor.execute("DELETE FROM pdf_files WHERE id = ? AND username = ?", (pdf_id, username))
            affected_rows += cursor.rowcount
    except sqlite3.Error as e:
        print(f"SQLite error while deleting: {str(e)}")
        conn.rollback()
    finally:
        conn.commit()
        conn.close()
    
    return affected_rows


def register_user(username, password):
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    conn = sqlite3.connect('database/db.sqlite')
    cursor = conn.cursor()
    
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


def verify_user(username, password):
    conn = sqlite3.connect('database/db.sqlite')
    cursor = conn.cursor()
    cursor.execute('SELECT username, password FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    
    if user and check_password_hash(user[1], password):
        return {'username': user[0]}  # Return user dictionary with username
    return None

