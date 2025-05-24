#########################################################
# Created  on 26th Nov 2024                             #
# By DAVID KAMANDE                                      #
# dkamande@co-opbank.co.ke                              #
# To Process Co-op Trust Investments Services	        #    
#                                                       #
#########################################################
# SET UP THE ENVIRONMENT
from flask import Flask, render_template, url_for, flash, redirect,request,jsonify,send_file, make_response
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix
from forms import SSCheckForm, StmRequestForm, ACCheckForm, CMSForm, ARFRequestForm, ARFCollectForm,CustDetailForm,EnrichForm,UpdateTRXForm,custWDRForm,populate_bank_choices,PageSelectionForm,amendCNTForm,editBNKForm,editKYCForm,RegistrationForm, LoginForm
#from myfunctions.custfile import enrich_cust_details_logic, capture_cust,get_db_connection,get_customer_name_logic,fetch_oracle,parameterize_SQL_in_statement,get_trx_details_logic,update_trx_details_logic
from myfunctions.custfile import enrich_cust_details_logic, capture_cust,get_db_connection,get_customer_name_logic,get_trx_details_logic,update_trx_details_logic
from myfunctions.welcome import MembershipLetterGenerator
from myfunctions.receipt import receipt_customer
from myfunctions.custwithdraw import  queue_withdr_logic,get_with_details_logic
from myfunctions.edit_cust import amend_cust_contacts_logic,get_amend_cust_contact_logic,edit_bnk_details_logic,get_edit_bnk_details_logic,get_edit_kyc_details_logic,edit_kyc_details_logic
from sqlalchemy import create_engine
from oikonomos.models import User, Post

from flask_login import login_user, current_user, logout_user, login_required



from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager 



from markupsafe import Markup,escape 
from jinjasql import JinjaSql
from Runpy import sqlparse
import cryptography as cy
from cryptography.fernet import Fernet
import pandas as pd
import oracledb
from oracledb import create_pool,InterfaceError
oracledb.init_oracle_client(lib_dir="C:\\Program Files (x86)\\Oracle\\instantclient_19_11")
import psycopg2
import logging
logging.basicConfig(level=logging.DEBUG)

import re


import os,shutil
import sys
import paramiko
from base64 import decodebytes
import zipfile

#REPORTS CONNECTION CONFIG
enc_paswd = str.encode('gAAAAABm48ggWyZaq319Yx-0SwjxiM4L1W7ghCdp2-y4FNVtw8TPvjgkfiPKSwEB0QQv6zr8WuP-Cpf00J0wKd2yXOqe-MCqtw1OqbciD7Y7jfvKUnBzLME=') #Encrypted Password
key = str.encode('p26wa9-pbWGHKuda8LnLs4hDbmhXMDFhOQYBOj84O1g=') #Encryption Key
fern_key=Fernet(key)
dec_paswd=fern_key.decrypt(enc_paswd)
decod_paswd=str(dec_paswd.decode("utf-8"))
dsn = oracledb.makedsn('copkdnas-c2-scan', 1528, service_name='BIUAT')
#pool= create_pool(user='COOP_STG', password=decod_paswd, dsn=dsn,min=1, max=5)

# Create Reusable Connection Pool
def get_connection():
    return pool.acquire()
    
    
    
    
    
    
app = Flask(__name__, static_folder='static')
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)
app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde280ba245'
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'


# List of allowed IPs
ALLOWED_IPS = {'127.0.0.1','192.168.100.63', '203.0.113.5'}  # Replace with your allowed IPs

@app.before_request
def limit_remote_addr():
    client_ip = request.remote_addr
    if client_ip not in ALLOWED_IPS:
        abort(403)  # Forbidden