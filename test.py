import sqlite3

keys_to_extract = {
    "First Name": "TEXT",
    "Last Name": "TEXT",
    "M.I": "TEXT",
    "Date": "DATE",
    "Street Address": "TEXT",
    "Apartment/Unit#": "TEXT",
    "City": "TEXT",
    "State": "TEXT",
    "Zip Code": "INTEGER",
    "Phone": "TEXT",
    "E-mail Address": "TEXT",
    "Job(s) You're Applying For": "TEXT",
    "Years of Experience": "INTEGER",
    "Desired Salary/Rate": "REAL",
    "Earliest Date Available": "DATE",
    "Relevant Skills": "TEXT"
}

def sanitize_column_name(name):
    # Replace spaces with underscores, remove special characters, and make lowercase
    sanitized = ''.join(e for e in name if e.isalnum() or e == ' ')
    return sanitized.replace(' ', '_').replace('.', '').lower()

def setup_database(keys_to_extract):
    conn = None
    try:
        conn = sqlite3.connect('applications.db')
        cursor = conn.cursor()
        
        # Generating the column names and types dynamically
        columns = ", ".join([f"{sanitize_column_name(key)} {value}" for key, value in keys_to_extract.items()])
        
        # SQL command
        sql = f'''
        CREATE TABLE IF NOT EXISTS ApplicationData (
            id INTEGER PRIMARY KEY,
            {columns}
        )
        '''
        cursor.execute(sql)
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error occurred: {e}")
    finally:
        if conn:
            conn.close()
            
setup_database(keys_to_extract)

