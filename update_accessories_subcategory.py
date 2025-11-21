import sqlite3

def update_accessories_subcategories():
    """Add subcategories to accessories products"""
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    
    print("Updating accessories subcategories...\n")
    
    # Update brewing equipment
    cursor.execute("""
        UPDATE products 
        SET subcategory = 'brewing-equipment' 
        WHERE category = 'accessories' AND (
            name LIKE '%tamper%' OR 
            name LIKE '%pitcher%' OR 
            name LIKE '%scale%' OR 
            name LIKE '%cup%' OR
            name LIKE '%mug%' OR
            name LIKE '%jug%' OR
            name LIKE '%knock%' OR
            name LIKE '%cloth%'
        )
    """)
    brewing_count = cursor.rowcount
    print(f"✅ Updated {brewing_count} products to 'brewing-equipment'")
    
    # Update grinders
    cursor.execute("""
        UPDATE products 
        SET subcategory = 'grinders' 
        WHERE category = 'accessories' AND (
            name LIKE '%grinder%' OR 
            name LIKE '%burr%' OR
            name LIKE '%mill%'
        )
    """)
    grinders_count = cursor.rowcount
    print(f"✅ Updated {grinders_count} products to 'grinders'")
    
    # Show any accessories without subcategory
    cursor.execute("""
        SELECT id, name, subcategory 
        FROM products 
        WHERE category = 'accessories' AND (subcategory IS NULL OR subcategory = '')
    """)
    uncategorized = cursor.fetchall()
    
    if uncategorized:
        print(f"\n⚠️  {len(uncategorized)} accessories still need subcategories:")
        for product in uncategorized:
            print(f"   - ID {product[0]}: {product[1]}")
        print("\nYou may need to manually assign these in the database.")
    else:
        print("\n✅ All accessories have subcategories!")
    
    # Verify the updates
    cursor.execute("""
        SELECT subcategory, COUNT(*) 
        FROM products 
        WHERE category = 'accessories' 
        GROUP BY subcategory
    """)
    summary = cursor.fetchall()
    
    print("\n📊 Accessories Summary:")
    for row in summary:
        subcat = row[0] if row[0] else "(none)"
        count = row[1]
        print(f"   {subcat}: {count} products")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Migration complete!")

if __name__ == "__main__":
    response = input("Update accessories subcategories? (yes/no): ")
    if response.lower() == 'yes':
        update_accessories_subcategories()
    else:
        print("Migration cancelled.")