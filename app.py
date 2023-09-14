import os
import sqlite3
import boto3
from datetime import datetime
from flask import Flask, flash, redirect, render_template, request, session, send_from_directory, url_for, jsonify
from flask_session import Session
from trp import Document
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


app = Flask(__name__)

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


@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")

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
            msg = "File Successfully Uploaded"
            return render_template("index.html", msg=msg)
        else:
            msg = "Failed to Upload File"
            return render_template("index.html", msg=msg)
    

@app.route("/execute", methods=["POST"])
def execute():
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
    text = []
    for page in doc.pages:

        key = "First Name"
        field = page.form.getFieldByKey(key)
        if(field):
            print("Key: {}, Value: {}".format(field.key, field.value))

        field_amt = page.form.searchFieldsByKey("First Name")
        for f in field_amt:
            print("Key: {}, Value: {}".format(f.key, f.value))
            text.append(f.key)
            text.append(f.value)

        key = "Last Name"
        field = page.form.getFieldByKey(key)
        if(field):
            print("Key: {}, Value: {}".format(field.key, field.value))

        field_amt = page.form.searchFieldsByKey("Last Name")
        for f in field_amt:
            print("Key: {}, Value: {}".format(f.key, f.value))
            text.append(f.key)
            text.append(f.value)

        return render_template("index.html", text=text)

    
    #doc = Document(response)
    #text = []
    #for page in doc.pages:

     #   key = "First Name"
        #field = page.form.getFieldByKey(key)
        #if(field):
            #print("Key: {}, Value: {}".format(field.key, field.value))
#
        #key = "Last Name"
        #field = page.form.getFieldByKey(key)
        #if(field):
            #print("Key: {}, Value: {}".format(field.key, field.value))
#
        #key = "M.I"
        #field = page.form.getFieldByKey(key)
        #if(field):
            #print("Key: {}, Value: {}".format(field.key, field.value))
#
        #key = "Date"
        #field = page.form.getFieldByKey(key)
        #if(field):
            #print("Key: {}, Value: {}".format(field.key, field.value))
#
    #return render_template("index.html")

        


# @app.route('/download/<filename>')
# def download(filename):
#    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)