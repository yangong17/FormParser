import boto3
import csv
from io import StringIO

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'pdf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


import boto3
import time

def process_with_textract(file_path):
    # Initialize the Textract client
    client = boto3.client('textract', region_name='us-west-1')  # Make sure to replace 'your_region_name' with the appropriate AWS region.

    # Start the text detection process
    with open(file_path, 'rb') as file:
        start_response = client.start_document_text_detection(Document={'Bytes': file.read()})

    job_id = start_response['JobId']

    # Initially set the status to indicate that the job is in progress
    status = 'IN_PROGRESS'

    # Poll the results of the job until it's no longer in progress
    while status == 'IN_PROGRESS':
        time.sleep(5)  # Delay for 5 seconds before checking the job status again
        response = client.get_document_text_detection(JobId=job_id)
        status = response['JobStatus']

    # Once out of the loop, the job should be either 'SUCCEEDED', 'FAILED', or 'PARTIAL_SUCCESS'
    if status == 'FAILED':
        print(f"Text detection failed with reason: {response['StatusMessage']}")
        return {}

    # Extract key-value pairs from the Textract response
    extracted_data = {}
    for item in response["Blocks"]:
        if item["BlockType"] == "KEY_VALUE_SET":
            if 'KEY' in item['EntityTypes']:
                key = item['Text']
                value_block_id = item['Relationships'][0]['Ids'][0]
                
                for block in response["Blocks"]:
                    if block['Id'] == value_block_id:
                        value = block['Text']
                        extracted_data[key] = value

    return extracted_data



def convert_to_csv(data):
    """Convert a list of dictionaries to a CSV string."""
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()