import psycopg2
import os
import datetime

def run_db_procedure():
    print(f"Starting DB job at {datetime.datetime.now()}")
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor()
        cur.execute("CALL update_due_loans();")
        cur.execute("CALL insert_balance_snapshot();")
        conn.commit()
        cur.close()
        conn.close()
        print("Procedures executed successfully.")
    except Exception as e:
        print(f"Error executing procedure: {e}")

if __name__ == "__main__":
    run_db_procedure()
