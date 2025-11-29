import sqlite3
import os


def check_db():
    db_path = "maxflash.db"
    if not os.path.exists(db_path):
        print(f"Database file {db_path} does not exist!")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Tables in {db_path}:")
        for table in tables:
            print(f"- {table[0]}")
        conn.close()
    except Exception as e:
        print(f"Error reading database: {e}")


if __name__ == "__main__":
    check_db()
