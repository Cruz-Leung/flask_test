import sqlite3
import os
from pathlib import Path
import argparse
import hashlib

BASEDIR = Path(__file__).parent
DB_PATH = BASEDIR / "store.db"

# Database creation SQL
CREATE_CUSTOMERS = """
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    phone TEXT,
    address TEXT,
    role TEXT DEFAULT 'customer' CHECK(role IN ('customer', 'admin', 'manager')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_PRODUCTS = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    sku TEXT UNIQUE,
    category TEXT NOT NULL,
    subcategory TEXT,
    description TEXT,
    price REAL NOT NULL,
    stock INTEGER DEFAULT 0,
    image TEXT,
    brand TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_ORDERS = """
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    status TEXT DEFAULT 'pending',
    total REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE SET NULL
);
"""

CREATE_ORDER_ITEMS = """
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE RESTRICT
);
"""

CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand);
CREATE INDEX IF NOT EXISTS idx_products_subcategory ON products(subcategory);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_customers_role ON customers(role);
"""

# Sample products for beans and accessories
SAMPLE_PRODUCTS = [
    # Beans
    ("House Blend 1kg", "B-HOUSE-001", "beans", None, "Medium roast - chocolate & citrus notes", 24.50, 50, "beans1.jpg", "Cruzy Coffee"),
    ("Single Origin Colombia 250g", "B-COL-002", "beans", None, "Light-medium roast, bright acidity", 12.00, 80, "beans2.jpg", "Cruzy Coffee"),
    ("Dark Roast Espresso 250g", "B-ESP-003", "beans", None, "Rich, full-bodied dark roast", 11.00, 40, "beans3.jpg", "Cruzy Coffee"),
    # Accessories
    ("Precision Grinder", "A-GRID-001", "accessories", None, "Consistent grind for every brew", 199.00, 15, "accessory1.jpg", "Cruzy Coffee"),
    ("Barista Tamper", "A-TAMP-002", "accessories", None, "Stainless steel tamper with calibration", 39.00, 60, "accessory2.jpg", "Cruzy Coffee"),
    ("Milk Frothing Pitcher 600ml", "A-PITCH-003", "accessories", None, "Professional stainless pitcher", 29.50, 75, "accessory3.jpg", "Cruzy Coffee"),
]

# Semi-automatic machine brands and models
MACHINE_BRANDS = {
    "Breville": {
        "models": ["Bambino Plus", "Bambino", "Barista Express", "Barista Express Impress", 
                  "Barista Pro", "Dual Boiler", "Infuser", "Oracle Touch", "Barista Touch"],
        "base_price": 799.00
    },
    "DeLonghi": {
        "models": ["Dedica Arte EC885M", "Dedica EC685M", "La Specialista Arte", 
                  "La Specialista Prestigio", "La Specialista Maestro", "ECP3420", 
                  "Stilosa EC260", "EC9335M La Specialista", "EC9155M"],
        "base_price": 599.00
    },
    "Rocket Espresso": {
        "models": ["Appartamento", "Appartamento TCA", "Giotto Type V", 
                  "Mozzafiato Cronometro R", "R58 Cinquantotto", "R Nine One"],
        "base_price": 1699.00
    }
}

def hash_password(password):
    """Hash a password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables(conn):
    cur = conn.cursor()
    cur.executescript(
        "\n".join([
            CREATE_CUSTOMERS,
            CREATE_PRODUCTS,
            CREATE_ORDERS,
            CREATE_ORDER_ITEMS,
            CREATE_INDEXES
        ])
    )
    conn.commit()
    print("✅ Tables created/verified")

def seed_products(conn, force=False):
    cur = conn.cursor()
    
    # Check existing products
    existing_count = cur.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    
    if existing_count > 0 and not force:
        print(f"ℹ️  Found {existing_count} existing products. Use --force to add anyway.")
    
    added = 0
    skipped = 0
    
    # Insert basic products (beans & accessories)
    for product in SAMPLE_PRODUCTS:
        try:
            cur.execute("""
                INSERT INTO products 
                (name, sku, category, subcategory, description, price, stock, image, brand) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, product)
            added += 1
        except sqlite3.IntegrityError:
            skipped += 1
    
    # Insert machine products
    for brand, info in MACHINE_BRANDS.items():
        base_price = info["base_price"]
        for i, model in enumerate(info["models"], 1):
            name = f"{brand} {model}"
            sku = f"M-{brand[:3].upper()}{i:03d}"
            price = base_price * (1 + (i % 5) * 0.1)
            
            try:
                cur.execute("""
                    INSERT INTO products 
                    (name, sku, category, subcategory, description, price, stock, image, brand) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    name, 
                    sku,
                    "machines",
                    "semi-auto",
                    f"Semi-automatic espresso machine from {brand}",
                    price,
                    5,
                    f"machine_{brand.lower()}_{i}.jpg",
                    brand
                ))
                added += 1
            except sqlite3.IntegrityError:
                skipped += 1
    
    conn.commit()
    print(f"✅ Products: {added} added, {skipped} skipped (already exist)")

def seed_users(conn, force=False):
    """Create default users with different roles"""
    cur = conn.cursor()
    
    users = [
        ("Cruzy", "cruzleung@gmail.com", "Cruzyc09#", "0400000001", "1 Manager St", "manager"),
        ("Admin User", "admin@cruzy.com", "admin123", "0400000002", "2 Admin Ave", "admin"),
        ("Test Customer", "test@example.com", "password123", "0412345678", "123 Coffee St", "customer"),
    ]
    
    added = 0
    skipped = 0
    
    for name, email, password, phone, address, role in users:
        hashed_password = hash_password(password)
        try:
            cur.execute("""
                INSERT INTO customers (name, email, password, phone, address, role)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, email, hashed_password, phone, address, role))
            added += 1
            print(f"✅ Created {role}: {email} (password: {password})")
        except sqlite3.IntegrityError:
            skipped += 1
    
    conn.commit()
    if skipped > 0:
        print(f"ℹ️  {skipped} users already exist")

def main():
    parser = argparse.ArgumentParser(description="Setup and seed the coffee store database")
    parser.add_argument("--reset", action="store_true", help="Reset the database (deletes all data)")
    parser.add_argument("--seed", action="store_true", help="Seed with sample data (safe, won't duplicate)")
    parser.add_argument("--force", action="store_true", help="Force seed even if data exists")
    args = parser.parse_args()

    # Reset database if requested
    if args.reset:
        if DB_PATH.exists():
            DB_PATH.unlink()
            print(f"🗑️  Removed existing database: {DB_PATH}")
        else:
            print("ℹ️  No existing database to reset")

    # Always ensure tables exist
    conn = get_connection()
    create_tables(conn)
    print(f"📊 Database ready at: {DB_PATH}")

    # Seed if requested
    if args.seed:
        seed_products(conn, force=args.force)
        seed_users(conn, force=args.force)
        print("\n✅ Seeding complete!")

    conn.close()

if __name__ == "__main__":
    main()