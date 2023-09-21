import os
import sqlite3
import boto3
from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, session, send_from_directory, url_for, jsonify
from flask_session import Session
from trp import Document
from helpers import clean_text
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.debug = True



# Configurations
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER



# -------------
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

# -------------
# Other Configs

job_data = {} # in-memory storage for the job information

# -------------

@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")


@app.route('/jobinformation', methods=['GET', 'POST'])
def job_information():
    if request.method == 'POST':
        job_data['jobTitle'] = request.form['jobTitle']
        job_data['yearsOfExperience'] = request.form['yearsOfExperience']
        job_data['jobLocation'] = request.form['jobLocation']
        job_data['salary'] = request.form['salary']
        job_data['keyWords'] = request.form['keyWords']
        
        infomsg = "Info Successfully Submitted"

        print(job_data['jobTitle'])
        print(job_data['yearsOfExperience'])
        print(job_data['jobLocation'])
        print(job_data['salary'])
        print(job_data['keyWords'])
        
        return render_template("index.html", infomsg=infomsg, job_data=job_data)
    else:
        infomsg = "Failed to Submit Info"
        return render_template("index.html", infomsg=infomsg, job_data=job_data)



@app.route('/upload', methods=["POST"])
def upload():
    if request.method == "POST":
        pdf = request.files['file']
        if pdf:
            filename = secure_filename(pdf.filename)
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            pdf.save(full_path)
            
            # Add timestamp to the filename for S3
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            s3_filename = f"{filename.rsplit('.', 1)[0]}_{timestamp}.{filename.rsplit('.', 1)[1]}"
            
            s3.upload_file(
                Bucket=bucket_name,
                Filename=full_path,  # Use the full path here
                Key=s3_filename
            )
            uploadmsg = "File Successfully Uploaded"
            return render_template("index.html", uploadmsg=uploadmsg)
        else:
            uploadmsg = "Failed to Upload File"
            return render_template("index.html", uploadmsg=uploadmsg)
    

@app.route("/execute", methods=["POST"])
def execute():

    # Config:
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

    # Fetch the most recently uploaded file from S3 bucket
    objs = s3.list_objects_v2(Bucket=bucket_name)['Contents']
    objs.sort(key=lambda e: e['LastModified'], reverse=True)
    latest_file = objs[0]['Key']

    # Call Amazon Textract
    response = textract.analyze_document(
        Document={'S3Object': {'Bucket': bucket_name, 'Name': latest_file}},
        FeatureTypes=["FORMS"]
    )
    doc = Document(response)
    print("doc:") #check

    for key in keys_to_extract:
        print(key)
    
    def add_colons(keys_to_extract):
        return [key + ":" for key in keys_to_extract]
    cleaned_keys = add_colons(keys_to_extract)
     
    # Establish a connection to the database
    conn = sqlite3.connect('applications.db')
    cursor = conn.cursor()

    # Clear all data in the ApplicationData table
    try:
        cursor.execute("DELETE FROM ApplicationData")
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error deleting data: {e}")
    
    data_to_insert = {}
    for page in doc.pages:
        for key in cleaned_keys:
            field = page.form.getFieldByKey(key)
            if field:
                sanitized_key = sanitize_column_name(key.replace(':', ''))
                data_to_insert[sanitized_key] = str(field.value)

    columns_str = ', '.join(data_to_insert.keys())
    placeholders = ', '.join(['?'] * len(data_to_insert))
    values_tuple = tuple(data_to_insert.values())

    sql = f"INSERT INTO ApplicationData ({columns_str}) VALUES ({placeholders})"
    try:
        cursor.execute(sql, values_tuple)
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error inserting data: {e}")
    finally:
        conn.close()
    
    executemsg = "Data successfully stored in the database!" 
    return render_template("index.html", executemsg=executemsg)


@app.route("/analyze", methods=["POST"])
def analyze():
    # Connect to the SQLite database
    conn = sqlite3.connect('applications.db')
    cursor = conn.cursor()

    # Extract the user's input skills
    user_skills = [skill.strip().lower() for skill in job_data['keyWords'].split(',')]

    # Execute the SQL query
    cursor.execute('SELECT first_name, last_name, years_of_experience, your_relevant_skills FROM ApplicationData')
    
    # Fetch all rows
    rows = cursor.fetchall()

    # Close the connection
    conn.close()

    # Format the data and compute the number of skill matches for each application
    data = []
    for row in rows:
        # Get the list of matched skills for the current application
        cleaned_app_skills = row[3].lower()
        matched_skills_list = [skill for skill in user_skills if skill in cleaned_app_skills]
        
        # Convert the list to a comma-separated string
        matched_skills = ', '.join(matched_skills_list)

        data.append({
            "first_name": row[0],
            "last_name": row[1],
            "years_of_experience": row[2],
            "your_relevant_skills": row[3],
            "match_count": len(matched_skills_list),  # Use the length of matched_skills_list for the match_count
            "matched_skills": matched_skills,
        })

    print(user_skills)

    # Return the formatted data as JSON
    return jsonify(data)        



'''    
    # Function to process and extract data from the document based on a given key
    def process_field(page, key_name):
    # Helper function to format the key for database insertion
        def format_key(key):
            return key.replace(" ", "_").lower()

        # Helper function to extract data from a field
        def extract_data_from_field(field, data_dict):
            if field.key in keys_to_extract.keys():
                print("Key: {}, Value: {}".format(field.key, field.value))
                data_dict[format_key(field.key)] = field.value

        data = {}  # Dictionary to store key-value pairs for database insertion

        main_field = page.form.getFieldByKey(key_name)
        if main_field:
            extract_data_from_field(main_field, data)

        fields_found = page.form.searchFieldsByKey(key_name)
        for field in fields_found:
            extract_data_from_field(field, data)

        print("data:")
        print(data)
        
        return data


   # Accumulate data from all keys
    accumulated_data = {}  

    for page in doc.pages:
        for key in keys_to_extract.keys():
            data_for_key = process_field(page, key)
            accumulated_data.update(data_for_key)
        print(data_for_key) #check




    # Insert the accumulated data into the database
    print(accumulated_data)
    insert_data_into_db(accumulated_data)

    executemsg = "Data successfully stored in the database!"
    return render_template("index.html", executemsg=executemsg)

'''
