import os
import time
import psycopg2

# 1. Read connection configuration and target directory
DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "logs_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "secret123")
LOGS_DIR = os.getenv("LOGS_DIR", "server_logs")

# 2. Database Connection Retry Mechanism
conn = None
print(f"Connecting to PostgreSQL host '{DB_HOST}'...")

for attempt in range(1, 11):
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            connect_timeout=3
        )
        print("✓ Connected to PostgreSQL successfully!")
        break
    except psycopg2.OperationalError as e:
        print(f"Attempt {attempt}/10 - Waiting for database to be ready...")
        time.sleep(2)

if not conn:
    raise Exception("Could not connect to PostgreSQL database after 10 attempts.")

cursor = conn.cursor()

# 3. Create table if it doesn't exist
cursor.execute("""
    CREATE TABLE IF NOT EXISTS critical_errors (
        id SERIAL PRIMARY KEY,
        filename VARCHAR(255),
        log_line TEXT
    );
""")
conn.commit()

# 4. Verify target log directory exists
if not os.path.exists(LOGS_DIR):
    raise FileNotFoundError(
        f"Error: Target directory '{LOGS_DIR}' does not exist inside the container. "
        f"Ensure './server_logs' exists on your host machine."
    )

print(f"Scanning directory '{LOGS_DIR}' for .log files...")

# 5. Parse log files and insert errors into database
inserted_count = 0
for filename in os.listdir(LOGS_DIR):
    if filename.endswith(".log"):
        file_path = os.path.join(LOGS_DIR, filename)
        
        with open(file_path, "r", encoding="utf-8", errors="ignore") as in_f:
            for line in in_f:
                if "ERROR" in line:
                    cursor.execute(
                        "INSERT INTO critical_errors (filename, log_line) VALUES (%s, %s);",
                        (filename, line.strip())
                    )
                    inserted_count += 1

conn.commit()
print(f"✓ Inserted {inserted_count} error log(s) into PostgreSQL database from '{LOGS_DIR}'!")

cursor.close()
conn.close()
