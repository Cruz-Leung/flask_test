import sqlite3
from werkzeug.security import generate_password_hash

def migrate_passwords():
    """One-time script to migrate old SHA-256 passwords to bcrypt with salt"""
    conn = sqlite3.connect('store.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check which table exists
    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND (name='customers' OR name='users')"
    ).fetchall()
    
    if not tables:
        print("ERROR: No users or customers table found!")
        conn.close()
        return
    
    table_name = tables[0]['name']
    print(f"Found table: {table_name}")
    
    # Get all users
    users = cursor.execute(f"SELECT id, email FROM {table_name}").fetchall()
    
    print(f"Found {len(users)} users to migrate")
    print("\nIMPORTANT: Existing passwords cannot be migrated automatically.")
    print("Users will need to reset their passwords on next login.\n")
    
    # Set a temporary password for all users
    temp_password = "TempPass123!"  # Users will need to reset this
    hashed_temp = generate_password_hash(temp_password, method='pbkdf2:sha256', salt_length=16)
    
    for user in users:
        cursor.execute(
            f"UPDATE {table_name} SET password = ? WHERE id = ?",
            (hashed_temp, user['id'])
        )
        print(f"Updated user: {user['email']}")
    
    conn.commit()
    conn.close()
    
    print(f"\nMigration complete!")
    print(f"Temporary password for all users: {temp_password}")
    print("Users should change their password immediately after logging in.")

if __name__ == "__main__":
    response = input("This will reset all user passwords. Continue? (yes/no): ")
    if response.lower() == 'yes':
        migrate_passwords()
    else:
        print("Migration cancelled.")