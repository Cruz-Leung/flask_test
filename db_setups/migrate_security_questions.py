import sqlite3

def migrate():
    """Add security question fields to customers table"""
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    
    # Check if columns already exist
    cursor.execute("PRAGMA table_info(customers)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'security_question' not in columns:
        cursor.execute("""
            ALTER TABLE customers 
            ADD COLUMN security_question TEXT
        """)
        print("✓ Added security_question column")
    
    if 'security_answer' not in columns:
        cursor.execute("""
            ALTER TABLE customers 
            ADD COLUMN security_answer TEXT
        """)
        print("✓ Added security_answer column")
    
    conn.commit()
    conn.close()
    print("✓ Security question migration complete")

if __name__ == '__main__':
    migrate()