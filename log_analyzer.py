import os
import time
import psycopg2

# 1. קריאת הגדרות ההתחברות (שם המארח 'db' הוא שם ה-Service ב-Docker Compose)
DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "logs_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "secret123")

# 2. מנגנון Retry להמתנה עד שבסיס הנתונים יעלה ויקבל חיבורים
conn = None
for _ in range(10):
    try:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS
        )
        print("✓ Connected to PostgreSQL successfully!")
        break
    except psycopg2.OperationalError:
        print("Waiting for database to be ready...")
        time.sleep(2)

if not conn:
    raise Exception("Could not connect to database.")

cursor = conn.cursor()

# 3. יצירת טבלה במידה ולא קיימת
cursor.execute("""
    CREATE TABLE IF NOT EXISTS critical_errors (
        id SERIAL PRIMARY KEY,
        filename VARCHAR(255),
        log_line TEXT
    );
""")
conn.commit()

# 4. יצירת התיקייה וקבצי ה-Log לדוגמה
folder_name = "server_logs"
os.makedirs(folder_name, exist_ok=True)
sample_files = {
    "app.log": "2026-08-10 ERROR Database connection timeout.\n2026-08-10 INFO System healthy.\n",
    "error.log": "2026-08-11 ERROR Disk limit exceeded.\n"
}
for filename, content in sample_files.items():
    with open(os.path.join(folder_name, filename), "w", encoding="utf-8") as f:
        f.write(content)

# 5. ניתוח והכנסה לבסיס הנתונים
inserted_count = 0
for filename in os.listdir(folder_name):
    if filename.endswith(".log"):
        file_path = os.path.join(folder_name, filename)
        with open(file_path, "r", encoding="utf-8") as in_f:
            for line in in_f:
                if "ERROR" in line:
                    cursor.execute(
                        "INSERT INTO critical_errors (filename, log_line) VALUES (%s, %s);",
                        (filename, line.strip())
                    )
                    inserted_count += 1
                if "INFO" in line:
                    info_count += 1

conn.commit()
print(f"✓ Inserted {inserted_count} error logs into PostgreSQL database!")
print(f"There's {info_count} lines of info")
cursor.close()
conn.close()
