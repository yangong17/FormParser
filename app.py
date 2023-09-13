import os
import sqlite3
from flask import Flask, flash, redirect, render_template, request, session, send_from_directory, url_for
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from helpers import allowed_file, process_with_textract, convert_to_csv

app = Flask(__name__)

# Configurations
DATABASE = 'pdf_processor.db'
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files.get('pdf')

        # Check if the file is present in the request and has a valid filename
        if not file or file.filename == '' or not allowed_file(file.filename):
            flash('Invalid or no file uploaded.')
            return redirect(request.url)

        # Save the file
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # Store the filename in the session for further use
        session['filename'] = filename

        flash('File successfully uploaded.')
        return redirect(url_for('index'))

    return render_template("index.html")



@app.route("/execute", methods=["POST"])
def execute():
    # Assuming you've stored the filename in the session or elsewhere
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], session.get('filename'))
    
    # Process with Textract
    extracted_data = process_with_textract(file_path)
    
    # Convert the extracted_data to CSV (you can use Python's csv library)
    csv_output = convert_to_csv(extracted_data)
    
    # Save the CSV to a file or store it somewhere
    csv_filename = "output.csv"
    with open(os.path.join(app.config['UPLOAD_FOLDER'], csv_filename), 'w') as csv_file:
        csv_file.write(csv_output)

    # Return some status info (like number of pages processed, F1 score, etc.)
    return {
        "status": "success",
        "pages_processed": len(extracted_data),  # This is just a placeholder. Adjust based on your needs.
        "f1_score": "0.95",  # This is also a placeholder. Adjust based on your real calculations.
        "csv_filename": csv_filename
    }

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)