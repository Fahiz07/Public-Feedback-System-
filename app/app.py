import os
from flask import Flask, request, render_template, session, redirect, url_for, Response, flash
from io import BytesIO
import xlsxwriter
import sqlite3
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
import nltk
from joblib import load
import re
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Download NLTK resources
nltk.download('punkt')

app = Flask(__name__)

# Configure SQLite database
DATABASE = 'database.db'

# Define function to send email
def send_email(subject, recipient, body):
    sender_email = 'codingdoor607@gmail.com'
    password = 'mubizvevtdufnxlg'
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient
    msg['Subject'] = subject
    
    msg.attach(MIMEText(body, 'plain'))
    
    # Connect to SMTP server
    with smtplib.SMTP('smtp.example.com', 587) as smtp:
        smtp.starttls()
        smtp.login(sender_email, password)
        
        # Send email
        smtp.send_message(msg)

def create_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  name TEXT,
                  email TEXT, 
                  mobile INTEGER, 
                  username TEXT UNIQUE, 
                  password TEXT)''')
    conn.commit()
    conn.close()


def create_feedback_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS feedback 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  username TEXT,
                  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  feedback TEXT,
                  label TEXT)''')
    conn.commit()
    conn.close()

def create_contact_messages_table():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS contact_messages 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  full_name TEXT,
                  email TEXT, 
                  message TEXT)''')
    conn.commit()
    conn.close()

def save_feedback_to_db(username, feedback, label):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO feedback (username, feedback, label) VALUES (?, ?, ?)", (username, feedback, label))
    conn.commit()
    conn.close()

def insert_user(name, email, mobile, username, password):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    sql_query = "INSERT INTO users (name, email, mobile, username, password) VALUES (?, ?, ?, ?, ?)"
    params = (name, email, mobile, username, password)
    print("SQL Query:", sql_query)
    print("Parameters:", params)
    c.execute(sql_query, params)
    conn.commit()
    conn.close()


def get_user(username):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()
    return user

@app.route("/")
def homepage():
    return render_template('landing.html')

@app.route("/home")
def home():
    if 'username' in session and session['username'] == 'admin':
        return redirect(url_for('landing_admin'))
    
    else:
        return render_template('index.html')

@app.route("/landing")
def landing():
    return render_template('landing.html')


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form['name'] 
        email = request.form['email']
        mobile = request.form['mobile']
        username = request.form['username']
        password = request.form['password']
        
        if get_user(username):
            message = "User already exists!"
            return render_template('signup.html', message=message)
        insert_user(name, email, mobile, username, password)
        message = "Account successfully created"
        return render_template('signup.html', message=message)
    return render_template('signup.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        user = get_user(username)

        if user and user[5] == password:
            session['username'] = username
            # Check if the user is an admin
            if username == 'admin':
                return redirect(url_for('landing_admin'))
            else:
                return redirect(url_for('home'))
        return render_template('login.html', message="Invalid username or password!")
    return render_template('login.html')


@app.route("/logout", methods=["POST"])
def logout():
    session.pop('username', None)
    return redirect(url_for('landing'))

@app.route("/landing_admin")
def landing_admin():
    return render_template('landing_admin.html')


# @app.route("/contactus")
# def contactus():
#     return render_template('contactus.html')

@app.route("/contactus", methods=["GET", "POST"])
def contactus():
    if request.method == "POST":
        # Get form data
        full_name = request.form['full_name']
        email = request.form['email']
        message = request.form['message']
        
        # Save data to the database
        save_contact_message(full_name, email, message)

        subject = "Thank You for Contacting Feedbackify"
        body = f"Dear {full_name},\n\nThank you for reaching out to us. Your message has been received and we appreciate your interest in Feedbackify. Our team will review your inquiry and get back to you as soon as possible.\n\nBest Regards,\nThe Feedbackify Team"

        # try:
        #     send_email(subject, email, body)
        # except Exception as e:
        #     print(f"An error occurred: {e}")

        # Flash a success message
        flash("Your response has been submitted.", "success")
        
        # Optionally, you can redirect the user to a thank you page
        render_template('contactus.html')

    # If the request method is GET, simply render the contact us page
    return render_template('contactus.html')

def save_contact_message(full_name, email, message):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO contact_messages (full_name, email, message) VALUES (?, ?, ?)", (full_name, email, message))
    conn.commit()
    conn.close()

def save_contact_message(full_name, email, message):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO contact_messages (full_name, email, message) VALUES (?, ?, ?)", (full_name, email, message))
    conn.commit()
    conn.close()

    

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if 'username' not in session or session['username'] != 'admin':
        return redirect(url_for('login'))

    if request.method == "POST":
        # Handle user removal
        username_to_remove = request.form.get('username')
        # Call a function to remove the user from the database
        remove_user(username_to_remove)
        return redirect(url_for('admin'))

    # Fetch all users from the database
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT name, email, mobile, username FROM users")
    users = c.fetchall()
    conn.close()

    return render_template('admin.html', users=users)

def remove_user(username):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username=?", (username,))
    conn.commit()
    conn.close()

@app.route("/prediction")
def prediction():
    return render_template('prediction.html')


@app.route('/feedback')
def feedback():

    feedback_data = fetch_feedback()

    unique_labels = set(feedback[4] for feedback in feedback_data)

    return render_template('feedback.html', feedback_data=feedback_data, unique_labels=unique_labels)


def fetch_feedback():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM feedback order by timestamp desc")
    feedback_data = c.fetchall()
    conn.close()
    return feedback_data

# Define column names
COLUMN_NAMES = ['ID', 'User', 'Date', 'Feedback', 'Label']

@app.route('/export_excel')
def export_excel():
    # Fetch feedback data from the database
    feedback_data = fetch_feedback()

    # Create a BytesIO object to store the Excel file
    output = BytesIO()

    # Create a new Excel workbook and add a worksheet
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()

    # Write column names as headers
    for col, name in enumerate(COLUMN_NAMES):
        worksheet.write(0, col, name)

    # Write feedback data starting from the second row
    for row, feedback in enumerate(feedback_data, start=1):
        for col, value in enumerate(feedback):
            worksheet.write(row, col, value)

    # Close the workbook
    workbook.close()

    # Seek to the beginning of the BytesIO object
    output.seek(0)

    # Create a response with the BytesIO object as the file
    return Response(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={
        'Content-Disposition': 'attachment; filename=feedback_data.xlsx'
    })



# Load the saved Multinomial Naive Bayes model
loaded_model = load('model.joblib')

# Load the TF-IDF vectorizer
tfidf_vectorizer = load('tfidf_vectorizer.joblib')

# Define function to clean text
def clean_text(text):
    stop_words = set(stopwords.words('english'))
    ps = PorterStemmer()
    # Remove hash-tags, mentions, URLs, punctuations
    text = re.sub(r'@\S+|#\S+|http\S+|[^\w\s]', '', text)
    # Convert text to lowercase
    text = text.lower()
    # Tokenization and remove stopwords
    tokens = [ps.stem(token) for token in text.split() if token not in stop_words]
    return ' '.join(tokens)

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == "POST":
        text = request.form['text']
   
        # Clean the new text
        cleaned_text = clean_text(text)

        # Transform the cleaned text using TF-IDF vectorizer
        new_text_tfidf = tfidf_vectorizer.transform([cleaned_text])

        # Make a single prediction
        label = loaded_model.predict(new_text_tfidf)[0]

        # Save the feedback and label to the database
        save_feedback_to_db(session['username'], text, label)

        return render_template('prediction.html', x=label, y=text)

        # return redirect(url_for('prediction_result', label=label, feedback=text))

    return render_template('prediction.html')

def save_feedback_to_db(username, feedback, label):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO feedback (username, feedback, label) VALUES (?, ?, ?)", (username, feedback, label))
    conn.commit()
    conn.close()




if __name__ == "__main__":

    # Create the database if it doesn't exist
    if not os.path.exists(DATABASE):
        create_db()
        create_feedback_db()
    
    # Secret key for session management
    app.secret_key = 'supersecretkey'
    
    app.run(debug=True)
