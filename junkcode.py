# Call Amazon Textract
response = textract.analyze_document(
    Document={'S3Object': {'Bucket': bucket_name, 'Name': latest_file}},
    FeatureTypes=["FORMS"]
)
doc = Document(response)

for page in doc.pages:
    
    key = 'Pay'
    field = page.form.getFieldByKey(key)
    if(field):
        print("Key: {}, Value: {}".format(field.key, field.value))
        
    field_amt = page.form.searchFieldsbyKey("Rupees")
    for f in field_amt:
        print("Key: {}, Value: {}".format(f.key, f.value))
        text.append(f.key)
        text.append(f.value)
        
    print(text)
    key = "A/c No"
    fields = page.form.searchFieldsByKey(key)
        
