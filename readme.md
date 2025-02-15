# CS50 Final Project - Form Parser

#### **Video Demo:** https://www.youtube.com/watch?v=beN0jdlOnrc

#### **Description:**

* Form Parser is a Flask-based web application that is able to extract and analyze data from handwritten documents using computer vision (specifically the Amazon Textract API).

* It was developed using Python, HTML, with snippets of JavaScript and SQL.

* The current version is modified to process handwritten job applications, a common document for companies that hire many blue-collar workers.

* The source code can be further tweaked to handle a variety of forms and PDFs with key-value pairs.

&nbsp;

---

#### **Inspiration:**

* My inspiration for this project stemmed from the desire to simplify and expedite time-consuming data-entry tasks inherent in many business operations.


&nbsp;

---


#### **Real-World Applications:**

Automated extraction and processing of data from documents can be immensely valuable in various industries and tasks. Here are some real-world applications:

* **Invoice Management:** Extracting invoice numbers, dates, vendor names, and amounts from invoices for automated payment or auditing.

* **Supply Chain and Logistics:** Extracting product IDs, shipment dates, and quantities from shipping and receiving documents to automate inventory management.

* **Healthcare:** Extracting patient details like name, date of birth, medication, and diagnosis from medical records to streamline patient management.

* **Banking:** Extracting account numbers, transaction dates, and amounts from bank statements to automate the reconciliation process.

&nbsp;

---

### **Main Functions (simplified):**


#### **Upload**

* Splits the selected PDF into individual pages, and uploads these pages into an Amazon S3 bucket



#### **Analyze**
* Runs a for-loop for each file in the S3 bucket, calling Amazon Textract to:
    * Read the document
    * Extract the assigned key-value pairs from each page (Can be tweaked in app.py to extract different key-value pairs)
    * Insert extracted data into a database in the working directory (applications.db)


#### **Filter**
* Compares the user-inputted filter parameters against the value in the database
* Other auxiliary functions such as calculating the total number of applicants, and sorting the data based on the number of skill matches

&nbsp;

---

### Requirements:

* Because this app utilizes the Amazon Textract API, an Amazon Web Services (AWS) account is required. [Link to AWS](aws.amazon.com)

* This app requires you to create an AWS account and obtain an AWS access key and AWS secret access key. The app is designed to pull your access keys from your environment variables, as represented with the code on line 34:

```
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY') 
```

You can store your access keys in environment variables by doing the following:

&nbsp;

**1. For Windows:**

* Open the start menu, type Environment Variables, then choose "Edit the system environment variables."
* In the System Properties window, click the “Environment Variables” button.
* Under the "User variables" section, click the "New" button.
* For "Variable name", enter AWS_ACCESS_KEY_ID and for "Variable value", enter your actual AWS Access Key ID.
* Click OK.
* Repeat the process to add another user variable with the name AWS_SECRET_ACCESS_KEY and your actual AWS Secret Access Key as the value.
* Click OK again to apply the changes.

&nbsp;

**2. For macOS and Linux:**

* Open your terminal.
* Use the export command to set each variable. For example:

```
export AWS_ACCESS_KEY_ID=your_actual_access_key_id
export AWS_SECRET_ACCESS_KEY=your_actual_secret_access_key
```

