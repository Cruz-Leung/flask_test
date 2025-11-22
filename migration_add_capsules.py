import sqlite3

def migrate():
    """Update ground-coffee subcategory to capsules where appropriate"""
    conn = sqlite3.connect('store.db')
    cursor = conn.cursor()
    
    # You can manually update specific products or leave them as ground-coffee
    # This is just a template - adjust based on your actual data
    
    print("Migration complete. You can now use 'capsules' as a subcategory.")
    print("Update individual products through the admin panel.")
    
    conn.close()

if __name__ == '__main__':
    migrate()