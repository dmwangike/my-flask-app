#########################################################
# Created on 17th May 2025                              #
# By DAVID KAMANDE                                      #
# dmwangike@yahoo.com				        #
# for PCEA CHAIRETE SACCO			        #
#########################################################
# SET UP THE ENVIRONMENT
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, render_template, url_for, flash, redirect, request, jsonify, send_file, current_app
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix
import socket
from myfunctions.welcome import MembershipLetterGenerator
from forms import CMSForm, CustDetailForm, EnrichForm, populate_bank_choices
from markupsafe import Markup, escape
from jinjasql import JinjaSql
from Runpy import sqlparse
import cryptography as cy
from cryptography.fernet import Fernet
import pandas as pd
import psycopg2
import logging
from flask_mail import Message
from extensions import mail
import re
from openpyxl import load_workbook
import os, shutil
import sys
import zipfile
from reportlab.pdfgen import canvas
import qrcode
import io
from io import BytesIO
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.pagesizes import landscape, letter
import tempfile
import urllib.parse as urlparse

logging.basicConfig(level=logging.DEBUG)

WELCOME_DIR = "/tmp/DATA"
os.makedirs(WELCOME_DIR, exist_ok=True)

def get_db_connection():
    try:
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            raise ValueError("DATABASE_URL is not set in environment variables")
        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
        print(f"Error connecting to Railway DB via DATABASE_URL: {e}")
        return None

def fetch_customers():
    try:
        conn = get_db_connection()
        query = """
        SELECT membership_number, cust_name, post_address, city,
               LPAD(post_code, 5, '0') AS post_code, account_number,
               trans_date::date AS trans_date, trxid AS counter,
               SUBSTRING(narrative, 1, 45) AS narration, amount,
               pref_email
        FROM transactions A
        JOIN portfolio B ON A.account_number = B.account_no
        JOIN MEMBERS C USING (membership_number)
        WHERE posted = 'N'
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
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill='green', back_color='white')
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(temp_file, format="PNG")
    temp_file.close()
    return temp_file.name

import io
from flask import send_file

def generate_receipt(customer):
    membership_number, cust_name, post_address, city, post_code, account_number, trans_date, counter, narration, amount, pref_email = customer

    # Use in-memory buffer instead of disk file
    output = io.BytesIO()
    c = canvas.Canvas(output, pagesize=landscape(letter))
    width, height = landscape(letter)

    logo_path = "logo.png"
    try:
        c.drawImage(logo_path, 50, height - 100, width=100, height=100, mask='auto')
    except Exception as e:
        logging.debug(f"Error loading logo: {e}")

    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.darkgreen)
    c.drawRightString(width - 50, height - 60, "PCEA CHAIRETE SACCO")
    c.setFont("Helvetica", 12)
    c.setFillColor(colors.black)
    c.drawRightString(width - 50, height - 80, "PCEA MACEDONIA CHURCH")
    c.drawRightString(width - 50, height - 95, "ONGATA RONGAI")
    c.drawRightString(width - 50, height - 110, "P.O. Box 28 - 00511, Nairobi")
    c.drawRightString(width - 50, height - 140, "Email: pceabarakaparish@yahoo.com")

    current_date = datetime.now().strftime("%Y-%m-%d")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 120, f" {current_date}")

    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.gold)
    c.drawCentredString(width / 2, height - 160, "Acknowledgement Receipt")
    c.setFillColor(colors.black)

    c.setFont("Helvetica", 12)
    c.drawString(100, height - 200, f"Name: {cust_name}")
    c.drawString(100, height - 220, f"Account ID: {account_number}")
    c.drawString(100, height - 240, f" {post_address or ''}")
    c.drawString(100, height - 260, f" {city or ''}")
    c.drawString(100, height - 280, f" {post_code or ''}")

    table_data = [["TRANDATE", "RECEIPTNO", "AMOUNT", "ACCOUNT"],
                  [trans_date, counter, amount, account_number]]

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

    table.wrapOn(c, width, height)
    table_height = height - 350
    table.drawOn(c, 100, table_height)

    qr_data = f"ID: {membership_number}, Tran_Date: {current_date}, NARRATION {narration}, ReceiptNO: {counter}, Amount: {amount}, ReceiptDate:{trans_date},Account:{account_number}"
    qr_file_path = generate_qr_code(qr_data)
    qr_x = width - 250
    qr_y = table_height - 150
    c.drawImage(qr_file_path, qr_x, qr_y, width=120, height=120, mask='auto')

    c.save()
    os.unlink(qr_file_path)

    output.seek(0)  # Important: rewind the buffer for reading

    # Optionally update the DB
    conn = get_db_connection()
    cursor = conn.cursor()
    update_query = """
        UPDATE transactions 
        SET posted = 'Y'
        WHERE trxid = %s
    """
    cursor.execute(update_query, (counter,))
    conn.commit()

    # Email the receipt
    if pref_email:
        try:
            with current_app.app_context():
                msg = Message(
                    subject="DEPOSIT RECEIPT",
                    sender=current_app.config['MAIL_USERNAME'],
                    recipients=[pref_email],
                    cc=["dmwangike@yahoo.com"],
                    body="Dear Member,\n\nFind attached your receipt for your recent deposit.\n\nKind Regards,\n\nPCEA CHAIRETE SACCO."
                )
                msg.attach(f"receipt_{account_number}_{counter}.pdf", "application/pdf", output.getvalue())
                mail.send(msg)
        except Exception as e:
            logging.error(f"Failed to send email to {pref_email}: {e}")

    # Return PDF buffer for download
    filename = f"receipt_{account_number}_{counter}.pdf"
    return send_file(output, download_name=filename, as_attachment=True)


def receipt_customer():
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
    flash('Receipts generated and emailed successfully. Please check spool location', 'success')
    return redirect(url_for('home'))
