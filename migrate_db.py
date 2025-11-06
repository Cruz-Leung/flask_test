import sqlite3

def migrate_database():
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    
    # List of migrations to run
    migrations = [
        # Add new columns to customers table
        "ALTER TABLE customers ADD COLUMN city TEXT",
        "ALTER TABLE customers ADD COLUMN state TEXT",
        "ALTER TABLE customers ADD COLUMN postcode TEXT",
        "ALTER TABLE customers ADD COLUMN country TEXT DEFAULT 'AU'",
        
        # Add new columns to orders table
        "ALTER TABLE orders ADD COLUMN payment_method TEXT DEFAULT 'card'",
        "ALTER TABLE orders ADD COLUMN shipping_address TEXT",
    ]
    
    for migration in migrations:
        try:
            cursor.execute(migration)
            print(f"✅ Success: {migration[:50]}...")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"⚠️  Column already exists, skipping: {migration[:50]}...")
            else:
                print(f"❌ Error: {e}")
                print(f"   Failed migration: {migration}")
    
    conn.commit()
    conn.close()
    print("\n✅ Database migration completed!")

if __name__ == '__main__':
    migrate_database()