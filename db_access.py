import sqlite3

# Connect to the SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('db.sqlite')

# Create a cursor object to interact with the database
cursor = conn.cursor()

# # Create the doctors table if it does not already exist
# cursor.execute('''
# CREATE TABLE IF NOT EXISTS doctors (
#     id INTEGER PRIMARY KEY,
#     email TEXT NOT NULL
# )
# ''')

# # Create the reports table if it does not already exist
# cursor.execute('''
# CREATE TABLE IF NOT EXISTS reports (
#     id INTEGER PRIMARY KEY,
#     doctor_id INTEGER,
#     report_name TEXT,
#     FOREIGN KEY (doctor_id) REFERENCES doctors(id)
# )
# ''')

# # Insert data into the doctors table
# cursor.execute('''
# INSERT INTO doctors (email) VALUES ('dr_ali5@gmail.com')
# ''')

# cursor.execute('''
# INSERT INTO doctors (email) VALUES ('zaid123@yahoo.com')
# ''')

# # Commit the changes
# conn.commit()


# Query the doctors table to verify the insertion
cursor.execute('SELECT * FROM doctors')
doctors = cursor.fetchall()
print('Doctors:', doctors)

# Close the connection
conn.close()
