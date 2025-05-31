import psycopg2
from fpdf import FPDF
from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv()

import urllib.parse as urlparse

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




class MembershipLetterGenerator:
    def __init__(self,cust_id):
        #self.db_params = db_params
        self.cust_id = cust_id

    def fetch_data(self):
        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            query = (
             "select account_no as \"ACCOUNT NUMBER\", cust_name as \"NAME\", membership_number as \"MEMBER NUMBER\", "
            "post_code as \"Code\", city as \"City\" from members m join portfolio  p using(membership_number) "
            "where  account_type = 'Savings' and member_id = %s"
            )
            cursor.execute(query,(self.cust_id,))
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            print(f"Error fetching data: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    def generate_pdf(self, data):
        output_directory = "/tmp/DATA"
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)

        for row in data:
            pdf = FPDF()
            pdf.add_page()

            # Add a Unicode-capable font (e.g., using the Times New Roman or any other font with Unicode support)
            pdf.add_font('Times', '', 'C:\\Windows\\Fonts\\times.ttf', uni=True)  # Ensure the font supports Unicode
            pdf.set_font("Times", size=9)

            # Dimensions for the table
            page_width = 210  
            margin = 10
            table_width = page_width - 2 * margin  
            column_width = table_width / 3  
            table_y = 10  
            table_height = 70  

            # First column: Logo
            logo_x = margin
            logo_y = table_y
            logo_width = column_width
            logo_height = table_height
            pdf.image("logo.png", x=logo_x, y=logo_y, w=logo_width, h=logo_height)

            # Second column: Empty 
            pdf.set_xy(margin + column_width, table_y)
            pdf.cell(column_width, table_height, "", border=0)

            # Third column: Organizational address
            address_x = margin + 2 * column_width
            pdf.set_xy(address_x, table_y)

            # Organizational Address 
            pdf.set_font("Times", style="B", size=9)
            pdf.multi_cell(column_width, 5, ("PCEA CHAIRETE SACCO\n"
                "PCEA MACEDONIA CHURCH\n"
                "ONGATA RONGAI\n"
                "P.O. Box 28 - 00511, Nairobi\n"
                "Email: pceabarakaparish@yahoo.com\n"
                                             ), align="L")

            # Current Date
            pdf.set_y(table_y + table_height + 5)
            current_date = datetime.now().strftime("%B %d, %Y")
            pdf.cell(0, 5, current_date, ln=True)

            # Recipient Details
            name = row.get("NAME") or ""
            address = row.get("MEMBER NUMBER") or ""
            code = row.get("Code") or ""
            city = row.get("City") or ""

            pdf.ln(5)
            pdf.cell(0, 5, name, ln=True)
            pdf.cell(0, 5, f"{address} - {code}", ln=True)
            pdf.cell(0, 5, city, ln=True)

            # Salutation
            pdf.ln(5)
            pdf.set_font("Times", size=12)
            pdf.cell(0, 5, "Dear Member,", ln=True)

            # Reference
            pdf.ln(3)           
            pdf.set_font("Times", style="BU", size=12)
            pdf.cell(0, 5, "RE: MEMBERSHIP CONFIRMATION", ln=True)

            # Paragraph
            pdf.ln(3)  
            pdf.set_font("Times", size=12)
            pdf.multi_cell(0, 5, (
            "Thank you for choosing PCEA CHAIRETE SACCO as your preferred investment partner. "
            "You can count on our commitment to serve you. Your account details "
            "are as indicated below:\n"
             ))
            pdf.ln(3)  
            pdf.set_font("Times", size=12)
            pdf.multi_cell(0, 5, (
            f"Account Name: {name}\n"
            f"Account Number: {row.get('ACCOUNT NUMBER') or ''}"
             ))
            pdf.ln(3)  
            pdf.set_font("Times", size=12)
            pdf.multi_cell(0, 5, (
            f"Please indicate your member number {row.get('MEMBER NUMBER') or ''} for all transactions and instructions."
            "For any top ups kindly use the PCEA CHAIRETE SACCO with Co-op Bank "
            "Ongata Rongai Branch, A/c No. 01134211013100 or Mpesa Paybill number 400222 and "
            f"the account number is  412673#{row.get('MEMBER NUMBER') or ''}."
             ))
            pdf.ln(3)  
            pdf.set_font("Times", size=12)
            pdf.multi_cell(0, 5, (
            "For other requests, kindly send your request to pceabarakaparish@yahoo.com "
            f" also indicating your member number  {row.get('MEMBER NUMBER') or ''}."
             ))  
               
            # Sign-off
            pdf.ln(5)
            pdf.cell(0, 5, "Yours faithfully,", ln=True)

            # Insert stamp (7 cm × 2 cm)
            stamp_width = 70  # in mm
            stamp_height = 20  # in mm
            pdf.image("logo.png", x=10, y=pdf.get_y() + 5, w=stamp_width, h=stamp_height)
 
            pdf.ln(stamp_height + 15) # Add a small vertical space before the line
            pdf.set_line_width(0.5)  # Set line width
            pdf.line(pdf.get_x(), pdf.get_y(), pdf.w - 10, pdf.get_y())  # Draw a line           

            # Footer
 
            pdf.set_y(-45)
            pdf.set_font("Times",style="B", size=8) 
            pdf.cell(0, 5, "Growing Together", ln=True, align='C')            
            # Save PDF
            member_number = row.get("MEMBER NUMBER") or "unknown"
            pdf.output(f"{output_directory}\\{member_number}.pdf")

#if __name__ == "__main__":

