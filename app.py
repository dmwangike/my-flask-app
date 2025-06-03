#########################################################
# Created  on 17th May 2025                             #
# By DAVID KAMANDE                                      #
# dmwangike@yahoo.com	                                #
# for PCEA CHAIRETE SACCO    			        #    
#                                                       #
#########################################################
# SET UP THE ENVIRONMENT
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, render_template, url_for, flash, redirect,request,jsonify,send_file, make_response,abort, current_app 
from datetime import datetime, timedelta
from werkzeug.middleware.proxy_fix import ProxyFix
from forms import  CMSForm,ReportsForm, CustDetailForm,EnrichForm,UpdateTRXForm,custWDRForm,populate_bank_choices,PageSelectionForm,amendCNTForm,editBNKForm,editKYCForm,HolsForm,cusdKYCForm

from myfunctions.custfile import enrich_cust_details_logic, capture_cust,get_db_connection,get_customer_name_logic,get_trx_details_logic,update_trx_details_logic

from myfunctions.receipt import receipt_customer
from myfunctions.custwithdraw import  queue_withdr_logic,get_with_details_logic,generate_withdrawal_logic,recon_purchases_logic,audit_report_logic
from myfunctions.edit_cust import amend_cust_contacts_logic,get_amend_cust_contact_logic,edit_bnk_details_logic,get_edit_bnk_details_logic,get_edit_kyc_details_logic,edit_kyc_details_logic,add_related_party_logic,get_edit_related_party_logic,edit_related_party_logic,fetch_member_logic,assign_beneficiary_allocations_logic,fetch_guarantor_name_logic,fetch_member_balance_logic,loan_form_logic,get_cust_details_logic
from sqlalchemy import create_engine
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField,PasswordField,validators,FloatField,DateField, SelectField
from wtforms.validators import DataRequired, Length, EqualTo ,Email, ValidationError,InputRequired
from psycopg2.extras import RealDictCursor
from flask_login import login_user, current_user, logout_user, login_required,UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager 
from flask_mail import Mail,Message 
import jwt 
import smtplib  
from markupsafe import Markup,escape 
from jinjasql import JinjaSql

import cryptography as cy
from cryptography.fernet import Fernet
import pandas as pd
#import oracledb
#from oracledb import create_pool,InterfaceError

#oracledb.init_oracle_client(lib_dir="C:\\Program Files (x86)\\Oracle\\instantclient_19_11")
import psycopg2
import logging
logging.basicConfig(level=logging.DEBUG)
import re
import os,shutil
import sys
#import paramiko
from base64 import decodebytes
import zipfile


from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch


from myfunctions.localpkg import generate_statements_logic,create_date_folder,create_bank_statement_revised

from extensions import mail    
    
    
    
app = Flask(__name__, static_folder='static')
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)
app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde280ba245'
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'dangawalla@gmail.com' 
app.config['MAIL_PASSWORD'] = 'ghno sctr qbcl mljd'
app.config['MAIL_DEFAULT_SENDER'] = 'noreply@demo.com'
#mail = Mail(app)

# Initialize mail with app
mail.init_app(app)

# Import after defining mail
from myfunctions.welcome import MembershipLetterGenerator


# List of allowed IPs
#ALLOWED_IPS = {'127.0.0.1','192.168.100.243', '203.0.113.5'}  # Replace with your allowed IPs

#@app.before_request
#def limit_remote_addr():
#    client_ip = request.remote_addr
#    if client_ip not in ALLOWED_IPS:
#        abort(403)  # Forbidden

posts = [
    {
        'author': 'OIKONOMOS',
        'title': 'WELCOME TO PCEA CHAIRETE SACCO',
        'content': 'Service Portal',
        'date_posted': datetime.now().strftime('%Y-%m-%d')
    },
    {
          
            'content': 'Welcome to PCEA CHAIRETE SACCO.  We grow value',
           
    }
]

post1 = [
    {
        'author': 'OIKONOMOS',
        'title': 'WELCOME TO PCEA CHAIRETE SACCO',
        'content': 'Service Portal',
        'date_posted': datetime.now().strftime('%Y-%m-%d')
    },
    {
          
            'content': 'Customer Relationship Management',
           
    }
]
post2 = [
    {
        'author': 'OIKONOMOS',
        'title': 'WELCOME TO PCEA CHAIRETE SACCO',
        'content': 'Service Portal',
        'date_posted': datetime.now().strftime('%Y-%m-%d')
    },
    {
          
            'content': 'Members Payment Processing',
           
    }
]
post3 = [
    {
        'author': 'OIKONOMOS',
        'title': 'WELCOME TO PCEA CHAIRETE SACCO',
        'content': 'Service Portal',
        'date_posted': datetime.now().strftime('%Y-%m-%d')
    },
    {
          
            'content': 'Members Loan Processing',
           
    }
]
  
post4 = [
    {
        'author': 'OIKONOMOS',
        'title': 'WELCOME TO PCEA CHAIRETE SACCO',
        'content': 'Service Portal',
        'date_posted': datetime.now().strftime('%Y-%m-%d')
    },
    {
          
            'content': 'General Reports',
           
    }
]

#  DEFINE The FILE TO LOG EVENTS
LOG_FILE = '/tmp/DATA/execution_log.txt'

# Base path to save PDFs
BASE_PDF_OUTPUT_DIR = '/tmp/DATA'

# FUNCTION TO LOG EVENTS
def log_event(message):
    """Append a log message to the log file."""
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
        


 

@app.route("/")
@app.route("/home")
@login_required 
def home():
    return render_template('home.html', posts=posts)




@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        created_date = datetime.utcnow()  # Get the current UTC time
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO users (username, email, password, created_date)
                VALUES (%s, %s, %s, %s)
                """,
                (form.username.data.lower(), form.email.data.lower(), hashed_password, created_date)
            )
            connection.commit()
            cursor.close()
            connection.close()
            flash('Your account has been created! You are now able to log in', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('An error occurred while creating your account. Please try again.', 'danger')
            print(f"Error: {e}")  # For debugging, log the error to the console
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        try:
            # Establish a connection to the database
            connection = get_db_connection()
            cursor = connection.cursor()
            logging.debug("Acquired DB connections...")
            # Query the database for the user using the username
            cursor.execute("SELECT id, username,email, password FROM users WHERE username = %s", (form.username.data.lower(),))
            user_data = cursor.fetchone()
            cursor.close()
            connection.close()
            logging.debug("User data received...")
            # Check if user exists and verify the password
            if user_data:
                user_id, username,email, hashed_password = user_data
                if bcrypt.check_password_hash(hashed_password, form.password.data):
                    user = User(user_id, username,email,hashed_password)  
                    login_user(user, remember=form.remember.data)
                    next_page = request.args.get('next')
                    logging.debug("Login Successful...")
                    return redirect(next_page) if next_page else redirect(url_for('home'))
        except Exception as e:
            flash('An error occurred during login. Please try again.', 'danger')
            print(f"Error: {e}")  # Debugging

        flash('Login Unsuccessful. Please check username and password.', 'danger')
    return render_template('login.html', title='Login', form=form)




@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/account")
@login_required
def account():
    return render_template('account.html', title='Account')



# Initialize Flask-Mail
mail = Mail()

def send_reset_email(user):
    token = user.get_reset_token()
    user = user.verify_reset_token(token)
    logging.debug(f"Customer ID is: {user.id}")  
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Query to get the customer email
    query = "SELECT email FROM USERS WHERE  id = %s"
    cursor.execute(query, (user.id,))
    result = cursor.fetchone()
    cust_email = result[0]
    logging.debug(f"Sending email to: {cust_email}") 
    # Create the message
    msg = Message('Password Reset Request',
                  sender='noreply@demo.com',
                  recipients= [cust_email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}

If you did not make this request, simply ignore this email and no changes will be made.
'''

    try:
        # Send the email
        mail.send(msg)
    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP Authentication Error: {e}")
        # Handle authentication error (e.g., wrong password or blocked by Google)
        raise
    except Exception as e:
        print(f"Error sending email: {e}")
        raise




   
    
    
@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = RequestResetForm()
    
    if form.validate_on_submit():

        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute('SELECT id, username, email, password FROM users WHERE email = %s', (form.email.data.lower(),))
        user_data = cursor.fetchone()
        cursor.close()
        connection.close()

        if user_data:
            user = User(*user_data)  # Create a User object from the fetched data
            send_reset_email(user)
            flash('An email has been sent with instructions to reset your password.', 'info')
        else:
            flash('No account found with that email address.', 'warning')
            return redirect(url_for('reset_request'))
        
        return redirect(url_for('login'))

    return render_template('reset_request.html', title='Reset Password', form=form)
   


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)

    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        connection = get_db_connection()
        cursor = connection.cursor()
        query = """
        UPDATE users SET password = %s WHERE id = %s
        """
        cursor.execute(query, (hashed_password,user.id))
        connection.commit()
        cursor.close()
        connection.close()
        flash(f'Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)

    



 
    
@app.after_request
def add_cache_control_headers(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response   




@app.route("/define_holidays", methods=['GET', 'POST'])
def define_holidays():
    form = HolsForm()
    regex = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    
    if request.method == 'POST' and form.validate_on_submit():
        # Convert the date object to a string for regex matching
        stdate = form.cstartd.data.strftime('%Y-%m-%d') if form.cstartd.data else ""
        if regex.match(stdate):
            endate = form.cendd.data.strftime('%Y-%m-%d') if form.cendd.data else stdate
            holiday = form.cname.data
            mod_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cust_mgr = current_user.username

            # Connect to the DB            
            logging.debug("Connecting to database...")            
            conn = get_db_connection()            
            cursor = conn.cursor()            

            # SQL INSERT statement to insert customer details            
            insert_query = """            
            INSERT INTO holidays (start_date, end_date, holiday, created_by, created_on)            
            VALUES ( %s, %s, %s, %s, %s)            
            """            
            cursor.execute(insert_query, (stdate, endate, holiday, cust_mgr, mod_date))            

            # Commit the transaction            
            conn.commit()            
            logging.debug("Data inserted into the holiday table...")            

            # Close the connection            
            cursor.close()            
            conn.close()
            flash('Holiday defined successfully!', 'success')
            return redirect(url_for('home'))
        #else:
            #flash('Invalid date format for START_DATE. Please enter a valid date.', 'danger')
    elif request.method == 'POST':
        flash('Holiday not defined, please check your input.', 'secondary')

    return render_template('define_holidays.html', title='Holidays', form=form)


@app.route("/stmt", methods=['GET', 'POST'])
def stmt():
    form = ACCheckForm()
    return render_template('stmt.html', title='Stmt',posts=post2,form=form)
    
@app.route("/reports", methods=['GET', 'POST'])
def reports():
    form = ReportsForm()
    return render_template('reports.html', title='Stmt',posts=post4,form=form)


@app.route("/deposits", methods=['GET', 'POST'])
@login_required 
def deposits():
    form = CMSForm()
    return render_template('deposits.html', title='DEP', posts=post2,form=form )
    
    
@app.route("/loans", methods=['GET', 'POST'])
@login_required 
def loans():
    form = CMSForm()
    return render_template('loans.html', title='LON', posts=post3,form=form )
    
 

@app.route('/fetch_guarantor_name', methods=['GET', 'POST'])
@login_required 
def fetch_guarantor_name():
    return fetch_guarantor_name_logic() 
    
    


@app.route('/fetch_member_balance', methods=['GET', 'POST'])
@login_required 
def fetch_member_balance():
    return fetch_member_balance_logic()
   
    
@app.route('/get_amend_cust_contact', methods=['GET', 'POST'])
@login_required 
def get_amend_cust_contact():
    return get_amend_cust_contact_logic() 
    
@app.route('/get_edit_bnk_details', methods=['GET', 'POST'])
@login_required 
def get_edit_bnk_details():
    return get_edit_bnk_details_logic() 
        
@app.route('/get_edit_kyc_details', methods=['GET', 'POST'])
@login_required 
def get_edit_kyc_details():
    return get_edit_kyc_details_logic() 
    
@app.route('/get_cust_details', methods=['GET', 'POST'])
@login_required 
def get_cust_details():
    return get_cust_details_logic() 


    
    
@app.route('/get_edit_related_party', methods=['GET', 'POST'])
@login_required 
def get_edit_related_party():
    return get_edit_related_party_logic()    
    

@app.route('/add_related_party', methods=['GET', 'POST'])
@login_required 
def add_related_party():
    return add_related_party_logic()    
  
    
@app.route('/generate_statements', methods=['GET', 'POST'])
@login_required
def generate_statements():
    generate_statements_logic()  
    return redirect(url_for('home'))  
            

@app.route('/enquire_cust_details', methods=['GET', 'POST'])
def enquire_cust_details():
    form = cusdKYCForm()
    return render_template('enquire_cust_details.html', form=form)

    
    
@app.route("/execute_sql", methods=['GET','POST'])
@login_required 
def  execute_sql():
    # Connect to the database
    conn = get_db_connection()
    query = """
    with new_clients as (
    select customer_id, cust_name, cust_acct,datejoined, identification,account_no,cust_bank,
    ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY account_no desc) AS rwn from clients join 
    portfolio using(customer_id)where datejoined = CURRENT_DATE)
    SELECT * from new_clients where rwn = 1
               """
    
    # Read data into a DataFrame
    df = pd.read_sql(query, conn)
    conn.close()
    conditions = df['cust_acct'].tolist()
    df_orc = fetch_oracle(conditions)
    check_df = pd.merge(df, df_orc, how='left', left_on='cust_acct', right_on='BANK_ACCT')


    
    # Create an Excel file on disk
    today = datetime.today().strftime('%Y-%m-%d')
    filename = f"E:\\oikonomos\\DATA\\acct_open_{today}.xlsx" 
    check_df.to_excel(filename, index=False, sheet_name='Data')

    flash('Extract successful. Please check location', 'success')
    return render_template('execute_sql.html', title='CUS', posts=post1)
    

    
@app.route("/members", methods=['GET', 'POST'])
@login_required 
def members():
    form = CMSForm()
    return render_template('members.html', title='MEM', posts=post1,form=form )
    
    
    
@app.route("/capture_member_details", methods=['GET', 'POST'])
@login_required 
def capture_member_details():

    return capture_cust()
@app.route('/enrich_member_details', methods=['GET', 'POST'])
@login_required 
def enrich_member_details():
    return enrich_cust_details_logic()
   
   
@app.route("/edit_member", methods=["GET", "POST"])
@login_required 
def edit_member():
    form = PageSelectionForm()
    if form.validate_on_submit():
        # Redirect to the selected page
        return redirect(url_for(form.page_selection.data))
    return render_template("edit_member.html", form=form)

# Routes for pages referenced in the dropdown
@app.route("/amend_cust_contacts", methods=['GET', 'POST'])
@login_required 
def amend_cust_contacts():
    return amend_cust_contacts_logic()

@app.route("/edit_bnk_details", methods=['GET', 'POST'])
@login_required 
def edit_bnk_details():
    return edit_bnk_details_logic()

@app.route("/edit_kyc_details", methods=['GET', 'POST'])
@login_required 
def edit_kyc_details():
    return edit_kyc_details_logic()   
    


@app.route("/edit_related_party", methods=['GET', 'POST'])
@login_required 
def edit_related_party():
    return edit_related_party_logic() 


#Fetch Beneficiary details
@app.route("/fetch_member", methods=["POST"])
@login_required 
def fetch_member():
    return fetch_member_logic()
    
@app.route("/assign_beneficiary_allocations", methods=['GET','POST'])
@login_required 
def assign_beneficiary_allocations():
    return assign_beneficiary_allocations_logic()    
    

    
    
    
@app.route('/get_customer_name', methods=['POST'])
@login_required 
def get_customer_name():
    return get_customer_name_logic()
    
@app.route('/spool_receipt', methods=['GET','POST'])
@login_required 
def spool_receipt():
    return receipt_customer()
    
@app.route('/get_trx_details', methods=['POST'])
@login_required 
def get_trx_details():
    return get_trx_details_logic()

@app.route('/update_trx_details', methods=['GET', 'POST'])
@login_required 
def update_trx_details():
    return update_trx_details_logic() 

@app.route('/queue_withdr', methods=['GET', 'POST'])
@login_required 
def queue_withdr():
    return queue_withdr_logic() 

@app.route('/get_with_details', methods=['GET', 'POST'])
@login_required 
def get_with_details():
    return get_with_details_logic() 
    
    


@app.route('/loan_form', methods=['GET', 'POST'])
@login_required
def loan_form():
    return loan_form_logic()

    
@app.route('/generate_withdrawal', methods=['GET', 'POST'])
@login_required
def generate_withdrawal():
    return generate_withdrawal_logic()

@app.route('/recon_purchases', methods=['GET', 'POST'])
@login_required
def recon_purchases():
    return recon_purchases_logic()
    
    
@app.route('/audit_report', methods=['GET', 'POST'])
@login_required
def audit_report():
    return audit_report_logic()
    


    

@app.route("/cust_address", methods=['GET', 'POST'])
def cust_address():
    try:
        # SQL script to execute
        sql_script = """
        SELECT customer_id AS "ID", TRIM(name) AS "CUSTOMER", TRIM(address) AS "MAILING ADDRESS" 
        FROM customers
        """  
        
        # Set up the spool statement
        statement_name = 'Customer_Address'    
        var = sqlparse.Spool_statement(statement_name)
        
        # Connect to the database
        logging.debug("Connecting to database...")
        with get_db_connection() as conn:  # Use a context manager to ensure the connection is closed
            logging.debug("Executing SQL script...")
            df = pd.read_sql(sql_script, conn)
            df.to_excel(var, sheet_name='CUST_ADDRESS', index=False)
        
        flash('Check your output in spool location after a few minutes!', 'success')
        logging.debug("Execution successful, redirecting to home...")
        return render_template('home.html', posts=posts)

        
    except Exception as err:
        logging.error(f'An error occurred: {err}')
        flash(f'An error occurred: {err}', 'error')
        logging.debug("Redirecting to home after error...")
        return render_template('home.html', posts=posts)



@login_manager.user_loader
def load_user(user_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('SELECT id, username,email, password FROM users WHERE id = %s', (user_id,))
    user_data = cursor.fetchone()
    cursor.close()
    connection.close()
    
    if user_data:
        return User(*user_data) 
    return None


class User(UserMixin):
    def __init__(self, id, username, password,email):
        self.id = id
        self.username = username
        self.password = password
        self.email = email

    def get_reset_token(self, expires_sec=1800):
        expiration = datetime.utcnow() + timedelta(seconds=expires_sec)
        
        token = jwt.encode(
            {'user_id': self.id, 'exp': expiration},
            app.config['SECRET_KEY'],
            algorithm='HS256' 
        )
        return token

    @staticmethod
    def verify_reset_token(token):
        try:
            decoded_token = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = decoded_token['user_id']
        except jwt.ExpiredSignatureError:
            return None  # Token expired
        except jwt.InvalidTokenError:
            return None  # Invalid token

        return User.get_by_id(user_id)  

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

    @staticmethod
    def get_by_id(id):
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute('SELECT id, username, email,password FROM users WHERE id = %s', (id,))
        user_data = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if user_data:
            return User(*user_data)
        return None

    @staticmethod
    def get_by_username(username):
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user_data = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if user_data:
            return User(*user_data)
        return None

    @staticmethod
    def get_by_email(email):
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user_data = cursor.fetchone()
        cursor.close()
        connection.close()

        if user_data:
            return User(*user_data)
        return None

    @staticmethod
    def create(username, email, image_file, password):
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            'INSERT INTO users (username, email, image_file, password) VALUES (%s, %s, %s, %s) RETURNING id',
            (username, email, image_file, password)
        )
        user_id = cursor.fetchone()[0]
        connection.commit()
        cursor.close()
        connection.close()
        
        return User(user_id, username, email, image_file, password)
        

class RegistrationForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT 1 FROM users WHERE username = %s"
        cursor.execute(query, (username.data,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor = conn.cursor()
        query = "SELECT 1 FROM users WHERE email = %s"
        cursor.execute(query, (email.data,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')
        
class RequestResetForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

    def validate_email(self, email):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor = conn.cursor()
        query = "SELECT 1 FROM users WHERE email = %s"
        cursor.execute(query, (email.data.lower(),))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user is None:

            raise ValidationError('There is no account with that email. You must register first.')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')






if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4028,debug=True)
