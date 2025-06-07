#########################################################
# Created on 17th May 2025                              #
# By DAVID KAMANDE                                      #
# for PCEA CHAIRETE SACCO                               #
#########################################################
# SET UP THE ENVIRONMENT
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, render_template, url_for, flash, redirect,request,jsonify,send_file
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix
import socket
from myfunctions.welcome import MembershipLetterGenerator
from forms import  CMSForm, CustDetailForm,EnrichForm,UpdateTRXForm,custWDRForm,populate_bank_choices
from markupsafe import Markup,escape 
from jinjasql import JinjaSql
from Runpy import sqlparse
import cryptography as cy
from cryptography.fernet import Fernet
import pandas as pd
#import oracledb
#oracledb.init_oracle_client(lib_dir="C:\\Program Files (x86)\\Oracle\\instantclient_19_11")
#from oracledb import create_pool,InterfaceError
import psycopg2
import logging
logging.basicConfig(level=logging.DEBUG)

import re

from openpyxl import load_workbook


import os,shutil
import sys
#import paramiko
from base64 import decodebytes
import zipfile





from flask_login import current_user, login_required
import io

from psycopg2.extras import RealDictCursor

import urllib.parse as urlparse


#CREATE THE DATABASE CONNECTION

def get_db_connection():
    try:
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            raise ValueError("DATABASE_URL is not set in environment variables")

        # Parse the connection string (optional: psycopg2 can handle full URL directly)
        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
        print(f"Error connecting to Railway DB via DATABASE_URL: {e}")
        return None


 
    
def audit_report_logic():
    current_date = datetime.today().date()  # Current date for withdrawal
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)  # Use RealDictCursor for dictionary-like access

    # Query to generate the report
    query = """
    SELECT windows_user, ip_address, transaction_time,id, table_name,
    case when table_name = 'members' then update_audit.old_values ->> 'membership_number' 
    when table_name = 'transactions' then update_audit.old_values ->> 'trxid' 
    when table_name = 'related_party' then update_audit.old_values ->> 'partyid' end AS value_id,
    old_values.key AS key, old_values.value AS old_value,new_values.value AS new_value
    FROM  update_audit,
    LATERAL jsonb_each_text(old_values) AS old_values(key, value),
    LATERAL jsonb_each_text(new_values) AS new_values(key, value)
    WHERE old_values.key = new_values.key AND 
	((old_values.value <> new_values.value) or (old_values.value is null and  new_values.value is not null)) 
    and windows_user is not null and old_values.key not in('date_modified','modified_by') and transaction_time::date >= CURRENT_DATE - INTERVAL '7 days'
    order by transaction_time;
    """
    
    # Fetch the data for the report
    cursor.execute(query)
    data = cursor.fetchall()

    # Convert the result to a Pandas DataFrame
    df = pd.DataFrame(data)

    # Save the DataFrame to an in-memory Excel file
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='7D_Audit_Report')

    output.seek(0)  # Rewind the buffer to the beginning

    # Generate filename with current date suffix
    filename = f"7D_Audit_Report_{current_date}.xlsx"

    # Close the cursor and connection
    cursor.close()
    conn.close()

    # Send the file as an attachment for download
    return send_file(output, download_name=filename, as_attachment=True)  



