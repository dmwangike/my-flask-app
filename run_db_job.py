import psycopg2 
import os

def run_db_procedure():
    try:
        # Use Railway-provided environment variables
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()

        # Call your stored procedures
        cur.execute("CALL update_due_loans();")
        cur.execute("CALL insert_balance_snapshot();")
        conn.commit()
        cur.close()
        conn.close()
        print("Procedure executed successfully.")
    except Exception as e:
        print(f"Error executing procedure: {e}")

if __name__ == "__main__":
    run_db_procedure()
