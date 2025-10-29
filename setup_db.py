import sqlite3
import os
from pathlib import Path
import argparse

BASEDIR = Path(__file__).parent
DB_PATH = BASEDIR / "store.db"

# Database creation SQL
CREATE_CUSTOMERS = """
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    phone TEXT,
    address TEXT,
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
"""

# Sample products for beans and accessories
SAMPLE_PRODUCTS = [
    # Beans
    ("House Blend 1kg", "B-HOUSE-001", "beans", "Medium roast - chocolate & citrus notes", 24.50, 50, "beans1.jpg", "Cruzy Coffee"),
    ("Single Origin Colombia 250g", "B-COL-002", "beans", "Light-medium roast, bright acidity", 12.00, 80, "beans2.jpg", "Cruzy Coffee"),
    ("Dark Roast Espresso 250g", "B-ESP-003", "beans", "Rich, full-bodied dark roast", 11.00, 40, "beans3.jpg", "Cruzy Coffee"),
    # Accessories
    ("Precision Grinder", "A-GRID-001", "accessories", "Consistent grind for every brew", 199.00, 15, "accessory1.jpg", "Cruzy Coffee"),
    ("Barista Tamper", "A-TAMP-002", "accessories", "Stainless steel tamper with calibration", 39.00, 60, "accessory2.jpg", "Cruzy Coffee"),
    ("Milk Frothing Pitcher 600ml", "A-PITCH-003", "accessories", "Professional stainless pitcher", 29.50, 75, "accessory3.jpg", "Cruzy Coffee"),
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

def seed_products(conn):
    cur = conn.cursor()
    
    # First, insert basic products (beans & accessories)
    for product in SAMPLE_PRODUCTS:
        cur.execute("""
            INSERT OR IGNORE INTO products 
            (name, sku, category, description, price, stock, image, brand) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, product)
    
    # Then insert machine products with SKU-based image names
    for brand, info in MACHINE_BRANDS.items():
        base_price = info["base_price"]
        for i, model in enumerate(info["models"], 1):
            name = f"{brand} {model}"
            sku = f"M-{brand[:3].upper()}{i:03d}"
            price = base_price * (1 + (i % 5) * 0.1)
            image = f"{sku}.jpg"  # Image name matches SKU
            
            cur.execute("""
                INSERT OR IGNORE INTO products 
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
                image,
                brand
            ))
    
    conn.commit()
    print("Products seeded successfully")

def seed_sample_customer_and_order(conn):
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO customers (name, email, phone, address) 
        VALUES (?, ?, ?, ?)
    """, ("Test Customer", "test@example.com", "0412345678", "123 Coffee St"))
    
    conn.commit()
    print("Sample customer seeded successfully")

def main():
    parser = argparse.ArgumentParser(description="Setup and seed the coffee store database")
    parser.add_argument("--reset", action="store_true", help="Reset the database")
    parser.add_argument("--seed", action="store_true", help="Seed with sample data")
    args = parser.parse_args()

    if args.reset and DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Removed existing database: {DB_PATH}")

    conn = get_connection()
    create_tables(conn)
    print(f"Database ready at: {DB_PATH}")

    if args.seed:
        seed_products(conn)
        seed_sample_customer_and_order(conn)

    conn.close()

if __name__ == "__main__":
    main()