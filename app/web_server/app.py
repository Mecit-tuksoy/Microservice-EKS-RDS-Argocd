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
        'host': db_credentials['host'],
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

# Write a function named `init_phonebook_db`
def init_phonebook_db():
    phonebook_table = f"""
    CREATE TABLE IF NOT EXISTS {project_db}.phonebook (
        id INT NOT NULL AUTO_INCREMENT,
        name VARCHAR(100) NOT NULL,
        number VARCHAR(100) NOT NULL,
        PRIMARY KEY (id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            cursor.execute(phonebook_table)
        connection.commit()
        connection.close()
    except Exception as e:
        print(f"Error initializing database: {e}")

# Write a function named `insert_person`
def insert_person(name, number):
    select_query = "SELECT * FROM phonebook WHERE name LIKE %s;"
    like_name = name.strip().lower()
    insert_query = "INSERT INTO phonebook (name, number) VALUES (%s, %s);"
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            cursor.execute(select_query, (like_name,))
            row = cursor.fetchone()
            if row:
                connection.close()
                return f'Person with name {row["name"].title()} already exists.'
            cursor.execute(insert_query, (like_name, number))
        connection.commit()
        connection.close()
        return f'Person {name.strip().title()} added to Phonebook successfully'
    except Exception as e:
        print(f"Error inserting person: {e}")
        return 'Error occurred while adding person.'

# Write a function named `update_person`
def update_person(name, number):
    select_query = "SELECT * FROM phonebook WHERE name LIKE %s;"
    like_name = name.strip().lower()
    update_query = "UPDATE phonebook SET number = %s WHERE id = %s;"
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            cursor.execute(select_query, (like_name,))
            row = cursor.fetchone()
            if not row:
                connection.close()
                return f'Person with name {name.strip().title()} does not exist.'
            cursor.execute(update_query, (number, row['id']))
        connection.commit()
        connection.close()
        return f'Phone record of {name.strip().title()} is updated successfully'
    except Exception as e:
        print(f"Error updating person: {e}")
        return 'Error occurred while updating person.'

# Write a function named `delete_person`
def delete_person(name):
    select_query = "SELECT * FROM phonebook WHERE name LIKE %s;"
    like_name = name.strip().lower()
    delete_query = "DELETE FROM phonebook WHERE id = %s;"
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            cursor.execute(select_query, (like_name,))
            row = cursor.fetchone()
            if not row:
                connection.close()
                return f'Person with name {name.strip().title()} does not exist, no need to delete.'
            cursor.execute(delete_query, (row['id'],))
        connection.commit()
        connection.close()
        return f'Phone record of {name.strip().title()} is deleted from the phonebook successfully'
    except Exception as e:
        print(f"Error deleting person: {e}")
        return 'Error occurred while deleting person.'

# Write a function named `add_record`
@app.route('/add', methods=['GET', 'POST'])
def add_record():
    if request.method == 'POST':
        name = request.form['username']
        if not name or not name.strip():
            return render_template('add-update.html', not_valid=True, message='Invalid input: Name can not be empty', show_result=False, action_name='save', developer_name='Mecit')
        elif name.strip().isdecimal():
            return render_template('add-update.html', not_valid=True, message='Invalid input: Name of person should be text', show_result=False, action_name='save', developer_name='Mecit')

        phone_number = request.form['phonenumber']
        if not phone_number or not phone_number.strip():
            return render_template('add-update.html', not_valid=True, message='Invalid input: Phone number can not be empty', show_result=False, action_name='save', developer_name='Mecit')
        elif not phone_number.strip().isdecimal():
            return render_template('add-update.html', not_valid=True, message='Invalid input: Phone number should be in numeric format', show_result=False, action_name='save', developer_name='Mecit')

        result = insert_person(name, phone_number)
        return render_template('add-update.html', show_result=True, result=result, not_valid=False, action_name='save', developer_name='Mecit')
    else:
        return render_template('add-update.html', show_result=False, not_valid=False, action_name='save', developer_name='Mecit')

# Write a function named `update_record`
@app.route('/update', methods=['GET', 'POST'])
def update_record():
    if request.method == 'POST':
        name = request.form['username']
        if not name or not name.strip():
            return render_template('add-update.html', not_valid=True, message='Invalid input: Name can not be empty', show_result=False, action_name='update', developer_name='Mecit')
        
        phone_number = request.form['phonenumber']
        if not phone_number or not phone_number.strip():
            return render_template('add-update.html', not_valid=True, message='Invalid input: Phone number can not be empty', show_result=False, action_name='update', developer_name='Mecit')
        elif not phone_number.strip().isdecimal():
            return render_template('add-update.html', not_valid=True, message='Invalid input: Phone number should be in numeric format', show_result=False, action_name='update', developer_name='Mecit')

        result = update_person(name, phone_number)
        return render_template('add-update.html', show_result=True, result=result, not_valid=False, action_name='update', developer_name='Mecit')
    else:
        return render_template('add-update.html', show_result=False, not_valid=False, action_name='update', developer_name='Mecit')

# Write a function named `delete_record`
@app.route('/delete', methods=['GET', 'POST'])
def delete_record():
    if request.method == 'POST':
        name = request.form['username']
        if not name or not name.strip():
            return render_template('delete.html', not_valid=True, message='Invalid input: Name can not be empty', show_result=False, developer_name='Mecit')
        result = delete_person(name)
        return render_template('delete.html', show_result=True, result=result, not_valid=False, developer_name='Mecit')
    else:
        return render_template('delete.html', show_result=False, not_valid=False, developer_name='Mecit')

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
    init_phonebook_db()
    app.run(host='0.0.0.0', port=80)
