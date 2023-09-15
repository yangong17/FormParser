import csv
import io
import os
import boto3
import time
import string
import sqlite3

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'pdf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# -------

def clean_text(text):
    
    # List of stop words to remove
    stop_words = ["and", "to", "the", "of", "in", "on", "with", "for", "as", "by", "an", "a", "is", "it", "at", "or"]

    # Remove unwanted characters and punctuation
    text = text.replace("\r", " ").replace("\n", " ")
    text = ''.join([char for char in text if char not in string.punctuation])

    # Tokenize the string
    words = text.split()

    # Remove stop words
    cleaned_words = [word for word in words if word.lower() not in stop_words]

    return ' '.join(cleaned_words)

# -------

def setup_database(keys_to_extract):
    try:
        conn = sqlite3.connect('applications.db')
        cursor = conn.cursor()
        
        # Generating the column names and types dynamically
        columns = ", ".join([f"{key.replace(' ', '_').lower()} {value}" for key, value in keys_to_extract.items()])
        
        # SQL command
        sql = f'''
        CREATE TABLE IF NOT EXISTS ApplicationData (
            id INTEGER PRIMARY KEY,
            {columns}
        )
        '''
        
        cursor.execute(sql)
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"Error occurred: {e}")

# -------

def insert_data_into_db(data):
    conn = sqlite3.connect('applications.db')
    cursor = conn.cursor()

    # Convert keys to valid named placeholders
    formatted_keys = [key.replace(" ", "_").lower() for key in data.keys()]

    columns = ', '.join(formatted_keys)
    placeholders = ':' + ', :'.join(formatted_keys)

    sql = f"INSERT INTO ApplicationData ({columns}) VALUES ({placeholders})"

    # Create a new dictionary with formatted keys to match placeholders
    formatted_data = {key.replace(" ", "_").lower(): value for key, value in data.items()}

    cursor.execute(sql, formatted_data)
    conn.commit()
    conn.close()

