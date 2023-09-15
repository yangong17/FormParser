import os
import sqlite3
import boto3
from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, session, send_from_directory, url_for, jsonify
from flask_session import Session
from trp import Document
from helpers import clean_text, setup_database, insert_data_into_db
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
        job_data['keyWords'] = clean_text(request.form['keyWords']).split(' ')
        
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
        img = request.files['file']
        if img:
            filename = secure_filename(img.filename)
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            img.save(full_path)
            
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
    # List of keys to extract from the document and their data type
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


    # Check if the database exists
    if not os.path.exists('applications.db'):
        setup_database(keys_to_extract)
    else:
        # If it exists, delete all data from the ApplicationData table
        conn = sqlite3.connect('applications.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ApplicationData")
        conn.commit()
        conn.close()

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
    
    # Function to process and extract data from the document based on a given key
    def process_field(page, key_name):
        field = page.form.getFieldByKey(key_name)

        data = {}  # Dictionary to store key-value pairs for database insertion

        if field and field.key in keys_to_extract.keys():
            print("Key: {}, Value: {}".format(field.key, field.value))
            # Store the key-value pair in the dictionary
            data[field.key.replace(" ", "_").lower()] = field.value

        field_amt = page.form.searchFieldsByKey(key_name)
        for f in field_amt:
            if f.key in keys_to_extract.keys():
                print("Key: {}, Value: {}".format(f.key, f.value))
                # Store the key-value pair in the dictionary
                data[f.key.replace(" ", "_").lower()] = f.value

        return data

    # Accumulate data from all keys
    accumulated_data = {}  

    for page in doc.pages:
        for key in keys_to_extract.keys():
            data_for_key = process_field(page, key)
            accumulated_data.update(data_for_key)

    # Insert the accumulated data into the database
    insert_data_into_db(accumulated_data)

    executemsg = "Data successfully stored in the database!"
    return render_template("index.html", executemsg=executemsg)