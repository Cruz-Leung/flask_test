import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "store.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_order():
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Create customer
        cur.execute("""
            INSERT INTO customers (name, email, phone, address) 
            VALUES (?, ?, ?, ?)
        """, ("Cruz Leung", "cruz@example.com", "0412345678", "123 Coffee Street, Sydney"))
        customer_id = cur.lastrowid
        
        # Create order
        cur.execute("""
            INSERT INTO orders (customer_id, status) 
            VALUES (?, ?)
        """, (customer_id, "pending"))
        order_id = cur.lastrowid
        
        # Get products
        products_to_order = [
            ("M-BREV-001", 1),  # Breville Barista Express
            ("B-HOUSE-001", 2),  # House Blend Coffee
            ("A-TAMP-002", 1),   # Tamper
            ("A-GRID-001", 1),   # Grinder
        ]
        
        # Add order items
        for sku, quantity in products_to_order:
            # Get product details
            cur.execute("SELECT id, price FROM products WHERE sku = ?", (sku,))
            product = cur.fetchone()
            
            if product:
                cur.execute("""
                    INSERT INTO order_items (order_id, product_id, quantity, unit_price)
                    VALUES (?, ?, ?, ?)
                """, (order_id, product['id'], quantity, product['price']))
        
        # Calculate and update order total
        cur.execute("""
            UPDATE orders 
            SET total = (
                SELECT SUM(quantity * unit_price) 
                FROM order_items 
                WHERE order_id = ?
            )
            WHERE id = ?
        """, (order_id, order_id))
        
        conn.commit()
        print("Order created successfully!")
        
        # Show order details
        cur.execute("""
            SELECT p.name, oi.quantity, oi.unit_price, (oi.quantity * oi.unit_price) as subtotal
            FROM order_items oi
            JOIN products p ON p.id = oi.product_id
            WHERE oi.order_id = ?
        """, (order_id,))
        
        print("\nOrder Details:")
        print("-" * 50)
        total = 0
        for item in cur.fetchall():
            print(f"{item['name']}: {item['quantity']} x ${item['unit_price']:.2f} = ${item['subtotal']:.2f}")
            total += item['subtotal']
        print("-" * 50)
        print(f"Total: ${total:.2f}")
        
    except sqlite3.Error as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    create_order()