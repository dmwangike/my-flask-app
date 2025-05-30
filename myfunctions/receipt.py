#########################################################
# Created on 17th May 2025                              #
# By DAVID KAMANDE                                      #
# dmwangike@yahoo.com				        #
# for PCEA CHAIRETE SACCO			        #
#########################################################
# SET UP THE ENVIRONMENT
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, render_template, url_for, flash, redirect,request,jsonify,send_file
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix
import socket
from myfunctions.welcome import MembershipLetterGenerator
from forms import  CMSForm, CustDetailForm,EnrichForm,populate_bank_choices
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






from reportlab.pdfgen import canvas
import qrcode
from io import BytesIO
import os
import tempfile

from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle

from reportlab.lib.pagesizes import landscape, letter


def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=os.environ.get('PGHOST'),
            database=os.environ.get('PGDATABASE'),
            user=os.environ.get('PGUSER'),
            password=os.environ.get('PGPASSWORD'),
            port=os.environ.get('PGPORT')
        )
        return conn
    except Exception as e:
        print(f"Error connecting to Railway DB: {e}")
        return None





#Create the Spool Path
WELCOME_DIR = "E:\\oikonomos\\DATA"
os.makedirs(WELCOME_DIR, exist_ok=True)



def fetch_customers():
    """Fetch customer data from the PostgreSQL database."""
    try:
        conn = get_db_connection()
        query = """
        select membership_number, cust_name,post_address,city,lpad(post_code, 5, '0') as post_code,account_number,
        trans_date::date AS trans_date,trxid as counter, substring(narrative,1,45) as narration ,amount from transactions A  join portfolio B 
	on A.account_number = B.account_no join MEMBERS C USING(membership_number) where posted = 'N'      
        """
        cursor = conn.cursor()
        cursor.execute(query)
        customers = cursor.fetchall()
        conn.close()
        return customers
    except Exception as e:
        logging.debug(f"Error fetching data: {e}")
        return []
        
        
        
def generate_qr_code(data):
    """Generate a QR code for the given data and return it as a temporary file path."""
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill='green', back_color='white')

    # Save to a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(temp_file, format="PNG")
    temp_file.close()
    return temp_file.name
    
    
    
def generate_receipt(customer):
    """Generate a PDF receipt for the customer."""
    membership_number, cust_name,post_address,city,post_code,account_number, trans_date, counter, narration ,amount = customer
    receipt_file = os.path.join(WELCOME_DIR, f"receipt_{account_number}_{counter}.pdf")
    c = canvas.Canvas(receipt_file, pagesize=landscape(letter))  # Set landscape orientation
    width, height = landscape(letter)

    # Add company logo at the top-left corner
    logo_path = "logo.png"
    try:
        c.drawImage(logo_path, 50, height - 100, width=100, height=100, mask='auto')
    except Exception as e:
        logging.debug(f"Error loading logo: {e}")

    # Add the company address at the top-right corner
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.darkgreen)
    c.drawRightString(width - 50, height - 60, "PCEA CHAIRETE SACCO")
    c.setFont("Helvetica", 12)
    c.setFillColor(colors.black)
    c.drawRightString(width - 50, height - 80, "PCEA MACEDONIA CHURCH")
    c.drawRightString(width - 50, height - 95, "ONGATA RONGAI")
    c.drawRightString(width - 50, height - 110, "P.O. Box 28 - 00511, Nairobi")
    c.drawRightString(width - 50, height - 140, "Email: pceabarakaparish@yahoo.com")
    
    # Add the date below the company logo
    current_date = datetime.now().strftime("%Y-%m-%d")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 120, f" {current_date}")

    # Add receipt header
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.gold)
    c.drawCentredString(width / 2, height - 160, "Acknowledgement Receipt")
    c.setFillColor(colors.black)

    # Add customer details
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 200, f"Name: {cust_name}")
    c.drawString(100, height - 220, f"Account ID: {account_number}")
    c.drawString(100, height - 240, f" {post_address or ''}")
    c.drawString(100, height - 260, f" {city or ''}")
    c.drawString(100, height - 280, f" {post_code or ''}")
    
    # Create a table with transaction details
    table_data = [
        ["TRANDATE", "RECEIPTNO",  "AMOUNT","ACCOUNT"],
        [trans_date, counter,  amount,account_number]
    ]

    table = Table(table_data, colWidths=[120, 120, 120, 120])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.green),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgoldenrodyellow),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    # Position and draw the table
    table.wrapOn(c, width, height)
    table_height = height - 350
    table.drawOn(c, 100, table_height)

    # Generate and add the QR code below the table
    qr_data = f"ID: {membership_number}, Tran_Date: {current_date}, NARRATION {narration}, ReceiptNO: {counter}, Amount: {amount}, ReceiptDate:{trans_date},Account:{account_number}"
    qr_file_path = generate_qr_code(qr_data)
    qr_x = width - 250
    qr_y = table_height - 150  # Place QR code below the table
    c.drawImage(qr_file_path, qr_x, qr_y, width=120, height=120, mask='auto')

    # Finalize the PDF
    c.save()

    # Clean up the temporary QR code file
    os.unlink(qr_file_path)
    conn = get_db_connection()
    cursor = conn.cursor()
    # SQL UPDATE statement
    update_query = """
    update transactions 
    SET posted =  'Y'
    WHERE trxid =  %s
    """
                
    # Execute the update statement
    cursor.execute(update_query, (counter,))
                
    # Commit the transaction
    conn.commit()   


   
    logging.debug(f"Receipt generated: {receipt_file}") 











def receipt_customer():
    """Main function to fetch customer data and generate receipts."""
    # Invoke the PostgreSQL procedure update_tran_date to change valuedate
    try:
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute("CALL update_tran_date();")
            conn.commit()
    except Exception as e:
        logging.error(f"Error executing update_tran_date procedure: {e}")
        flash('Error updating transaction dates', 'danger')
        return redirect(url_for('home'))
    finally:
        if conn:
            conn.close()

    customers = fetch_customers()
    if not customers:
        logging.debug("No customers found or error fetching data.")
        flash('No valid customers to receipt', 'success')        
        return redirect(url_for('home')) 

    for customer in customers:
        generate_receipt(customer)
    flash('Receipts generated successfully. Please check spool location', 'success')
    return redirect(url_for('home'))   
