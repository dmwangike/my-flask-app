import psycopg2

# Railway Postgres credentials
conn = psycopg2.connect(
    host='switchyard.proxy.rlwy.net',
    port='25459',
    dbname='railway',
    user='postgres',
    password='SetMrVNKCaThIproHaFQTBlRjLCiKwHU',
    sslmode='require'
)

cur = conn.cursor()

# Call your stored procedures
cur.execute("CALL update_due_loans();")
cur.execute("CALL collect_due_instalments();")

conn.commit()

cur.close()
conn.close()

