import os
import glob
import psycopg2

# 1. קריאת משתני סביבה מ-docker-compose
DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "logs_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "secret123")

def main():
    # 2. התחברות ל-PostgreSQL
    print("Connecting to PostgreSQL...")
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    cursor = conn.cursor()

    # 3. יצירת הטבלה במידה ולא קיימת
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS critical_errors (
            id SERIAL PRIMARY KEY,
            filename VARCHAR(255),
            log_line TEXT
        );
    """)
    conn.commit()

    # 4. סריקת כל קבצי ה-log בתיקייה server_logs (או בתיקייה הנוכחית)
    log_files = glob.glob("server_logs/*.log") + glob.glob("*.log")
    
    if not log_files:
        print("No log files found.")
        return

    for file_path in log_files:
        filename = os.path.basename(file_path)
        info_count = 0

        print(f"Processing file: {filename}")
        
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                
                # בדיקת שורות ERROR והכנסתן ל-DB
                if "ERROR" in line_str:
                    cursor.execute(
                        "INSERT INTO critical_errors (filename, log_line) VALUES (%s, %s);",
                        (filename, line_str)
                    )
                
                # ספירת שורות INFO
                if "INFO" in line_str:
                    info_count += 1

        # הכנסת סיכום שורות ה-INFO ל-DB עבור הקובץ הנוכחי
        info_summary_line = f"The number of INFO lines are: {info_count}"
        cursor.execute(
            "INSERT INTO critical_errors (filename, log_line) VALUES (%s, %s);",
            (filename, info_summary_line)
        )

        # ביצוע COMMIT קריטי לשמירת השינויים ב-Database!
        conn.commit()
        print(f"Finished {filename}: Saved ERRORs and INFO summary ({info_summary_line}).")

    cursor.close()
    conn.close()
    print("Log analysis complete successfully!")

if __name__ == "__main__":
    main()
