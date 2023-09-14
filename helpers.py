import csv
import io
import os
import boto3
import time

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'pdf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def process_with_textract(file_path):
    # S3 bucket name
    bucket_name = 'formparser'
    
    # Get just the filename for S3
    s3_object_name = os.path.basename(file_path)
    
    # Initialize the S3 and Textract clients
    s3 = boto3.client('s3', region_name='us-west-1')
    textract = boto3.client('textract', region_name='us-west-1')

    # Upload the file to the S3 bucket
    with open(file_path, 'rb') as file:
        s3.upload_fileobj(file, bucket_name, file_path)

    # Start the text detection process using the S3 object
    response = textract.start_document_text_detection(
        DocumentLocation={
            'S3Object': {
                'Bucket': bucket_name,
                'Name': file_path
            }
        }
    )

    job_id = response['JobId']
    status = 'IN_PROGRESS'

    # Poll the results of the job until it's no longer in progress
    while status == 'IN_PROGRESS':
        time.sleep(5)  # Delay for 5 seconds
        response = textract.get_document_text_detection(JobId=job_id)
        status = response['JobStatus']

    # Check if the job failed
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

    # Convert the extracted data to CSV format
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Key', 'Value'])
    for key, value in extracted_data.items():
        writer.writerow([key, value])

    # Get the content of the StringIO object
    csv_content = output.getvalue()

    # Save the CSV content to a file
    with open('output.csv', 'w') as csv_file:
        csv_file.write(csv_content)

    delete_from_s3(bucket_name, s3_object_name)

def delete_from_s3(bucket_name, object_key):
    s3_client = boto3.client('s3', region_name='us-west-1')  # Adjust the region_name if necessary
    s3_client.delete_object(Bucket=bucket_name, Key=object_key)

#def convert_to_csv(data):
 #   """Convert a list of dictionaries to a CSV string."""
  #  output = StringIO()
   # writer = csv.DictWriter(output, fieldnames=data[0].keys())
   # writer.writeheader()
   # writer.writerows(data)
   # return output.getvalue()