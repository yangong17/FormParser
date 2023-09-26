import os
import sqlite3
import boto3
from PyPDF2 import PdfReader, PdfWriter
import tempfile
from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, session, send_from_directory, url_for, jsonify
from flask_session import Session
from trp import Document
from helpers import clean_text
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = 'yangong'
app.debug = True


# =======================================================================
# Configurations
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER



# =======================================================================
# Amazon Config

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY_ID = os.environ.get('AWS_SECRET_ACCESS_KEY')

s3 = boto3.client('s3',
                  aws_access_key_id=AWS_ACCESS_KEY_ID,
                  aws_secret_access_key=AWS_SECRET_ACCESS_KEY_ID)

textract = boto3.client('textract', 
                        aws_access_key_id = AWS_ACCESS_KEY_ID, 
                        aws_secret_access_key = AWS_SECRET_ACCESS_KEY_ID, 
                        region_name = 'us-west-1')

bucket_name = 'formparser'

# =======================================================================
# Other Configs

job_data = {} # in-memory storage for the job information

# =======================================================================
# Home Page

@app.route("/", methods=["GET", "POST"])
def index():
    
    job_data['yearsOfExperience'] = 0
    job_data['salary'] = 0
    job_data['keyWords'] = 'none'
    

    # Fetch data from the database
    conn = sqlite3.connect('applications.db')
    cursor = conn.cursor()

    cursor.execute('SELECT first_name, last_name, email_address, desired_salaryrate, years_of_experience, your_relevant_skills FROM ApplicationData')
    rows = cursor.fetchall()

    conn.close()

    data = []
    for row in rows:
        data.append({
            "first_name": row[0],
            "last_name": row[1],
            "email_address": row[2],
            "desired_salaryrate": int(row[3]),
            "years_of_experience": row[4],
            "your_relevant_skills": row[5],
            "match_count": 0,
            "matched_skills": ""
        })

    # Render the template and pass the data
    return render_template("index.html", job_data=job_data, table_data=data)

# =======================================================================
# Upload Forms (/upload)

@app.route('/upload', methods=["POST"])
def upload():
    if request.method == "POST":
        pdf = request.files['file']
        if pdf:
            # Step 1: List all objects in the S3 bucket
            objects = s3.list_objects_v2(Bucket=bucket_name)
            
            # Step 2: Delete each object
            if 'Contents' in objects:
                for obj in objects['Contents']:
                    s3.delete_object(Bucket=bucket_name, Key=obj['Key'])
            
            filename = secure_filename(pdf.filename)
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            pdf.save(full_path)
            
            # Open the PDF and determine the number of pages
            with open(full_path, 'rb') as fr:
                reader = PdfReader(fr)
                total_pages = len(reader.pages)
                
                for page_num in range(total_pages):
                    writer = PdfWriter()
                    writer.add_page(reader.pages[page_num])

                    # Save each page to a temp file
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as page_file:
                        writer.write(page_file)
                        page_file_name = page_file.name

                    # Add timestamp to the filename for S3
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    s3_filename = f"{filename.rsplit('.', 1)[0]}_page{page_num + 1}_{timestamp}.{filename.rsplit('.', 1)[1]}"

                    # Upload the single-page PDF to the S3 bucket
                    s3.upload_file(
                        Bucket=bucket_name,
                        Filename=page_file_name, 
                        Key=s3_filename
                    )
                    os.remove(page_file_name)  # Delete the temp file after uploading
            
            uploadmsg = f"File Successfully Uploaded and Split into {total_pages} page(s)"
            session['file_uploaded'] = True
            return render_template("index.html", uploadmsg=uploadmsg)
        else:
            uploadmsg = "Failed to Upload File"
            return render_template("index.html", uploadmsg=uploadmsg)

# =======================================================================
# Analyze with Amazon Textract (/execute)

@app.route("/execute", methods=["POST"])
def execute():

# Config:

    #Check if file had been uploaded
    if 'file_uploaded' not in session:
        session['file_uploaded'] = False

    # List of keys to extract from the document and their data type (For database)
    keys_to_extract = {
        "First Name": "TEXT",
        "Last Name": "TEXT",
        "M.I": "TEXT",
        "Date": "DATE",
        "Street Address": "TEXT",
        "Apartment/Unit#": "TEXT",
        "City": "TEXT",
        "State": "TEXT",
        "ZIP Code": "INTEGER",
        "Phone": "TEXT",
        "E-mail Address": "TEXT",
        "Job Title": "TEXT",
        "Job(s) You're Applying For": "TEXT",
        "Years of Experience": "INTEGER",
        "Desired Salary/Rate": "REAL",
        "Earliest Date Available": "DATE",
        "Your Relevant Skills": "TEXT"
    }
    
    # Counter for total pages processed
    total_pages_processed = 0

# =======================================================================

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
    

    # Fetch all files from S3 bucket
    objs = s3.list_objects_v2(Bucket=bucket_name)['Contents']
    files_to_process = [obj['Key'] for obj in objs]

    # Establish a connection to the database
    conn = sqlite3.connect('applications.db')
    cursor = conn.cursor()

    # Delete all entries in the table "ApplicationData"
    try:
        cursor.execute("DELETE FROM ApplicationData")
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error deleting data: {e}")

    for file_key in files_to_process:
        print(f"Processing file: {file_key}")
        
        # CALL AMAZON TEXTRACT
        response = textract.analyze_document(
            Document={'S3Object': {'Bucket': bucket_name, 'Name': file_key}},
            FeatureTypes=["FORMS"]
        )

        doc = Document(response)
        
        def add_colons(keys_to_extract):
            return [key + ":" for key in keys_to_extract]
        cleaned_keys = add_colons(keys_to_extract)
            
        all_data_to_insert = []  #List to hold data for all pages

        for page in doc.pages: 
            data_to_insert = {}
            for key in cleaned_keys:
                field = page.form.getFieldByKey(key)
                if field:
                    sanitized_key = sanitize_column_name(key.replace(':', ''))
                    data_to_insert[sanitized_key] = str(field.value)
            all_data_to_insert.append(data_to_insert)  #Append each page's data
            total_pages_processed += 1 #Update counter for each page processed

        #Insert data for all pages into local database
        for data_to_insert in all_data_to_insert:
            columns_str = ', '.join(data_to_insert.keys())
            placeholders = ', '.join(['?'] * len(data_to_insert))
            values_tuple = tuple(data_to_insert.values())

            sql = f"INSERT INTO ApplicationData ({columns_str}) VALUES ({placeholders})"
            try:
                cursor.execute(sql, values_tuple)
                conn.commit()
            except sqlite3.Error as e:
                print(f"Error inserting data: {e}")
        

    conn.close()
    
    executemsg = f"{total_pages_processed} page(s) analyzed and imported into applications.db" 
    return render_template("index.html", executemsg=executemsg)

# =======================================================================
# Filter data (/filter)

@app.route('/filter', methods=['GET', 'POST'])
def filter():
     
    if request.method == 'POST':
        job_data['yearsOfExperience'] = request.form['yearsOfExperience']
        job_data['salary'] = request.form['salary']
        job_data['keyWords'] = request.form['keyWords']
        
        infomsg = "Info Successfully Submitted"

        # Connect to the SQLite database
        conn = sqlite3.connect('applications.db')
        cursor = conn.cursor()

        # Extract the user's input skills
        user_skills = [skill.strip().lower() for skill in job_data['keyWords'].split(',')]

        # Execute the SQL query
        cursor.execute('SELECT first_name, last_name, email_address, desired_salaryrate, years_of_experience, your_relevant_skills FROM ApplicationData')
    
        # Fetch all rows
        rows = cursor.fetchall()

        # Close the connection
        conn.close()

        # Format the data and compute the number of skill matches for each application
        data = []
        for row in rows:
            # Get the list of matched skills for the current application
            cleaned_app_skills = row[5].lower()
            matched_skills_list = [skill for skill in user_skills if skill in cleaned_app_skills]
        
            # Convert the list to a comma-separated string
            matched_skills = ', '.join(matched_skills_list)

            data.append({
                "first_name": row[0],
                "last_name": row[1],
                "email_address": row[2],
                "desired_salaryrate": int(row[3]),
                "years_of_experience": row[4],
                "your_relevant_skills": row[5],
                "match_count": len(matched_skills_list),
                "matched_skills": matched_skills,
            })

        # Sort the data by match_count (highest first)
        sorted_data = sorted(data, key=lambda x: x["match_count"], reverse=True)

        return render_template("index.html", infomsg=infomsg, table_data=sorted_data, job_data=job_data)
    else:
        infomsg = "Failed to Submit Info"
        return render_template("index.html", infomsg=infomsg, job_data=job_data)


  




