# CS50 Final Project - Form Parser

#### Video Demo: https://www.youtube.com/watch?v=beN0jdlOnrc

#### Description: 

* Form Parser is a Flask-based web application that is able to extract and analyze data from pdfs using computer vision (Specifically the Amazon Textract API)

* Languages include Python, HTML, and a bit of Javascript and SQL

---

### Main Functions:


#### Upload

* Splits the selected PDF into individual pages, and uploads these pages into an assigned Amazon S3 bucket


#### Analyze
* Calls the Amazon Textract API on the individual pages in the S3 bucket


