#########################################################
# Created on 17th May 2025                              #
# By DAVID KAMANDE                                      #
# dmwangike@yahoo.com                                   #
# for PCEA CHAIRETE SACCO			        #
#########################################################
# SET UP THE ENVIRONMENT
from flask_login import current_user, login_required
from flask import Flask, render_template, url_for, flash, redirect,request,jsonify,send_file
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix
import socket
from myfunctions.welcome import MembershipLetterGenerator
from forms import   CMSForm, CustDetailForm,EnrichForm,UpdateTRXForm,populate_bank_choices
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
from psycopg2 import errors
import logging
logging.basicConfig(level=logging.DEBUG)
from decimal import Decimal
from myfunctions.receipt import receipt_customer


import re

from openpyxl import load_workbook


import os,shutil
import sys
#import paramiko
from base64 import decodebytes
import zipfile



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



# Populate the KYC Details for a Member
def enrich_cust_details_logic():
    form = EnrichForm()
    regex = re.compile(r'[A-Za-z0-9 _-]+')
    if form.validate_on_submit():
        if regex.match(form.cmemberid.data):
            cust_name = form.cname.data
            cust_memid = form.cmemberid.data
            cust_postadd = form.cpostadd.data
            cust_postcode = form.cpostcode.data.upper()
            cust_city = form.ccity.data.upper()
            cust_occu = form.coccu.data.upper()
            cust_congr = form.ccongr.data            
            cust_resd = form.cresd.data.upper()            
            mod_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            #cust_mgr = os.getlogin()
            cust_mgr = current_user.username
            client_ip = request.remote_addr
            # Connect to the DB
            logging.debug("Connecting to database...")
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if the customer ID exists
            cursor.execute("SELECT MEMBERSHIP_NUMBER FROM MEMBERS WHERE  post_address is null and MEMBERSHIP_NUMBER = %s", (cust_memid,))
            existing_customer = cursor.fetchone()
            
            if existing_customer:
                logging.debug("Customer details found, proceeding with update...")  
                
                # SQL UPDATE statement
                update_query = """
                UPDATE MEMBERS
                SET post_address = %s, post_code = %s,city= %s, occupation = %s, date_modified = %s,modified_by = %s, congregation = %s,residence = %s
                WHERE MEMBERSHIP_NUMBER = %s
                """
                cursor.execute(f"SET myapp.cust_mgr = '{cust_mgr}';") 
                cursor.execute(f"SET myapp.client_ip = '{client_ip}';")                
                # Execute the update statement
                cursor.execute(update_query, (cust_postadd,cust_postcode,cust_city, cust_occu, mod_date,cust_mgr,cust_congr,cust_resd,cust_memid))
                
                # Commit the transaction
                conn.commit()
             
                flash(f'Customer No {cust_memid} Updated Successfully!', 'success')
            else:
                flash('Member ID not found or cannot be enriched further, update failed!', 'error')
            
            cursor.close()
            conn.close()
            return redirect(url_for('home'))
   
        else:
            flash('Update Unsuccessful. Please check the details provided', 'secondary')
    return render_template('enrich_member_details.html', title='EMS', form=form)



def update_trx_details_logic():
    form = UpdateTRXForm()
    regex = re.compile(r'[A-Za-z0-9 _-]+')

    if form.validate_on_submit():
        #if regex.match(form.cmemberid.data):
        if form.cmemberid.data and regex.match(form.cmemberid.data):
            cust_name = form.cname.data
            cust_tranid = form.ctranid.data
            try:
                cust_amount = Decimal(form.camount.data)
            except:
                flash("Invalid amount format. Please enter a valid number.", "danger")
                return render_template('update_member_payment.html', title='MXP', form=form)

            cust_mgr = current_user.username
            client_ip = request.remote_addr
            cust_membid = form.cmemberid.data

            logging.debug("Connecting to database...")
            conn = get_db_connection()
            conn.autocommit = False  # Explicitly disable auto-commit
            cursor = conn.cursor()

            try:
                # Lock the portfolio row for update
                cust_query = """
                      SELECT a.balance AS cust_bal, a.account_no AS cust_acct,b.balance AS int_bal, b.account_number AS int_acct
                      FROM portfolio a
                      JOIN internal_accounts b ON b.account_number = '1006'
                      WHERE a.membership_number = %s AND account_type = 'Savings'
                      FOR UPDATE OF a, b;
                """
                cursor.execute(cust_query, (cust_membid,))
                existing_trx = cursor.fetchone()

                if existing_trx:
                    prev_balance = Decimal(existing_trx[0])
                    prev_int_bal = Decimal(existing_trx[2])
                    cust_acct = existing_trx[1]
                    int_acct = existing_trx[3]
                    new_bal = prev_balance + cust_amount
                    int_new_bal = prev_int_bal - cust_amount
                    int_post = "Y"
                    # Check for duplicate transaction
                    duplicate_check_query = """
                        SELECT 1 FROM transactions
                        WHERE account_number = %s AND narrative = %s AND amount = %s
                          AND entered_by = %s AND ipaddr = %s
                        LIMIT 1
                    """
                    cursor.execute(duplicate_check_query, (
                        cust_acct, cust_tranid, cust_amount, cust_mgr, client_ip
                    ))
                    duplicate = cursor.fetchone()

                    if duplicate:
                        flash('Duplicate transaction detected. This transaction already exists.', 'warning')
                    else:
                        # Insert new transaction: Customer leg
                        insert_query = """
                            INSERT INTO transactions 
                            (account_number, narrative, amount, running_balance, entered_by, ipaddr)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """
                        cursor.execute(insert_query, (
                            cust_acct, cust_tranid, cust_amount, new_bal, cust_mgr, client_ip
                        ))
                        # Insert new transaction: Internal leg
                        insert_query = """
                            INSERT INTO transactions 
                            (account_number, narrative, amount, running_balance, posted,entered_by, ipaddr)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """
                        cursor.execute(insert_query, (
                            int_acct, cust_tranid, cust_amount * -1, int_new_bal,int_post,cust_mgr, client_ip
                        ))

                        # Update portfolio balance: Customer leg
                        update_query = """
                            UPDATE portfolio
                            SET balance = %s
                            WHERE account_no = %s
                        """
                        cursor.execute(update_query, (new_bal, cust_acct))

                        # Update Internal balance: Internal Account leg
                        update_query1 = """
                            UPDATE internal_accounts
                            SET balance = %s
                            WHERE account_number = %s
                        """
                        cursor.execute(update_query1, (int_new_bal, int_acct))
                        # Commit transaction
                        conn.commit()

                        # Generate receipt or confirmation
                        receipt_customer()  # Make sure this function handles errors internally

                        flash(f'Transaction for Member No {cust_membid} Updated Successfully!', 'success')

                else:
                    flash('Update failed! Member record not found.', 'danger')

            except Exception as e:
                conn.rollback()
                logging.exception("Transaction update failed:")
                flash("An error occurred while processing the transaction. Please try again.", "danger")

            finally:
                cursor.close()
                conn.close()

            return redirect(url_for('home'))
        else:
            logging.debug("Regex validation failed for member ID.")
            #flash('Invalid Member ID format.', 'danger')

    return render_template('update_member_payment.html', title='MXP', form=form)
  
 # Member Customer Details   



def capture_cust():
    form = CustDetailForm()

    regex = re.compile(r'[A-Za-z0-9 _-]+')

    if form.validate_on_submit():
        if regex.match(form.cname.data):
            cust_name = form.cname.data.title()
            cust_uniqueid = form.cuniqueid.data.upper()
            cust_taxid = form.ctaxid.data.upper()
            cust_tax = form.ctax.data
            cust_join = datetime.now()
            cust_phone = form.cphone.data
            cust_email = form.cemail.data.lower()
            cust_gend = form.cgender.data.upper()
            cust_dob = form.cdob.data
            cust_mgr = current_user.username
            cust_status = 'Active'


            # Connect to the DB
            logging.debug("Connecting to database...")
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                # SQL INSERT statement to insert Member details
                insert_query = """
                INSERT INTO MEMBERS (cust_name, gender, date_of_birth, identification, tax_cert, tax_exempt,
                                     pref_phone, pref_email, datejoined, membership_status,
                                     created_by, date_modified, modified_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_query, (cust_name, cust_gend, cust_dob, cust_uniqueid, cust_taxid,
                                              cust_tax, cust_phone, cust_email, cust_join, cust_status,
                                              cust_mgr, cust_join, cust_mgr))
            
                # Rest of your code for inserting into portfolio...
                cursor.execute("SELECT MAX(member_id) AS cust_id, MAX(membership_number) AS memb_id FROM members")
                result = cursor.fetchone()
                if result and result[0]:
                    cust_id = int(result[0])
                    memb_id = result[1]
                    acct_id = f"{memb_id}_SV"
                    acct_id2 = f"{memb_id}_DT"
                    acct_type = 'Savings'
                    acct_type2 = 'Deposits'
                    cust_join = datetime.now()
                    rows_to_insert = [(cust_id, acct_id, 0, cust_join, memb_id, acct_type)]
                    rows_to_insert2 = [(cust_id, acct_id2, 0, cust_join, memb_id, acct_type2)] 

            
                    insert_portfolio_query = """
                    INSERT INTO portfolio (customer_id, account_no, balance, open_date, membership_number, account_type)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    cursor.executemany(insert_portfolio_query, rows_to_insert)
                    insert_portfolio_query2 = """
                    INSERT INTO portfolio (customer_id, account_no, balance, open_date, membership_number, account_type)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    cursor.executemany(insert_portfolio_query, rows_to_insert2)
            
                    conn.commit()

                    generator = MembershipLetterGenerator(cust_id)
                    data = generator.fetch_data()
                    if data:
                        generator.generate_pdf(data)
                    else:
                        print("No data found to generate letters.")
                        
                logging.debug(f'New Account {acct_id} Created...')
            

                
                flash(f'Member No {memb_id} Added Successfully!', 'success')
                return redirect(url_for('home'))
            
            except psycopg2.errors.UniqueViolation as e:
                conn.rollback()  # Undo any partial inserts
                flash(f"Duplicate Entry: A customer with ID {cust_uniqueid} already exists.", 'danger')
                logging.debug(f"Duplicate Entry: A customer with ID {cust_uniqueid} already exists.")
                logging.error(f"Unique constraint violated: {e}")
            except Exception as e:
                conn.rollback()
                flash("An error occurred while adding the customer.", 'danger')
                logging.exception("Unexpected error")
            finally:
                cursor.close()
                conn.close()






        else:
            flash('Insert Unsuccessful. Please check the details provided', 'secondary')

    return render_template('capture_member_details.html', title='MXS', form=form)

   
    
    
    
    
 # Get Customer details for display   
def get_customer_name_logic():
    """Fetch customer name based on the provided cmemberid."""
    cmemberid = request.form.get('cmemberid')
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Query to get the customer name
    query = "SELECT cust_name FROM MEMBERS WHERE post_address is null and membership_number = %s"
    cursor.execute(query, (cmemberid,))
    result = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    # Return the customer name as a JSON response
    if result:
        return jsonify({'cname': result[0]})
    else:
        return jsonify({'cname': ''})   
        

 # Get tranasctions details for display   
def get_trx_details_logic():

    cmemberid = request.form.get('cmemberid')
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Query to get the customer name
    query = "SELECT cust_name FROM MEMBERS WHERE membership_number = %s"
    cursor.execute(query, (cmemberid,))
    result = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    # Return the customer name as a JSON response
    if result:
        return jsonify({'cname': result[0]})
    else:
        return jsonify({'cname': ''})   
        
 
def write_customer_welcome_logic(cust_id):
    """Fetch customer details and append to an Excel file."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Query to get the customer details
    query = """SELECT a.customer_id, account_no, cust_name, 
                      'Investor' AS salutation, pref_phone, pref_email, 
                      post_address, post_code, city, created_by, tax_cert
               FROM clients a
               JOIN portfolio b ON a.customer_id = b.customer_id
               WHERE SUBSTRING(account_no, 1, 2) = 'CL' AND a.customer_id = %s"""
    
    # Execute the query
    cursor.execute(query, (cust_id,))
    
    # Fetch all rows from the result
    result = cursor.fetchall()
    
    # Get column names (assuming the query's columns are ordered as they appear)
    column_names = [desc[0] for desc in cursor.description]
    
    # Close the cursor and connection
    cursor.close()
    conn.close()

    # Create a DataFrame from the result
    if result:
        df = pd.DataFrame(result, columns=column_names)
        
        # Define the path to the Excel file
        file_path = 'E:\\oikonomos\\DATA\\welcome letter.xlsx'
        
        # Check if the Excel file exists
        if os.path.exists(file_path):
            # If the file exists, load the workbook and append the data
            with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
                df.to_excel(writer, index=False, header=False, sheet_name='Sheet1', startrow=writer.sheets['Sheet1'].max_row)
        else:
            # If the file does not exist, create it and write the data
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Sheet1')
        
        return jsonify({'message': 'Data written to Excel successfully!'})
    else:
        return jsonify({'message': 'No data found for the given customer ID.'})
        



def append_customer_to_register(cust_uniqueid):
    """Fetch customer details and append to an Excel file."""
    
    # Establish connection to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    win_user = os.getlogin()


    # Query to get the customer details
    query = """
    SELECT clients.customer_id, account_no, cust_name, 'Investor' as Prefix, ownership, initialdep, datejoined,
    cust_acct, cust_bank, cust_branch, dep_freq, fund_source, identification, tax_cert,
    pref_phone, pref_email, post_address, post_code, city, date_of_birth, gender,
    civic_status, kin_details, occupation, tax_exempt, 'N/A' as tex_expry, aml_risk, pep_flg, pep_level, created_by
    FROM portfolio JOIN clients  ON clients.customer_id = portfolio.customer_id
    WHERE substring(account_no,1,2) = 'CL' and clients.customer_id = %s
    """
    
    # Execute the query with the customer unique ID
    cursor.execute(query, (cust_uniqueid,))
    
    # Fetch all rows from the result
    result = cursor.fetchall()
    
    # Get column names (assuming the query's columns are ordered as they appear)
    column_names = [desc[0] for desc in cursor.description]
    
    # Close the cursor and connection
    cursor.close()
    conn.close()

    # Create a DataFrame from the result
    if result:
        df = pd.DataFrame(result, columns=column_names)
        
        # Define the path to the Excel file
        file_path = 'E:\\oikonomos\\DATA\\register.xlsx'
        
        # Check if the Excel file exists
        if os.path.exists(file_path):
            # If the file exists, load the workbook and append the data
            with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
                df.to_excel(writer, index=False, header=False, sheet_name='Sheet1', startrow=writer.sheets['Sheet1'].max_row)
        else:
            # If the file does not exist, create it and write the data
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Sheet1')
        
        return jsonify({'message': 'Data written to Excel successfully!'})
    else:
        return jsonify({'message': 'No data found for the given customer ID.'})






def parameterize_SQL_in_statement(items):
    return f"""('{"', '".join(items)}')"""        
        
        
def fetch_oracle(conditions):
    try:
 
        placeholders = parameterize_SQL_in_statement(conditions)
        # SQL script to execute (ensure this is safe and sanitized)
        sql_script = f"""SELECT ACCT_NAME BANK_NAME, FORACID BANK_ACCT, SOL_ID BANK_BR,ACCT_CLS_FLG CLOSE_FLAG, 
        UNIQUEID AS CUST_ID, FREZ_CODE,STRUSERFIELD6 PEP_FLG, STRUSERFIELD7 PEPNAME, STRUSERFIELD8 PEP_ROLE FROM TBAADM.GAM@finstby
        A JOIN CRMUSER.ACCOUNTS@finstby B ON A.CIF_ID = B.ORGKEY WHERE FORACID IN {placeholders}"""

        # Connect to the DB
        logging.debug("Connecting to the database...")
        conn = get_connection()  # This is your connection pool or method
        logging.debug("Executing SQL script...")

        try:
            # Execute the query and return the result as a DataFrame
            df_oracle = pd.read_sql(sql_script, conn)
        except oracledb.InterfaceError:
            logging.warning("Connection failed, retrying...")
            conn = get_connection()  # Reconnect in case of failure
            df_oracle = pd.read_sql(sql_script, conn)
        finally:
            if conn:
                pool.release(conn)  # Release the connection back to the pool

    except oracledb.DatabaseError as e:
        error, = e.args
        logging.error(f"Oracle Database Error: {error.message}")
        return None  # Return None or handle the error as needed

    return df_oracle


