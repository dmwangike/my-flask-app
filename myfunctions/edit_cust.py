#########################################################
# Created on 17th May 2025                              #
# By DAVID KAMANDE                                      #
# dmwangike@yahoo.com    			        #
# for PCEA CHAIRETE SACCO				#
#########################################################
# SET UP THE ENVIRONMENT
from dotenv import load_dotenv
load_dotenv()
from flask_login import current_user, login_required
from flask import Flask, render_template, url_for, flash, redirect,request,jsonify,send_file
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix
import socket
from myfunctions.welcome import MembershipLetterGenerator
from forms import  CMSForm, CustDetailForm,EnrichForm,UpdateTRXForm,custWDRForm,populate_bank_choices,amendCNTForm,editBNKForm,editKYCForm,addRTDForm,editRTDForm,BeneficiaryForm,LoanForm,cusdKYCForm
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
from datetime import datetime, timedelta
import calendar

import re

from openpyxl import load_workbook
from decimal import Decimal


import os,shutil
import sys
#import paramiko
from base64 import decodebytes
import zipfile


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



    
# Update Customer Contacts
def amend_cust_contacts_logic():
    form = amendCNTForm()
    regex = re.compile(r'[A-Za-z0-9 _-]+')
    if form.validate_on_submit():
        if regex.match(form.cmemberid.data):
            cust_uniqueid = form.cmemberid.data
            cust_cclient = form.cname.data            
            cust_no = form.ccustno.data  
            cust_phone = form.cphone.data             
            cust_email = form.cemail.data.lower() 
            cust_address = form.caddress.data.upper()             
            cust_zip = form.czip.data.upper()
            cust_city = form.ccity.data.upper()             
            mod_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')           
            cust_mgr = current_user.username
            client_ip = request.remote_addr
            # Connect to the DB
            logging.debug("Connecting to database...")
            conn = get_db_connection()
            cursor = conn.cursor()
            cust_query = """
            SELECT  membership_number from  MEMBERS WHERE membership_number  = %s
            """
            # Check if the customer ID exists
            cursor.execute(cust_query, (cust_uniqueid,))
            existing_trx = cursor.fetchone()
            
            if existing_trx:
                logging.debug("Customer details found, proceeding with update...") 
                
                # SQL UPDATE statement
                update_query = """
                UPDATE MEMBERS
                SET pref_phone = %s, pref_email = %s, post_address = %s, post_code = %s,
                    city = %s,  date_modified = %s, modified_by = %s
                WHERE membership_number  = %s
                """
                cursor.execute(f"SET myapp.cust_mgr = '{cust_mgr}';") 
                cursor.execute(f"SET myapp.client_ip = '{client_ip}';")
                # Execute the update statement
                cursor.execute(update_query, (cust_phone, cust_email, cust_address, cust_zip, cust_city, mod_date,cust_mgr,cust_no ))
                
                # Commit the transaction
                conn.commit()                
                
                
               
             
                flash(f'Customer contacts for {cust_uniqueid} updated Successfully!', 'success')
            else:
                flash('Update failed!', 'error')
            
            cursor.close()
            conn.close()
            return redirect(url_for('home'))
   
        else:
            flash('Update Unsuccessful. Please check the details provided', 'secondary')
    return render_template('amend_cust_contacts.html', title='CNT', form=form)    
    
    
    
 
    
 

# Function to get customer contact data
def get_amend_cust_contact_logic():
    cmemberid = request.form.get('cmemberid')
    
    # Validate input
    if not cmemberid or not cmemberid.isalnum():
        return jsonify({'error': 'Invalid unique ID provided'}), 400
    
    try:
        # Database connection and query execution
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                    select cust_name,membership_number, pref_phone, pref_email, post_address, post_code, city
                    FROM MEMBERS 
                    WHERE membership_number = %s;
                """
                cursor.execute(query, (cmemberid,))
                result = cursor.fetchone()
        
        # Handle results
        if result:
            return jsonify({
                'cname': result[0],
                'ccustno': result[1],
                'cphone': result[2],
                'cemail': result[3],
                'caddress': result[4],
                'czip': result[5],
                'ccity': result[6] 
            })
        else:
            return jsonify({'error': 'No data found for the given unique ID'}), 404
    
    except Exception as e:
        # Log the exception (not shown here) and return a server error response
        return jsonify({'error': 'An error occurred while processing your request'}), 500
        






# Function to get related party details
def get_edit_related_party_logic():
    r_id = request.form.get('r_id')
    
    # Validate input
    if not r_id or not r_id.isalnum():
        return jsonify({'error': 'Invalid unique ID provided'}), 400
    
    try:
        # Database connection and query execution
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                select partyid,membership_number,cust_name, party_name, party_phone, party_email,party_role,lower(party_status) as party_status 
                from related_party a join MEMBERS b USING(membership_number)
                WHERE partyid = %s;
                """
                cursor.execute(query, (r_id,))
                result = cursor.fetchone()
        
        # Handle results
        if result:
            return jsonify({
                'r_id': result[0],
                'cmemberid': result[1],
                'cname': result[2],
                'rname': result[3],
                'rphone': result[4],
                'remail': result[5],
                'rrole': result[6],
                'rstatus': result[7]               
            })
        else:
            return jsonify({'error': 'No data found for the given unique ID'}), 404
    
    except Exception as e:
        # Log the exception (not shown here) and return a server error response
        return jsonify({'error': 'An error occurred while processing your request'}), 500
                








        
        
# Function to get customer data For Bank Details Update
def get_edit_bnk_details_logic():
    cmemberid = request.form.get('cmemberid')
    
    # Validate input
    if not cmemberid or not cmemberid.isalnum():
        return jsonify({'error': 'Invalid unique ID provided'}), 400
    
    try:
        # Database connection and query execution
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                    SELECT cust_name, membership_number
                    FROM MEMBERS WHERE  membership_number = %s;
                """
                cursor.execute(query, (cmemberid,))
                result = cursor.fetchone()
        
        # Handle results
        if result:
            return jsonify({
                'cname': result[0],
                'ccustno': result[1]
            })
        else:
            return jsonify({'error': 'No data found for the given unique ID'}), 404
    
    except Exception as e:
        # Log the exception (not shown here) and return a server error response
        return jsonify({'error': 'An error occurred while processing your request'}), 500
        
# Function to get customer KYC data
def get_edit_kyc_details_logic():
    cmemberid = request.form.get('cmemberid')
    
    # Validate input
    if not cmemberid or not cmemberid.isalnum():
        return jsonify({'error': 'Invalid unique ID provided'}), 400
    
    try:
        # Database connection and query execution
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                    select cust_name, membership_number,lower(tax_exempt) as tax_exempt,lower(membership_status) as membership_status
                    FROM MEMBERS 
                    WHERE membership_number = %s;
                """
                cursor.execute(query, (cmemberid,))
                result = cursor.fetchone()
        
        # Handle results
        if result:
            return jsonify({
                'cname': result[0],
                'ccustno': result[1],
                'ctax': result[2],
                'cstatus': result[3],

            })
        else:
            return jsonify({'error': 'No data found for the given unique ID'}), 404
    
    except Exception as e:
        # Log the exception (not shown here) and return a server error response
        return jsonify({'error': 'An error occurred while processing your request'}), 500        
        
# Function fill cust query
def get_cust_details_logic():
    cmemberid = request.form.get('cmemberid')
    
    # Validate input
    if not cmemberid or not cmemberid.isalnum():
        return jsonify({'error': 'Invalid unique ID provided'}), 400
    
    try:
        # Database connection and query execution
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                    SELECT cust_name, identification, pref_phone,pref_email,congregation 
                    from MEMBERS
                    WHERE membership_number = %s;
                """
                cursor.execute(query, (cmemberid,))
                result = cursor.fetchone()
        
        # Handle results
        if result:
            return jsonify({
                'cname': result[0],
                'ccustno': result[1],
                'cphone': result[2],
                'cemail': result[3],
                'ccongr': result[4],
            })
        else:
            return jsonify({'error': 'No data found for the given unique ID'}), 404
    
    except Exception as e:
        # Log the exception (not shown here) and return a server error response
        return jsonify({'error': 'An error occurred while processing your request'}), 500        
                


# Update Customer Bank Details
def edit_bnk_details_logic():
    form = editBNKForm()
    # Populate the bank choices from bank.txt file
    populate_bank_choices(form)
    regex = re.compile(r'[A-Za-z0-9 _-]+')
    if form.validate_on_submit():
        if regex.match(form.cmemberid.data):
            cust_uniqueid = form.cmemberid.data
            cust_cclient = form.cname.data            
            cust_no = form.ccustno.data  
            cust_bank = form.cbank.data             
            cust_acct = form.cacct.data.upper() 
            cust_branch = form.cbranch.data.title()             
          
            mod_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')           
            cust_mgr = current_user.username
            client_ip = request.remote_addr
            # Connect to the DB
            logging.debug("Connecting to database...")
            conn = get_db_connection()
            cursor = conn.cursor()
            cust_query = """
            SELECT  membership_number from  MEMBERS WHERE membership_number = %s
            """
            # Check if the customer ID exists
            cursor.execute(cust_query, (cust_uniqueid,))
            existing_trx = cursor.fetchone()
            
            if existing_trx:
                logging.debug("Customer details found, proceeding with update...") 
                
                # SQL UPDATE statement
                update_query = """
                UPDATE MEMBERS
                SET cust_bank = %s, cust_acct = %s, cust_branch = %s, date_modified = %s, modified_by = %s
                WHERE membership_number = %s
                """
                cursor.execute(f"SET myapp.client_ip = '{client_ip}';")
                cursor.execute(f"SET myapp.cust_mgr = '{cust_mgr}';")                
                # Execute the update statement
                cursor.execute(update_query, (cust_bank, cust_acct, cust_branch, mod_date,cust_mgr,cust_no ))
                
                # Commit the transaction
                conn.commit()                
                
                
               
             
                flash(f'Customer bank details for {cust_uniqueid} updated Successfully!', 'success')
            else:
                flash('Update failed!', 'error')
            
            cursor.close()
            conn.close()
            return redirect(url_for('home'))
   
        else:
            flash('Update Unsuccessful. Please check the details provided', 'secondary')
    return render_template('edit_bnk_details.html', title='ECBD', form=form)  
    
    
    
    
    
# Update Customer KYC Details
def edit_kyc_details_logic():
    form = editKYCForm()
    regex = re.compile(r'[A-Za-z0-9 _-]+')
    if form.validate_on_submit():
        if regex.match(form.cmemberid.data):
            cust_uniqueid = form.cmemberid.data
            cust_cclient = form.cname.data            
            cust_no = form.ccustno.data  
            cust_tax = form.ctax.data             
            cust_status = form.cstatus.data 
    
            mod_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')           
            cust_mgr = current_user.username
            client_ip = request.remote_addr
            # Connect to the DB
            logging.debug("Connecting to database...")
            conn = get_db_connection()
            cursor = conn.cursor()
            cust_query = """
            SELECT  membership_number from  MEMBERS WHERE membership_number = %s
            """
            # Check if the customer ID exists
            cursor.execute(cust_query, (cust_uniqueid,))
            existing_trx = cursor.fetchone()
            
            if existing_trx:
                logging.debug("Customer details found, proceeding with update...") 
                
                # SQL UPDATE statement
                update_query = """
                UPDATE MEMBERS
                SET tax_exempt = %s, membership_status = %s, date_modified = %s, modified_by = %s
                WHERE membership_number = %s
                """
                cursor.execute(f"SET myapp.client_ip = '{client_ip}';")
                cursor.execute(f"SET myapp.cust_mgr = '{cust_mgr}';")                
                # Execute the update statement
                cursor.execute(update_query, (cust_tax, cust_status, mod_date,cust_mgr,cust_no ))
                
                # Commit the transaction
                conn.commit()                
                
                
               
             
                flash(f'Member KYC details for {cust_uniqueid} updated Successfully!', 'success')
            else:
                flash('Update failed!', 'error')
            
            cursor.close()
            conn.close()
            return redirect(url_for('home'))
   
        else:
            flash('Update Unsuccessful. Please check the details provided', 'secondary')
    return render_template('edit_kyc_details.html', title='EKYC', form=form)    
    
# Add Related Party
def add_related_party_logic():
    form = addRTDForm()
    regex = re.compile(r'[A-Za-z0-9 _-]+')
    if form.validate_on_submit():
        if regex.match(form.cmemberid.data):
            cust_uniqueid = form.cmemberid.data
            cust_cclient = form.cname.data            
            rel_name = form.rname.data.title()
            rel_id = form.ridentification.data.upper()
            rel_phone = form.rphone.data             
            rel_email = form.remail.data.lower() 
            rel_role = form.rrole.data.upper()             
            rel_status = 'Active'
            
            mod_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')           
            cust_mgr = current_user.username
            client_ip = request.remote_addr
            # Connect to the DB
            logging.debug("Connecting to database...")
            conn = get_db_connection()
            cursor = conn.cursor()
            cust_query = """
            SELECT  membership_number from  MEMBERS WHERE membership_number  = %s
            """
            # Check if the customer ID exists
            cursor.execute(cust_query, (cust_uniqueid,))
            existing_trx = cursor.fetchone()
            
            if existing_trx:
                logging.debug("Customer details found, proceeding with update...") 
                # Check for duplicate party
                duplicate_check_query = """
                SELECT 1 FROM related_party
                WHERE party_uniqueid = %s AND membership_number = %s 
                LIMIT 1
                """
                cursor.execute(duplicate_check_query, (cust_uniqueid, rel_id))
                duplicate = cursor.fetchone()
            
                if duplicate:
                    flash('Duplicate Party detected. This Party already exists.', 'warning')
                else:
                    # SQL INSERT statement
                    insert_query = """
                    INSERT INTO related_party (membership_number, party_name,party_uniqueid,  party_phone, party_email,party_role,party_status,created_by)
                    VALUES (%s, %s, %s, %s, %s, %s,%s, %s)
                    """
                    cursor.execute(f"SET myapp.cust_mgr = '{cust_mgr}';") 
                    cursor.execute(f"SET myapp.client_ip = '{client_ip}';")
                    cursor.execute(insert_query, (cust_uniqueid, rel_name, rel_id,rel_phone, rel_email, rel_role,rel_status,cust_mgr))                
                    # Commit the transaction
                    conn.commit()             
                          
               
             
                    flash(f'Party added to {cust_uniqueid} Successfully!', 'success')
            else:
                flash('Update failed!', 'error')
            
            cursor.close()
            conn.close()
            return redirect(url_for('home'))
   
        else:
            flash('Party add Unsuccessful. Please check the details provided', 'secondary')
    return render_template('add_related_party.html', title='REL', form=form) 
    
    
    
    
# Update Related Party Details
def edit_related_party_logic():
    form = editRTDForm()

    if form.validate_on_submit():
        if form.r_id.data.isdigit():
            cust_uniqueid = form.cmemberid.data
            cust_cclient = form.cname.data            
            rel_id = form.r_id.data  
            rel_name = form.rname.data             
            rel_status = form.rstatus.data.title()
            rel_phone = form.rphone.data
            rel_email = form.remail.data.lower()
            rel_role = form.rrole.data.upper()            
            mod_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')           
            cust_mgr = current_user.username
            client_ip = request.remote_addr
            # Connect to the DB
            logging.debug("Connecting to database...")
            conn = get_db_connection()
            cursor = conn.cursor()
            cust_query = """
            SELECT  partyid from  related_party WHERE partyid = %s
            """
            # Check if the customer ID exists
            cursor.execute(cust_query, (rel_id,))
            existing_trx = cursor.fetchone()
            
            if existing_trx:
                logging.debug("Customer details found, proceeding with update...") 
                
                # SQL UPDATE statement
                update_query = """
                UPDATE related_party
                SET party_phone = %s, party_email = %s, party_role = %s,party_status = %s, date_modified = %s, modified_by = %s
                WHERE partyid = %s
                """
                cursor.execute(f"SET myapp.client_ip = '{client_ip}';")
                cursor.execute(f"SET myapp.cust_mgr = '{cust_mgr}';")                
                # Execute the update statement
                cursor.execute(update_query, (rel_phone, rel_email, rel_role,rel_status,mod_date,cust_mgr,rel_id ))
                
                # Commit the transaction
                conn.commit()                
                
                
               
             
                flash(f'Related Party for {cust_uniqueid} updated Successfully!', 'success')
            else:
                flash('Update failed!', 'error')
            
            cursor.close()
            conn.close()
            return redirect(url_for('home'))
   
        else:
            flash('Update Unsuccessful. Please check the details provided', 'secondary')
    return render_template('edit_related_party.html', title='REX', form=form) 
    
    
    
def fetch_member_logic():
    member_number = request.json.get('member_number')

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("""
        SELECT A.MEMBERSHIP_NUMBER, A.CUST_NAME, B.PARTYID, B.PARTY_NAME
        FROM MEMBERS A
        JOIN RELATED_PARTY B USING(MEMBERSHIP_NUMBER)
        WHERE  B.PARTY_ROLE = 'BENEFICIARY' AND A.MEMBERSHIP_NUMBER = %s
    """, (member_number,))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        return jsonify({"error": "Member not found"}), 404

    cust_name = rows[0]['cust_name']
    parties = [{"party_id": r["partyid"], "party_name": r["party_name"]} for r in rows]

    return jsonify({"cust_name": cust_name, "parties": parties})
    
    
def assign_beneficiary_allocations_logic():
    form = BeneficiaryForm()

    if form.validate_on_submit():
        conn = get_db_connection()
        cur = conn.cursor()
        cust_mgr = current_user.username
        client_ip = request.remote_addr
        for key in request.form:
            if key.startswith('percentage_'):
                party_id = key.split('_')[1]
                percentage = request.form.get(key)
                if percentage:
                    try:
                        cur.execute("""
                            UPDATE RELATED_PARTY
                            SET PERCENTAGE = %s
                            WHERE PARTYID = %s
                        """, (float(percentage), party_id))
                        cur.execute(f"SET myapp.client_ip = '{client_ip}';")
                        cur.execute(f"SET myapp.cust_mgr = '{cust_mgr}';")  
                    except ValueError:
                        continue

        conn.commit()
        cur.close()
        conn.close()

        flash('Beneficiary allocations updated successfully!', 'success')
        return redirect(url_for('home'))

    return render_template('assign_beneficiary_allocations.html', form=form)
    
    
    

def fetch_guarantor_name_logic():
    member_number = request.json.get("member_number")

    if not member_number:
        return jsonify({"cust_name": "", "balance": ""}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT CUST_NAME, balance 
            FROM MEMBERS A 
            JOIN portfolio B USING (MEMBERSHIP_NUMBER)
            WHERE account_type = 'Deposits' AND MEMBERSHIP_NUMBER = %s
        """, (member_number,))
        row = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    if row:
        return jsonify({
            "cust_name": row[0],
            "balance": float(row[1])  # Convert Decimal to float for JSON serialization
        })
    else:
        return jsonify({"cust_name": "", "balance": ""})




        
        
        
def fetch_member_balance_logic():
    member_number = request.json.get("member_number")
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("""
        SELECT A.MEMBERSHIP_NUMBER, A.CUST_NAME, B.BALANCE
        FROM MEMBERS A JOIN PORTFOLIO B USING(MEMBERSHIP_NUMBER)
        WHERE B.ACCOUNT_TYPE = 'Deposits' AND A.MEMBERSHIP_NUMBER = %s
    """, (member_number,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row:
        return jsonify({
            "cust_name": row["cust_name"],
            "balance": float(row["balance"])
        })
    else:
        return jsonify({"error": "Member not found"}), 404
        



def loan_form_logic():
    form = LoanForm()
    conn = None
    cur = None

    if form.validate_on_submit():
        try:
            member_number = form.member_number.data
            amount_borrowed = Decimal(form.amount_borrowed.data)
            disbursement_date = datetime.now()
            loan_tenure = form.loan_tenure.data
            last_update_date = datetime.now()
            pending_amount = -amount_borrowed
            cust_mgr = current_user.username
            client_ip = request.remote_addr
            int_post = "Y"

            conn = get_db_connection()
            conn.autocommit = False  # Explicit commit required
            cur = conn.cursor()

            # Lock necessary internal accounts
            cur.execute("""
                SELECT account_number, balance
                FROM internal_accounts
                WHERE account_number IN ('1001', '1002', '1006')
                FOR UPDATE;
            """)
            acct_1001_number = acct_1002_number = acct_1006_number = None
            acct_1001_balance = acct_1002_balance = acct_1006_balance = None
            for account_number, balance in cur.fetchall():
                if account_number == '1001':
                    acct_1001_number = account_number
                    acct_1001_balance = balance
                elif account_number == '1002':
                    acct_1002_number = account_number
                    acct_1002_balance = balance
                elif account_number == '1006':
                    acct_1006_number = account_number
                    acct_1006_balance = balance

            # Lock portfolio (savings) balance
            cur.execute("""
                SELECT balance, account_no 
                FROM portfolio 
                WHERE account_type = 'Savings' AND membership_number = %s
                FOR UPDATE;
            """, (member_number,))
            existing_trx2 = cur.fetchone()
            if not existing_trx2:
                flash("No savings portfolio found for member.", "danger")
                conn.rollback()
                return render_template("loan_form.html", form=form)

            prev_balance2 = Decimal(existing_trx2[0])
            cust_acct2 = existing_trx2[1]
            new_bal2 = prev_balance2 + amount_borrowed

            # Duplicate loan check
            cur.execute("""
                SELECT 1 FROM loan_accounts
                WHERE member_number = %s AND pending_amount <> 0
                LIMIT 1
            """, (member_number,))

            if cur.fetchone():
                flash("Duplicate loan record detected.", "warning")
                conn.rollback()
                return render_template("loan_form.html", form=form)

            # Insert into loan_accounts
            cur.execute("""
                INSERT INTO loan_accounts (
                    member_number, amount_borrowed, tenure, last_update_date,
                    pending_amount, disbursed_by, disbursement_date
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (member_number, pending_amount, loan_tenure, last_update_date,
                  pending_amount, cust_mgr, disbursement_date))

            # Fetch loan details
            cur.execute("""
                SELECT loan_account, member_loan_number, appraisal_fee 
                FROM loan_accounts 
                WHERE disbursement_date::DATE = CURRENT_DATE AND member_number = %s
            """, (member_number,))
            result = cur.fetchone()
            if not result:
                raise Exception("Loan account could not be retrieved.")
            loan_account, member_loan_number, appraisal_fee = result


            # Create interest account
            int_acct = f"{member_number}INT{member_loan_number}"
            disbursed_amount = amount_borrowed - appraisal_fee
            new_bal3 = prev_balance2 + amount_borrowed - appraisal_fee
            loan_drawdown_acct = f"{loan_account}_Drawdown"
            loan_disbursement_acct = f"{loan_account}_Disbursement"
            loan_appraisal_acct = f"{loan_account}_Appraisal_fee"

            # Insert into interest_accounts
            cur.execute("""
                INSERT INTO INTEREST_ACCOUNTS (
                    membership_number, interest_account, accrued_interest,
                    total_loan_interest, loan_account, amount_borrowed,
                    last_update_date, interest_due
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (member_number, int_acct, 0, 0, loan_account, amount_borrowed,
                  last_update_date, 0))

            # Guarantors
            for key in request.form:
                if key.startswith("guarantor_number_"):
                    suffix = key.split("_")[-1]
                    guarantor_number = request.form.get(f"guarantor_number_{suffix}")
                    amount_guaranteed = request.form.get(f"amount_guaranteed_{suffix}")
                    if guarantor_number and amount_guaranteed:
                        try:
                            cur.execute("""
                                INSERT INTO guarantors (
                                    membership_number, loan_acct,amount_borrowed, disbursement_date,
                                    guarantor_number, amount_guaranteed
                                ) VALUES (%s, %s, %s, %s, %s, %s)
                            """, (member_number,loan_account, amount_borrowed, disbursement_date,
                                  guarantor_number, float(amount_guaranteed)))
                        except ValueError:
                            continue


            # Insert transactions
            trx_insert = """
                INSERT INTO transactions 
                (account_number, narrative, amount, running_balance, posted, entered_by, ipaddr)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cur.execute(trx_insert, (loan_account, 'Loan Disbursement', pending_amount, pending_amount, int_post, cust_mgr, client_ip))
            cur.execute(trx_insert, (cust_acct2, loan_drawdown_acct, amount_borrowed, new_bal2, int_post, cust_mgr, client_ip))
            cur.execute(trx_insert, (cust_acct2, loan_appraisal_acct, -appraisal_fee, new_bal3, int_post, cust_mgr, client_ip))
            cur.execute(trx_insert, (acct_1002_number, loan_account, appraisal_fee, acct_1002_balance + appraisal_fee, int_post, cust_mgr, client_ip))
            cur.execute(trx_insert, (cust_acct2, loan_disbursement_acct, -disbursed_amount, prev_balance2, int_post, cust_mgr, client_ip))
            cur.execute(trx_insert, (acct_1006_number, loan_disbursement_acct, disbursed_amount, acct_1006_balance + disbursed_amount, int_post, cust_mgr, client_ip))

            # Update internal accounts
            cur.execute("UPDATE internal_accounts SET balance = balance + %s WHERE account_number = '1002'", (appraisal_fee,))
            cur.execute("UPDATE internal_accounts SET balance = balance + %s WHERE account_number = '1001'", (amount_borrowed,))
            cur.execute("UPDATE internal_accounts SET balance = balance + %s WHERE account_number = '1006'", (disbursed_amount,))
            cur.execute("UPDATE internal_accounts SET balance = balance - %s WHERE account_number = '1007'", (amount_borrowed,))
            # Create loan schedule
            def end_of_month(year, month):
                day = calendar.monthrange(year, month)[1]
                return datetime(year, month, day).date()

            instalment_amount = round(amount_borrowed / loan_tenure, 2)
            current_month = disbursement_date.month
            current_year = disbursement_date.year

            for i in range(loan_tenure):
                month = current_month + i
                year = current_year + (month - 1) // 12
                month = (month - 1) % 12 + 1
                due_date = end_of_month(year, month)
                cur.execute("""
                    INSERT INTO loan_schedules (
                        instalment_number, instalment_amount, membership_number,
                        loan_account, due_date
                    )
                    VALUES (%s, %s, %s, %s, %s)
                """, (i + 1, instalment_amount, member_number, loan_account, due_date))

            # Finalize
            conn.commit()
            flash("Loan disbursed successfully with repayment schedule!", "success")
            return redirect(url_for("home"))

        except Exception as e:
            if conn:
                conn.rollback()
            logging.exception("Loan processing failed.")
            flash("An error occurred during loan processing. Please try again.", "danger")

        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    return render_template("loan_form.html", form=form)
    
    
def update_loan_status_logic():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Call the stored procedure
        cur.execute("CALL update_due_loans()")

        conn.commit()
        cur.close()
        conn.close()

        flash('Loan status updated successfully.', 'success')
    except Exception as e:
        flash(f'Error updating loan status: {e}', 'danger')

    return redirect(url_for('loans'))

