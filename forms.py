from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField,DecimalField,  SubmitField, BooleanField,PasswordField,validators,FloatField,DateField, SelectField,IntegerField
from wtforms.validators import DataRequired,NumberRange, Length, EqualTo ,Email, ValidationError,InputRequired,Optional
from datetime import datetime
from flask import current_app
from decimal import Decimal


   
import os
import psycopg2
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
 
 
class LoanForm(FlaskForm):
    member_number = StringField('Member Number', validators=[DataRequired()])
    member_name = StringField('Member Name', render_kw={"readonly": True})
    balance = DecimalField('Current Balance', render_kw={"readonly": True})
    amount_borrowed = DecimalField('Amount Borrowed', validators=[DataRequired()])
    loan_tenure = IntegerField('Loan Tenure (months)', validators=[DataRequired()])
    submit = SubmitField('Submit')


class CustDetailForm(FlaskForm):
    cname = StringField('MEMBER_NAME',
                        validators=[DataRequired(), Length(min=2, max=100)])
    cuniqueid = StringField('ID_NO',
                            validators=[DataRequired(), Length(min=2, max=100)])
    ctaxid = StringField('TAX_CERT')
    ctax = BooleanField('TAX_EXEMPT')                         
    cphone = StringField('CUST_PHONE',
                         validators=[DataRequired(), Length(min=2, max=100)])
    cemail = StringField('CUST_EMAIL',
                         validators=[DataRequired(), Length(min=2, max=100)]) 
    cgender = SelectField(
        'GENDER/ORG_TYPE',
        validators=[DataRequired()],
        choices=[
            ('male', 'Male'),
            ('female', 'Female'),
            ('joint', 'Joint'),
            ('organization', 'Organization')
        ],
        coerce=str  # Ensures the selected value is returned as a string
)
    cdob = DateField('DOB/REG', format='%Y-%m-%d')                     
    submit = SubmitField('Submit')  




class editBNKForm(FlaskForm):

    cmemberid = StringField('MEMBER_NO',
                            validators=[DataRequired(), Length(min=2, max=100)])
    cname = StringField('CUSTOMER',
                             validators=[DataRequired(), Length(min=2, max=200)], render_kw={"readonly": True})
    ccustno = StringField('MNO',
                             validators=[DataRequired(), Length(min=2, max=200)], render_kw={"readonly": True}) 
    cacct = StringField('CUST_ACCT',
                           validators=[DataRequired(), Length(min=2, max=100)])

    cbank = SelectField('CUST_BANK',
                        validators=[DataRequired()],
                        choices=[],  # Placeholder for choices
                        coerce=str)  # Ensures the selected value is a string

    cbranch = StringField('CUST_BRANCH',
                          validators=[DataRequired(), Length(min=2, max=100)])
                        
    submit = SubmitField('Submit')  

    def populate_cust(self):
        conn = get_db_connect()  # Function to get DB connection
        cursor = conn.cursor()
        
        query = """
        SELECT cust_name, membership_number
        FROM MEMBERS 
	WHERE  membership_number = %s
        """
        cursor.execute(query, (self.cmemberid.data,))

        result = cursor.fetchone()
        if result:
            self.cname.data = result[0]  
            self.ccustno.data = result[1]  
        
        cursor.close()
        conn.close()
        
        
        


class editKYCForm(FlaskForm):

    cmemberid = StringField('MEMBER_NO',
                            validators=[DataRequired(), Length(min=2, max=100)])
    cname = StringField('CUSTOMER',
                             validators=[DataRequired(), Length(min=2, max=200)], render_kw={"readonly": True})
    ccustno = StringField('CUSTOMER_NUMBER',
                             validators=[DataRequired(), Length(min=1, max=200)], render_kw={"readonly": True}) 
    ctax = SelectField('TAX_EXEMPT', choices=[('true', 'True'), ('false', 'False')])

    cstatus = SelectField('CUSTOMER_STATUS', choices=[('active', 'Active'), ('inactive', 'Inactive'), ('suspended', 'Suspended'), ('exited', 'Exited')])

    
    submit = SubmitField('Submit')  

    def populate_cust(self):
        conn = get_db_connect()  # Function to get DB connection
        cursor = conn.cursor()
        
        query = """
        select cust_name, membership_number,lower(tax_exempt) as tax_exempt,lower(membership_status) as membership_status
        from MEMBERS 
        WHERE membership_number = %s
        """
        cursor.execute(query, (self.cmemberid.data,))

        result = cursor.fetchone()
        if result:
            self.cname.data = result[0]  
            self.ccustno.data = result[1]  

            
            # TAX_EXEMPT
            if result[2] not in [choice[0] for choice in self.ctax.choices]:
                self.ctax.choices.append((result[2], result[2].capitalize()))
            self.ctax.data = result[2]

            # MEMBERSHIP_STATUS
            if result[3] not in [choice[0] for choice in self.cstatus.choices]:
                self.cstatus.choices.append((result[3], result[3].capitalize()))
            self.cstatus.data = result[3]

        cursor.close()
        conn.close()
        
        
 

class cusdKYCForm(FlaskForm):
 
     cmemberid = StringField('MEMBER_NO',
                             validators=[DataRequired(), Length(min=2, max=100)])
     cname = StringField('CUSTOMER',
                              validators=[DataRequired(), Length(min=2, max=200)], render_kw={"readonly": True})
     ccustno = StringField('CUSTOMER_ID',
                              validators=[DataRequired(), Length(min=1, max=200)], render_kw={"readonly": True}) 
     cphone = StringField('PHONE_NUMBER',
                              validators=[DataRequired(), Length(min=1, max=200)], render_kw={"readonly": True}) 
     cemail = StringField('CUSTOMER_EMAIL',
                              validators=[DataRequired(), Length(min=1, max=200)], render_kw={"readonly": True}) 
     ccongr = StringField('CONGREGATION',
                              validators=[DataRequired(), Length(min=1, max=200)], render_kw={"readonly": True})   
 
     def populate_cust(self):
         conn = get_db_connect()  # Function to get DB connection
         cursor = conn.cursor()
         
         query = """
         SELECT cust_name, identification, pref_phone,pref_email,congregation 
         from MEMBERS 
         WHERE membership_number = %s
         """
         cursor.execute(query, (self.cmemberid.data,))
 
         result = cursor.fetchone()
         if result:
             self.cname.data = result[0]  
             self.ccustno.data = result[1]  
             self.cphone.data = result[2]  
             self.cemail.data = result[3] 
             self.ccongr.data = result[4]              
 
         cursor.close()
         conn.close()
 
 
 
 
 
 
 
        
class editRTDForm(FlaskForm):

    r_id = StringField('PARTY_ID')
    cname = StringField('MEMBER',
                              render_kw={"readonly": True})
    cmemberid = StringField('MEMBER_NUMBER',
                           render_kw={"readonly": True}) 
    rname = StringField('PARTY_NAME',
                           render_kw={"readonly": True}) 
    rphone = StringField('PARTY_PHONE')
    remail = StringField('PARTY_EMAIL')
    
    rrole = SelectField('PARTY_ROLE', validators=[DataRequired()],choices=[('signatory', 'Signatory'),('next_of_kin', 'Next of Kin'),('beneficiary', 'Beneficiary')],coerce=str  )
    rstatus = SelectField('PARTY_STATUS', choices=[('active', 'Active'), ('inactive', 'Inactive'), ('suspended', 'Suspended'), ('exited', 'Exited')])

    
    submit = SubmitField('Submit')  

    def populate_cust(self):
        conn = get_db_connect()  # Function to get DB connection
        cursor = conn.cursor()
        
        query = """
        select partyid,membership_number,cust_name, party_name, party_phone, party_email,party_role,party_status 
        from related_party a join MEMBERS b USING(membership_number)
        WHERE partyid = %s
        """
        cursor.execute(query, (self.r_id.data,))

        result = cursor.fetchone()
        if result:
            self.r_id.data = result[0]  
            self.cmemberid.data = result[1]  
            self.cname.data = result[2]  
            self.rname.data = result[3]              
            self.rphone.data = result[4] 
            self.remail.data = result[5]
            # ROLE
            if result[6] not in [choice[0] for choice in self.rrole.choices]:
                self.rrole.choices.append((result[6], result[6].capitalize()))
            self.rrole.data = result[6]            
            # STATUS
            if result[7] not in [choice[0] for choice in self.rstatus.choices]:
                self.rstatus.choices.append((result[7], result[7].capitalize()))
            self.rstatus.data = result[7]

        cursor.close()
        conn.close()
        
        
        
        
                

        
# Function to populate cbank dropdown from bank.txt
def populate_bank_choices(form):
    # Read the bank names from the "bank.txt" file
    try:
        with open('bank.txt', 'r') as file:
            banks = [line.strip() for line in file.readlines()]
        # Adding an empty choice as the first option (useful for an unselected option)
        form.cbank.choices = [('', 'Select Bank')] + [(bank, bank) for bank in banks]
    except FileNotFoundError:
        form.cbank.choices = [('', 'No banks available')]






class EnrichForm(FlaskForm):
    cmemberid = StringField('MEMBER_ID')
    cname = StringField('CUST_NAME',
                        validators=[DataRequired(), Length(min=2, max=100)], render_kw={"readonly": True})


    cpostadd = StringField('POSTAL_ADDRESS')
    cpostcode = StringField('POSTAL_CODE')
    ccity = StringField('CITY')    
    coccu = StringField('OCCUPATION/BUSINESS')
    ccongr = SelectField(
        'CONGREGATION',
        validators=[DataRequired()],
        choices=[
            ('upendo', 'Upendo'),
            ('nkaimurunya', 'Nkaimurunya'),
            ('ongata', 'Ongata'),            
            ('macedonia', 'Macedonia'), 
            ('others', 'Others')
        ],
        coerce=str  # Ensures the selected value is returned as a string
)
    cresd = StringField('RESIDENCE')    
    submit = SubmitField('Submit')

    def populate_cname(self):
        """Populate the cname field based on the cuniqueid from the database."""
        conn = get_db_connect()  # Function to get DB connection
        cursor = conn.cursor()
        
        # Query to get the customer name
        query = "SELECT cust_name FROM MEMBERS WHERE membership_number = %s"
        cursor.execute(query, (self.cmemberid.data,))
        
        result = cursor.fetchone()
        if result:
            self.cname.data = result[0]  # Assuming the first column is the cust_name
        
        cursor.close()
        conn.close()
        
        
class UpdateTRXForm(FlaskForm):
    cmemberid = StringField('MEMBER_NO')
    cname = StringField('NAME',
                       render_kw={"readonly": True})

    ctranid = StringField('NARRATION')

    camount = DecimalField(
        'AMOUNT',
        places=2,  
        rounding=None,
    )

    submit = SubmitField('Submit')

    def populate_trx(self):
        conn = get_db_connect()  # Function to get DB connection
        cursor = conn.cursor()
        
        # Query to get Transaction Details
        query = """
        select cust_name from MEMBERS where membership_number = %s
        """
        cursor.execute(query, (self.cmemberid.data,))
        
        result = cursor.fetchone()
        if result:
            self.cname.data = result[0] 
        
        cursor.close()
        conn.close()        
        
        
        
class custWDRForm(FlaskForm):
    cuniqueid = StringField('ACCOUNT_NO')
    ccustomer = StringField('CUSTOMER',
                             validators=[DataRequired(), Length(min=2, max=200)], render_kw={"readonly": True})
    cbalance = StringField('ACCOUNT BALANCE', render_kw={"readonly": True})  
    camountw = StringField('WITHDRAWAL')  
    cnarration = StringField('COMMENT')

    submit = SubmitField('Submit')

    def populate_trx(self):
        conn = get_db_connect()  # Function to get DB connection
        cursor = conn.cursor()
        
        query = """
        SELECT cust_name, balance from clients join portfolio using(customer_id)
        WHERE account_no = %s
        """
        cursor.execute(query, (self.cuniqueid.data,))

        result = cursor.fetchone()
        if result:
            self.ccustomer.data = result[0]  
            self.cbalance.data = result[1]  

        cursor.close()
        conn.close()




class amendCNTForm(FlaskForm):
    cmemberid = StringField('MEMBER_NO')
    cname = StringField('CUSTOMER',
                             validators=[DataRequired(), Length(min=2, max=200)], render_kw={"readonly": True})
    ccustno = StringField('CUSTOMER_NUMBER',
                             validators=[DataRequired(), Length(min=1, max=200)], render_kw={"readonly": True})                             
    cphone = StringField('PREFERRED_PHONE')  
    cemail = StringField('PREFERRED_EMAIL')  
    caddress = StringField('ADDRESS')
    czip = StringField('POST_CODE')
    ccity = StringField('CITY')
    
    submit = SubmitField('Submit')

    def populate_contact(self):
        conn = get_db_connect()  # Function to get DB connection
        cursor = conn.cursor()
        
        query = """
        select cust_name,membership_number, pref_phone, pref_email, post_address, post_code, city
        from MEMBERS
        WHERE membership_number = %s
        """
        cursor.execute(query, (self.cmemberid.data,))

        result = cursor.fetchone()
        if result:
            self.cname.data = result[0]  
            self.ccustno.data = result[1]  
            self.cphone.data = result[2]  
            self.cemail.data = result[3]  
            self.caddress.data = result[4]  
            self.czip.data = result[5] 
            self.ccity.data = result[6]  

        cursor.close()
        conn.close()





    
class LoginForm(FlaskForm):
     user_name_pid = StringField('', [validators. InputRequired()],
                                    render_kw={'autofocus': True, 'placeholder': 'Enter User'})
    
     user_pid_Password = PasswordField('', [validators. InputRequired()],
                                      render_kw={'autofocus': True, 'placeholder': 'Enter your login Password'})
                                      
                                      
class PageSelectionForm(FlaskForm):
    page_selection = SelectField(
        'Select Page', 
        choices=[('amend_cust_contacts', 'Edit Member Contacts'), ('edit_bnk_details', 'Edit Bank Details'), ('edit_kyc_details', 'Edit Members KYC Details'), ('add_related_party', 'Add Related Party'), ('edit_related_party', 'Edit Related Party'), ('assign_beneficiary_allocations', 'Assign Beneficiary Allocations')],
        validators=[DataRequired()]
    ) 
    
class HolsForm(FlaskForm):
    cstartd = DateField('START_DATE', format='%Y-%m-%d')
    cendd = DateField('END_DATE', format='%Y-%m-%d', validators=[Optional()])
    cname = StringField('HOLIDAY')
   
    submit = SubmitField('Submit')    

class ReportsForm(FlaskForm):

    submit = SubmitField('End Month Statements')
    submit1 = SubmitField('Daily Purchase Transactions')
    submit2 = SubmitField('Annual Review Fee Collection')  



                                      
class CMSForm(FlaskForm):

    submit = SubmitField('Annual Review Fee Reversed')
    submit1 = SubmitField('Annual Review Fee Assessment')
    submit2 = SubmitField('Annual Review Fee Collection')    
    
class BeneficiaryForm(FlaskForm):
    member_number = StringField('MEMBER_NUMBER', validators=[DataRequired()])
    member_name = StringField('MEMBER_NAME', render_kw={"readonly": True})
    submit = SubmitField('Submit')    
    
class addRTDForm(FlaskForm):
    cmemberid = StringField('MEMBER_NO')
    cname = StringField('CUSTOMER',
                              render_kw={"readonly": True})
    rname = StringField('PARTY_NAME')
    ridentification = StringField('PARTY_ID')
    rphone = StringField('PARTY_PHONE')  
    remail = StringField('PARTY_EMAIL')  
    rrole = SelectField(
        'PARTY_ROLE',
        validators=[DataRequired()],
        choices=[
            ('signatory', 'Signatory'),
            ('next_of_kin', 'Next of Kin'),
            ('beneficiary', 'Beneficiary')
        ],
        coerce=str  # Ensures the selected value is returned as a string
)
  
    submit = SubmitField('Submit')

    def populate_contact(self):
        conn = get_db_connect()  # Function to get DB connection
        cursor = conn.cursor()
        
        query = """
        select cust_name,membership_number
        from MEMBERS
        WHERE membership_number = %s
        """
        cursor.execute(query, (self.cmemberid.data,))

        result = cursor.fetchone()
        if result:
            self.cname.data = result[0]  


        cursor.close()
        conn.close()
        
        
        
        
        
class cusdLONForm(FlaskForm):
 
     cmemberid = StringField('MEMBER_NO',
                             validators=[DataRequired(), Length(min=2, max=100)])
     cname = StringField('CUSTOMER',
                              validators=[DataRequired(), Length(min=2, max=200)], render_kw={"readonly": True})
     lonact = StringField('LOAN_ACCT',
                              validators=[DataRequired(), Length(min=1, max=200)], render_kw={"readonly": True}) 
     lonamt = StringField('LOAN_AMOUNT',
                              validators=[DataRequired(), Length(min=1, max=200)], render_kw={"readonly": True}) 
     depact = StringField('DEPOSIT_ACCT',
                              validators=[DataRequired(), Length(min=1, max=200)], render_kw={"readonly": True}) 
     depamt = StringField('DEPOSIT_AMOUNT',
                              validators=[DataRequired(), Length(min=1, max=200)], render_kw={"readonly": True})   
     intact = StringField('INTEREST_ACCT',
                              validators=[DataRequired(), Length(min=1, max=200)], render_kw={"readonly": True}) 
     intamt = StringField('INTEREST_AMOUNT',
                              validators=[DataRequired(), Length(min=1, max=200)], render_kw={"readonly": True})   
     def populate_cust(self):
         conn = get_db_connect()  # Function to get DB connection
         cursor = conn.cursor()
         
         query = """
    SELECT 
        cust_name,
        a.account_no AS deposit_account,
        a.balance AS deposits,
        COALESCE(b.loan_account, 'None') AS loan_account,
        COALESCE(b.pending_amount, 0) AS loan,
        COALESCE(c.interest_account, 'None') AS interest_account,
        COALESCE(c.interest_due, 0) AS interest
    FROM portfolio a JOIN MEMBERS m on m.membership_number =  a.membership_number
    LEFT OUTER JOIN loan_accounts b 
        ON b.member_number = a.membership_number AND b.pending_amount <> 0
    LEFT OUTER JOIN interest_accounts c 
        ON c.membership_number = a.membership_number AND c.interest_due <> 0
    WHERE a.account_type = 'Deposits' and a.membership_number = %s
         """
         cursor.execute(query, (self.cmemberid.data,))
 
         result = cursor.fetchone()
         if result:
             self.cname.data = result[0]  
             self.depact.data = result[1]  
             self.depamt.data = result[2]  
             self.lonact.data = result[3] 
             self.lonamt.data = result[4]              
             self.intact.data = result[5] 
             self.intamt.data = result[6] 
         cursor.close()
         conn.close()
 