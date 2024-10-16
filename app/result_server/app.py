# Import Flask modules
from flask import Flask, request, render_template
import pymysql
import os
import boto3
import json

# Create an object named app
app = Flask(__name__)

# Function to get database credentials and endpoint from AWS Secrets Manager
def get_db_credentials():
    credentials_secret_name = "prod/mysql/credentials"  # Manuel olarak oluşturduğunuz secret
    endpoint_secret_name = "prod/mysql/endpoint"        # Terraform ile oluşturduğunuz endpoint secret
    region_name = "us-east-1"                           # Kendi bölgenizi buraya yazın

    # Boto3 client oluştur
    client = boto3.client(
        service_name="secretsmanager",
        region_name=region_name
    )

    try:
        # Secret'ı al (credentials)
        credentials_response = client.get_secret_value(SecretId=credentials_secret_name)
        credentials_secret = credentials_response['SecretString']
        credentials_dict = json.loads(credentials_secret)

        # Secret'ı al (endpoint)
        endpoint_response = client.get_secret_value(SecretId=endpoint_secret_name)
        endpoint_secret = endpoint_response['SecretString']
        endpoint_dict = json.loads(endpoint_secret)

        # İki secret'ı birleştir
        credentials_dict.update(endpoint_dict)  # endpoint bilgilerini credentials'a ekle
        return credentials_dict

    except Exception as e:
        print(f"Error retrieving secrets: {str(e)}")
        return None

# Get database credentials from AWS Secrets Manager
db_credentials = get_db_credentials()

# Configure MySQL database using credentials from Secrets Manager
if db_credentials:
    db_config = {
        'host': db_credentials['host'],          # Endpoint secret'tan geliyor
        'user': db_credentials['username'],
        'password': db_credentials['password'],
        'db': db_credentials['dbname'],
        'port': int(db_credentials.get('port', 3306)),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }
    project_db = db_credentials.get('project', 'phonebook')
else:
    print("Failed to load database credentials from AWS Secrets Manager.")
    db_config = {}

# Write a function named `find_persons`
def find_persons(keyword):
    query = "SELECT id, name, number FROM phonebook WHERE LOWER(name) LIKE %s;"
    like_keyword = f"%{keyword.strip().lower()}%"
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            cursor.execute(query, (like_keyword,))
            result = cursor.fetchall()
        connection.close()
        persons = [{'id': row['id'], 'name': row['name'].strip().title(), 'number': row['number']} for row in result]
        if not persons:
            persons = [{'name':'No Result', 'number':'No Result'}]
        return persons
    except Exception as e:
        print(f"Error in find_persons: {e}")
        return [{'name':'Error', 'number':'Error'}]

# Write a function named `find_records`
@app.route('/', methods=['GET', 'POST'])
def find_records():
    if request.method == 'POST':
        keyword = request.form['username']
        persons = find_persons(keyword)
        return render_template('index.html', persons=persons, keyword=keyword, show_result=True, developer_name='Mecit')
    else:
        return render_template('index.html', show_result=False, developer_name='Mecit')

# Add a statement to run the Flask application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
