import os
import re
import time
import psycopg2
from psycopg2.extras import execute_batch

# 1. Database and Path Configuration
DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "logs_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "secret123")
LOGS_DIR = os.getenv("LOGS_DIR", "server_logs")

# Regex to parse: "2026-08-17 08:15:22 ERROR Rate limit exceeded"
LOG_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+(?P<level>\w+)\s+(?P<message>.*)$"
)

# 2. Database Connection Loop
conn = None
for attempt in range(1, 11):
    try:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, connect_timeout=3
        )
        print("✓ Connected to PostgreSQL successfully!")
        break
    except psycopg2.OperationalError:
        print(f"Attempt {attempt}/10 - Waiting for DB...")
        time.sleep(2)

if not conn:
    raise Exception("Could not connect to database.")

cursor = conn.cursor()

# 3. Create Structured Table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS critical_errors (
        id SERIAL PRIMARY KEY,
        filename VARCHAR(255),
        timestamp TIMESTAMP,
        log_level VARCHAR(10),
        message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
conn.commit()

# 4. Parse Files and Collect Batch Records
records_to_insert = []

if os.path.exists(LOGS_DIR):
    for filename in os.listdir(LOGS_DIR):
        if filename.endswith(".log"):
            file_path = os.path.join(LOGS_DIR, filename)
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if "ERROR" in line:
                        match = LOG_PATTERN.match(line.strip())
                        if match:
                            data = match.groupdict()
                            records_to_insert.append((
                                filename,
                                data["timestamp"],
                                data["level"],
                                data["message"]
                            ))
                        else:
                            # Fallback if log format doesn't match regex exactly
                            records_to_insert.append((
                                filename,
                                None,
                                "ERROR",
                                line.strip()
                            ))

# 5. Execute Batch Insert
if records_to_insert:
    insert_query = """
        INSERT INTO critical_errors (filename, timestamp, log_level, message)
        VALUES (%s, %s, %s, %s);
    """
    execute_batch(cursor, insert_query, records_to_insert)
    conn.commit()
    print(f"✓ Successfully batch-inserted {len(records_to_insert)} structured log record(s)!")
else:
    print("No error logs found.")

cursor.close()
conn.close()
