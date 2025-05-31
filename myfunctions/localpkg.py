#########################################################
# Created on 04th Nov 2024                              #
# By DAVID KAMANDE                                      #
# To spool extracted data into PDFs                     #
#########################################################

#import Libraries
from dotenv import load_dotenv
load_dotenv()
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Spacer, Image, PageBreak
from datetime import datetime
from reportlab.lib.units import inch, cm
import os
from math import ceil
import logging
logging.basicConfig(level=logging.DEBUG)
import psycopg2
from flask import Flask, render_template, url_for, flash, redirect,request,jsonify,send_file, make_response
import urllib.parse as urlparse


   
# Define the Base directory for output files
base_directory = r"E:\oikonomos\DATA"



#  DEFINE The FILE TO LOG EVENTS
LOG_FILE = 'E:\\oikonomos\\logs\\execution_log.txt'

# Base path to save PDFs
BASE_PDF_OUTPUT_DIR = 'E:\\oikonomos\\DATA'

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
        


# FUNCTION TO LOG EVENTS
def log_event(message):
    """Append a log message to the log file."""
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")


# Define constants for layout
LEFT_MARGIN = 28.35  # 1 cm left margin in points
RIGHT_MARGIN = 28.35  # 1 cm right margin in points
PAGE_WIDTH, PAGE_HEIGHT = A4
    
def create_date_folder():
    current_date = datetime.now().strftime("%Y-%m-%d")
    date_folder_path = os.path.join(base_directory, current_date)
    os.makedirs(date_folder_path, exist_ok=True)
    return date_folder_path
    

def create_bank_statement_revised(filename, header_info, account_info, transactions, footer_info):
    doc = SimpleDocTemplate(filename, pagesize=A4, leftMargin=LEFT_MARGIN, rightMargin=RIGHT_MARGIN)
    elements = []  # List to store the PDF elements

    # Define column widths for header and transaction tables
    left_column_width = (2 / 3) * (PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN)
    right_column_width = (1 / 3) * (PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN)

    # Load the company logo image
    logo_path = "logo.png"
    logo_width = left_column_width - 28.35
    logo_image = Image(logo_path, width=logo_width, height=0.75 * inch)

    # Define header table data
    header_data = [
        [
            logo_image,
            f"Statement Date: {header_info['date']}\n"
            f"Statement Period: {header_info['period']}\n"
            f"Statement Number: {header_info['number']}"
        ],
        [
            "\n".join(map(str, header_info['address'])),
            f"Account Number: {account_info['number']}\n"
            f"Account Description: {account_info['description']}\n"
            f"Currency: {account_info['currency']}"
        ]
    ]

    # Create the header table
    header_table = Table(header_data, colWidths=[left_column_width, right_column_width])
    header_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica', 6),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('GRID', (0, 0), (-1, -1), 0, colors.white),
    ]))

    # Function to draw the header on each page at 2 cm from the top
    def draw_header(canvas, doc):
        header_table.wrapOn(canvas, doc.width, doc.topMargin)
        header_table.drawOn(canvas, LEFT_MARGIN, PAGE_HEIGHT - 6 * cm)

    # Adjust column widths as specified
    trans_date_width = 0.9 * inch - 0.5 * cm
    value_date_width = 0.9 * inch - 0.5 * cm
    description_width = 1.8 * inch + (1.5 * cm)
    reference_width = 0.9 * inch - 0.5 * cm    
    debit_credit_width = 0.8 * inch



    # Split transactions into chunks of 40 per page
    chunk_size = 40
    total_chunks = ceil(len(transactions) / chunk_size)

    # Transaction column headers
    transaction_headers = ["Trans Date", "Value Date", "Description","Reference","Credit",  "Debit"]

    for i in range(total_chunks):
        # Add a page break for all pages after the first one
        if i > 0:
            elements.append(PageBreak())
        
        # Add a spacer to position the transaction table 10 cm from the top
        elements.append(Spacer(1, 10 * cm - 6 * cm))  # Spacer to position transaction table at 10 cm below page top 

        # Add transaction headers for each chunk/page
        transaction_data = [transaction_headers]

        # Add the 40 (or fewer) transactions for this page
        transaction_chunk = transactions[i * chunk_size:(i + 1) * chunk_size]
        for txn in transaction_chunk:
 
              
            transaction_data.append([
                str(txn.get('TRAN DATE', 'N/A')),
                str(txn.get('VALUE DATE', 'N/A')),                
                str(txn.get('DESCRIPTION', 'N/A')),
                str(txn.get('REFERENCE', 'N/A')),                
                str(txn.get('CREDIT', '0.00')),
                str(txn.get('DEBIT', '0.00'))
            ])

        # Create the transaction table for this page with the adjusted column widths
        transaction_table = Table(transaction_data, colWidths=[
            trans_date_width,
            value_date_width,            
            description_width,
            reference_width,
            debit_credit_width,
            debit_credit_width
        ])
        transaction_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 6),
            ('FONT', (0, 1), (-1, -1), 'Helvetica', 6),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('ALIGN', (4, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
        ]))
        
        elements.append(transaction_table)

    # Footer section on the last page only
    elements.append(Spacer(1, 1 * cm))  # Spacer to position footer
    footer_data = [
        [f"Closing Book Balance: {footer_info['closing_book_balance']}"],
    ]
    footer_table = Table(footer_data, colWidths=[left_column_width + right_column_width])
    footer_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica', 6),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT')
    ]))
    elements.append(footer_table)

    # Build the PDF with header on each page and footer only on the last page
    doc.build(elements, onFirstPage=draw_header, onLaterPages=draw_header)
    
    
    
def generate_statements_logic():
    start_time = datetime.now()
    logging.debug("Statement Generation process started...")
    log_event("Statement Generation process started.")
	
    #Create output folder with current date
    output_folder = create_date_folder()
    logging.debug("Spool folder Created...")
    log_event("Spool folder Created....")
	
    stmt_qry = """
    WITH transactions AS ( SELECT "CLIENT_ID" AS account_no,"TRAN_DATE"::timestamp::date AS "TRAN DATE", 
        "VALUE_DATE"::timestamp::date AS "VALUE DATE", "TRANSACTIONAMOUNT"::numeric AS "CREDIT", 
        '0'::numeric AS "DEBIT",'Deposit' AS "DESCRIPTION", "UBACCTRANSCOUNTER"::text AS "REFERENCE" FROM htd_stmt 
    WHERE "TRAN_DATE"::date >= (date_trunc('month', current_date) - interval '1 month')::date
    AND "RECEIPT_STATUS" = 'Y'    
    UNION ALL    
    SELECT  account_no,withdrawal_date::timestamp::date AS trandate,withdrawal_date::timestamp::date AS valuedate,
        '0'::numeric AS credit,amount::numeric AS debit,'Withdrawal' AS DESCRIPTION,withdrawal_id::text 
    FROM withdrawals WHERE status = 'Y' 
    AND withdrawal_date::date >= (date_trunc('month', current_date) - interval '1 month')::date
    )
    SELECT cust_name,  post_address,  LPAD(post_code::text, 5, '0') as "Postal Code",  city, balance, c.* FROM clients a JOIN portfolio b USING (customer_id)
    JOIN transactions c USING (account_no)
    """
    conn=get_db_connection()       
    logging.debug("Executing SQL script...")

    df = pd.read_sql(stmt_qry, conn)
    if conn is not None:
        conn.close()

    logging.debug("Statement data imported to dataframe...")
    log_event("Statement data imported....")
    df = df.astype({'TRAN DATE': str, 'VALUE DATE': str, 'Postal Code': str})

	

    # Replace None/NaN with empty string
    df = df.fillna('')
	
	
    logging.debug("Spooling Statements Started...")
    log_event("Spooling statement started....")  

 
    # Loop through each unique account number in the DataFrame
    for account_number in df['account_no'].unique():
        # Filter and sort DataFrame for the current account number
        account_df = df[df['account_no'] == account_number].sort_values(by='TRAN DATE')

        # Extract header information
        header_info = {
            'date': datetime.today().date(),
            'period': datetime.today().date(),
            'number': 1,
            'address': [
                account_df['cust_name'].iloc[0],
                account_df['post_address'].iloc[0],
                account_df['city'].iloc[0],
                account_df['Postal Code'].iloc[0]
            ]
        }
        description = 'Money Market Fund' if account_df['account_no'].iloc[0].startswith('CL') else 'Bond Fund'
        # Extract account information
        account_info = {
            'number': account_df['account_no'].iloc[0],
            'description': description,
            'currency': 'KES'
        }

        # Prepare transactions as a list of dictionaries
        transactions = account_df[['TRAN DATE',  'VALUE DATE', 'DESCRIPTION', 'REFERENCE','CREDIT', 'DEBIT']].to_dict(orient='records')

        # Handle NaN values in transactions and convert numerical values to strings
        for txn in transactions:
            txn['CREDIT'] = str(txn['CREDIT']) if pd.notna(txn['CREDIT']) else '0.00'
            txn['DEBIT'] = str(txn['DEBIT']) if pd.notna(txn['DEBIT']) else '0.00'

        # Prepare footer information (assuming last entry's balances as footer info)
        footer_info = {
            'closing_book_balance': str(account_df['balance'].iloc[-1]) if pd.notna(account_df['balance'].iloc[-1]) else '0.00',

        }

        # Define output file path with account number in the filename

        output_path = os.path.join(output_folder, f"Statement_{account_number}.pdf")

        # Generate the statement PDF for the current account number
        create_bank_statement_revised(output_path, header_info, account_info, transactions, footer_info)

    logging.debug("Spooling Statements Completed...")
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    log_event("Statement Generation process completed.")	
    log_event(f"Execution duration: {duration:.2f} seconds")
    logging.debug("Statement Generation process completed...")	
    flash(f'Statement spooling completed successfully. Review logs for details.', 'success')	
    # Redirect back to the home page after generating PDFs
    #return redirect(url_for('home')) 
  
    
    
    
    

