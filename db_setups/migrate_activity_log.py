import sqlite3

def migrate():
    """Add activity_log table to existing database"""
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    
    # Check if table already exists
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='activity_log'
    """)
    
    if cursor.fetchone():
        print("✓ activity_log table already exists")
        conn.close()
        return
    
    # Create activity_log table
    cursor.execute("""
        CREATE TABLE activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            user_name TEXT NOT NULL,
            user_role TEXT NOT NULL,
            action TEXT NOT NULL,
            product_id INTEGER,
            product_sku TEXT,
            product_name TEXT,
            details TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("✓ Successfully created activity_log table")

if __name__ == '__main__':
    migrate()