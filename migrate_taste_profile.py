import sqlite3

def migrate_taste_profile():
    """Add taste profile columns to products table"""
    
    # Connect to your database
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    
    print("🔄 Starting taste profile migration...")
    
    # Check if columns exist
    cursor.execute("PRAGMA table_info(products)")
    columns = [column[1] for column in cursor.fetchall()]
    
    # Add taste profile columns if they don't exist
    if 'taste_sweetness' not in columns:
        cursor.execute("ALTER TABLE products ADD COLUMN taste_sweetness INTEGER DEFAULT NULL")
        print("✅ Added taste_sweetness column")
    else:
        print("ℹ️  taste_sweetness column already exists")
    
    if 'taste_aroma' not in columns:
        cursor.execute("ALTER TABLE products ADD COLUMN taste_aroma INTEGER DEFAULT NULL")
        print("✅ Added taste_aroma column")
    else:
        print("ℹ️  taste_aroma column already exists")
    
    if 'taste_body' not in columns:
        cursor.execute("ALTER TABLE products ADD COLUMN taste_body INTEGER DEFAULT NULL")
        print("✅ Added taste_body column")
    else:
        print("ℹ️  taste_body column already exists")
    
    # Commit changes
    conn.commit()
    
    # Verify the migration
    cursor.execute("PRAGMA table_info(products)")
    all_columns = [column[1] for column in cursor.fetchall()]
    
    print("\n📊 Current products table columns:")
    for col in all_columns:
        print(f"   - {col}")
    
    conn.close()
    print("\n✅ Migration completed successfully!")

if __name__ == "__main__":
    migrate_taste_profile()