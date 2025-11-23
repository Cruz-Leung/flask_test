import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = "store.db"  # Update if your DB file is named differently
EMAIL = "cruzleung@gmail.com"
NEW_PASSWORD = "Cruzleung09#"  # Change to your desired password

def main():
    conn = sqlite3.connect(DB_PATH)
    hashed = generate_password_hash(NEW_PASSWORD, method='pbkdf2:sha256', salt_length=16)
    cur = conn.cursor()
    cur.execute(
        "UPDATE customers SET password = ? WHERE email = ? AND role = 'manager'",
        (hashed, EMAIL)
    )
    conn.commit()
    conn.close()
    print("✅ Manager password updated and hashed.")

if __name__ == "__main__":
    main()