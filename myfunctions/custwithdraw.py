#########################################################
# Created on 17th May 2025                              #
# By DAVID KAMANDE                                      #
# for PCEA CHAIRETE SACCO                               #
#########################################################
# SET UP THE ENVIRONMENT
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
import oracledb
oracledb.init_oracle_client(lib_dir="C:\\Program Files (x86)\\Oracle\\instantclient_19_11")
from oracledb import create_pool,InterfaceError
import psycopg2
import logging
logging.basicConfig(level=logging.DEBUG)

import re

from openpyxl import load_workbook


import os,shutil
import sys
import paramiko
from base64 import decodebytes
import zipfile





from flask_login import current_user, login_required
import io

from psycopg2.extras import RealDictCursor




#CREATE THE DATABASE CONNECTION
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='postgres',
            user='postgres',
            password='12345',
            port ='5432'
        )
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None




    
# Update Transaction Details
def queue_withdr_logic():
    form = custWDRForm()
    regex = re.compile(r'[A-Za-z0-9 _-]+')
    if form.validate_on_submit():
        if regex.match(form.cuniqueid.data):
            cust_uniqueid = form.cuniqueid.data
            cust_cclient = form.ccustomer.data            
            cust_bal = form.cbalance.data  
            cust_amt = form.camountw.data             
            cust_narr = form.cnarration.data 
            mod_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')           

            # Connect to the DB
            logging.debug("Connecting to database...")
            conn = get_db_connection()
            cursor = conn.cursor()
            cust_query = """
            SELECT  account_no from  portfolio WHERE account_no = %s
            """
            # Check if the customer ID exists
            cursor.execute(cust_query, (cust_uniqueid,))
            existing_trx = cursor.fetchone()
            
            if existing_trx:
                logging.debug("Transaction details found, proceeding with update...")  
                
                insert_query = """
                INSERT INTO withdrawals (account_no,tran_date,amount,comment)
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(insert_query, (cust_uniqueid,mod_date,cust_amt,cust_narr))

                # Initialize a list to hold rows for DataFrame
                rows_to_insert = []
                
                # Commit the transaction
                conn.commit()
             
                flash(f'Transaction for {cust_uniqueid} queued Successfully!', 'success')
            else:
                flash('Transaction not valid, update failed!', 'error')
            
            cursor.close()
            conn.close()
            return redirect(url_for('home'))
   
        else:
            flash('Update Unsuccessful. Please check the details provided', 'secondary')
    return render_template('queue_withdrawal.html', title='EXS', form=form)    
    


def generate_withdrawal_logic():
    cust_mgr = current_user.username  # Get current user
    current_date = datetime.today().date()  # Current date for withdrawal

    # Establish database connection
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)  # Use RealDictCursor for dictionary-like access

    # Query to select withdrawals where status is not 'Y' or is NULL
    cursor.execute("""
        SELECT account_no, amount, status FROM withdrawals WHERE status <> 'Y' OR status IS NULL;
    """)
    withdrawals = cursor.fetchall()

    # Process each withdrawal and update portfolio balance and withdrawal status
    for withdrawal in withdrawals:
        account_no = withdrawal['account_no']  
        amount = withdrawal['amount']

        # Update the portfolio balance (subtract the withdrawal amount)
        cursor.execute("""
            SELECT balance FROM portfolio WHERE account_no = %s;
        """, (account_no,))
        portfolio = cursor.fetchone()  

        if portfolio:
            # Assuming 'balance' is at index 0 in the tuple
            new_balance = float(portfolio['balance']) - float(amount)  # Access balance by index

            # Update the portfolio balance
            cursor.execute("""
                UPDATE portfolio SET balance = %s WHERE account_no = %s;
            """, (new_balance, account_no))

        # Update the withdrawal status to 'Y', and set the userid and withdrawal_date
        cursor.execute("""
            UPDATE withdrawals 
            SET status = 'Y', userid = %s, withdrawal_date = %s 
            WHERE account_no = %s AND (status <> 'Y' OR status IS NULL);
        """, (cust_mgr, current_date, account_no))

    # Commit the changes to the database
    conn.commit()

    # Query to generate the report
    query = """
    SELECT c.cust_name, a.account_no, a.amount, c.cust_bank, c.cust_acct, c.cust_branch
    FROM withdrawals a
    JOIN portfolio b USING(account_no)
    JOIN clients c USING(customer_id)
    WHERE a.withdrawal_date = CURRENT_DATE;
    """
    
    # Fetch the data for the report
    cursor.execute(query)
    data = cursor.fetchall()

    # Convert the result to a Pandas DataFrame
    df = pd.DataFrame(data)

    # Save the DataFrame to an in-memory Excel file
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Withdrawals_Report')

    output.seek(0)  # Rewind the buffer to the beginning

    # Generate filename with current date suffix
    filename = f"withdrawals_report_{current_date}.xlsx"

    # Close the cursor and connection
    cursor.close()
    conn.close()

    # Send the file as an attachment for download
    return send_file(output, download_name=filename, as_attachment=True)
    
    

def recon_purchases_logic():
    current_date = datetime.today().date()  # Current date for withdrawal
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)  # Use RealDictCursor for dictionary-like access

    # Query to generate the report
    query = """
    select cust_name as "CUSTOMER","CLIENT_ID","PSTD_DATE","VALUE_DATE"::date, "TRAN_ID", "TRAN_PARTICULAR","TRANSACTIONAMOUNT","UBACCTRANSCOUNTER",
     "PHONENO", "RECEIPT_STATUS" from htd_stmt a 
    left outer join portfolio b ON b.account_no = a."CLIENT_ID"
    left outer join clients c ON c.customer_id = b.customer_id
    WHERE "PSTD_DATE"::date > NOW() - INTERVAL '60 days'
    order by "UBACCTRANSCOUNTER";
    """
    
    # Fetch the data for the report
    cursor.execute(query)
    data = cursor.fetchall()

    # Convert the result to a Pandas DataFrame
    df = pd.DataFrame(data)

    # Save the DataFrame to an in-memory Excel file
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='7D_Purchase_Report')

    output.seek(0)  # Rewind the buffer to the beginning

    # Generate filename with current date suffix
    filename = f"7d_purchase_report_{current_date}.xlsx"

    # Close the cursor and connection
    cursor.close()
    conn.close()

    # Send the file as an attachment for download
    return send_file(output, download_name=filename, as_attachment=True) 
    
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

# Function to get customer data by unique ID (account_no)
def get_customer_by_uniqueid(cuniqueid):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT cust_name FROM clients
        JOIN portfolio USING(customer_id)
        WHERE account_no = %s;
    """
    cursor.execute(query, (cuniqueid,))
    result = cursor.fetchone()  # fetchone will return a tuple
    cursor.close()
    conn.close()
    if result:
        return result[0]  # Return the customer name
    return None

# Function to get balance by unique ID (account_no)
def get_balance_by_uniqueid(cuniqueid):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT balance FROM clients
        JOIN portfolio USING(customer_id)
        WHERE account_no = %s;
    """
    cursor.execute(query, (cuniqueid,))
    result = cursor.fetchone()  # fetchone will return a tuple
    cursor.close()
    conn.close()
    if result:
        return result[0]  # Return the balance
    return None


def get_with_details_logic():
    cuniqueid = request.form.get('cuniqueid')
    
    # Retrieve customer name and balance
    customer = get_customer_by_uniqueid(cuniqueid)
    balance = get_balance_by_uniqueid(cuniqueid)

    if customer and balance:
        return jsonify({
            'ccustomer': customer,
            'cbalance': balance
        })
    else:
        return jsonify({
            'error': 'No data found for the given unique ID'
        }), 404



