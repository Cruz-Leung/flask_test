import os
import sqlite3
from flask import (
    Flask, 
    render_template, 
    url_for, 
    request, 
    redirect, 
    flash,
)
from werkzeug.utils import secure_filename
from pathlib import Path
from flask import jsonify, session


app = Flask(__name__)

# Configure your secret key for session management
app.secret_key = 'your_secret_key_here'

STATIC_IMG_DIR = Path(__file__).parent / "static" / "img"
ALLOWED_EXT = {"png", "jpg", "jpeg", "webp", "gif", "avif"} 

def get_db_connection():
    conn = sqlite3.connect('store.db')
    conn.row_factory = sqlite3.Row
    return conn

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

@app.route("/")
def index():
    return render_template("index.html", year=2025)

@app.route("/machines/<category>")
def machines(category):
    conn = get_db_connection()
    products = conn.execute('''
        SELECT * FROM products 
        WHERE category = "machines" 
        AND subcategory = ? 
        ORDER BY brand, name
    ''', (category,)).fetchall()
    conn.close()

    categories = {
        'semi-auto': 'Semi-Automatic Machines',
        'pod': 'Pod Machines',
        'fully-auto': 'Fully Automatic Machines'
    }
    
    return render_template(
        "machines.html",
        products=products,
        category=category,
        title=categories.get(category),
        year=2025
    )

@app.route("/beans")
def beans():
    return render_template("beans.html", year=2025)

@app.route("/accessories")
def accessories():
    return render_template("accessories.html", year=2025)

@app.route("/about")
def about():
    return render_template("about.html", year=2025)

# @app.route("/test-products")
# def test_products():
#     conn = get_db_connection()
#     # Get all products with their details
#     products = conn.execute('''
#         SELECT id, name, category, description, price, stock, image 
#         FROM products
#         ORDER BY category, name
#     ''').fetchall()
#     conn.close()
#     return render_template("test_products.html", year=2025, products=products)

# @app.route("/admin/upload-image", methods=["GET", "POST"])
# def upload_image():
#     if request.method == "POST":
#         file = request.files.get("image")
#         sku = request.form.get("sku", "").strip()
#         product_id = request.form.get("product_id", "").strip()

#         if not file or file.filename == "":
#             flash("No file selected", "danger")
#             app.logger.warning("Upload attempted with no file")
#             return redirect(request.url)

#         if not allowed_file(file.filename):
#             flash("Invalid file type", "danger")
#             app.logger.warning("Rejected file type: %s", file.filename)
#             return redirect(request.url)

#         # build stable filename
#         ext = file.filename.rsplit(".", 1)[1].lower()
#         if sku:
#             filename = secure_filename(f"{sku}.{ext}")
#         elif product_id:
#             filename = secure_filename(f"product_{product_id}.{ext}")
#         else:
#             filename = secure_filename(file.filename)

#         # ensure directory exists
#         STATIC_IMG_DIR.mkdir(parents=True, exist_ok=True)
#         dest = STATIC_IMG_DIR / filename

#         try:
#             file.save(dest)
#             app.logger.info("Saved upload to %s", dest)
#         except Exception as e:
#             flash("Failed to save file", "danger")
#             app.logger.exception("Error saving uploaded file: %s", e)
#             return redirect(request.url)

#         # update DB entry
#         try:
#             conn = get_db_connection()
#             if sku:
#                 conn.execute("UPDATE products SET image = ? WHERE sku = ?", (filename, sku))
#             elif product_id:
#                 conn.execute("UPDATE products SET image = ? WHERE id = ?", (filename, product_id))
#             conn.commit()
#             conn.close()
#             flash(f"Image uploaded as {filename}", "success")
#             app.logger.info("Updated DB for %s", sku or product_id)
#         except Exception as e:
#             flash("Uploaded file but failed to update DB", "warning")
#             app.logger.exception("DB update failed: %s", e)

#         return redirect(request.url)

#     # GET: show form and any flash messages
#     messages = get_flashed_messages(with_categories=True)
#     return render_template("edit_product.html", messages=messages)

# @app.route("/admin/product/edit/<sku>", methods=['GET', 'POST'])
# def admin_edit_product(sku):
#     conn = get_db_connection()
    
#     if request.method == 'POST':
#         # Get form data
#         name = request.form.get('name')
#         price = request.form.get('price')
#         description = request.form.get('description')
#         stock = request.form.get('stock')
        
#         # Handle image upload if provided
#         image = request.files.get('image')
#         image_filename = None
#         if image and image.filename:
#             if allowed_file(image.filename):
#                 # Create a filename based on SKU
#                 ext = image.filename.rsplit('.', 1)[1].lower()
#                 image_filename = f"{sku}.{ext}"
#                 image_path = STATIC_IMG_DIR / image_filename
#                 STATIC_IMG_DIR.mkdir(parents=True, exist_ok=True)
#                 image.save(image_path)
#             else:
#                 flash('Invalid image type', 'error')
#                 return redirect(request.url)

#         # Update database
#         try:
#             if image_filename:
#                 conn.execute("""
#                     UPDATE products 
#                     SET name = ?, price = ?, description = ?, stock = ?, image = ?
#                     WHERE sku = ?
#                 """, (name, price, description, stock, image_filename, sku))
#             else:
#                 conn.execute("""
#                     UPDATE products 
#                     SET name = ?, price = ?, description = ?, stock = ?
#                     WHERE sku = ?
#                 """, (name, price, description, stock, sku))
            
#             conn.commit()
#             flash('Product updated successfully', 'success')
#         except sqlite3.Error as e:
#             flash(f'Error updating product: {e}', 'error')
        
#         return redirect(url_for('admin_products'))

#     # GET request - show edit form
#     product = conn.execute('SELECT * FROM products WHERE sku = ?', (sku,)).fetchone()
#     conn.close()
    
#     if product is None:
#         flash('Product not found', 'error')
#         return redirect(url_for('admin_products'))
        
#     return render_template('admin/edit_product.html', product=product)

@app.route("/admin/product", methods=['GET', 'POST'])
def manage_product():
    action = request.args.get('action', 'edit')  # 'edit' or 'add'
    sku = request.args.get('sku') or request.form.get('sku')
    conn = get_db_connection()

    # ADD PRODUCT
    if request.method == 'POST' and action == 'add':
        sku = request.form.get('sku')
        name = request.form.get('name')
        category = request.form.get('category')
        subcategory = request.form.get('subcategory')
        price = request.form.get('price')
        stock = request.form.get('stock')
        description = request.form.get('description')

        # handle image
        image = request.files.get('image')
        image_filename = None
        if image and image.filename and allowed_file(image.filename):
            ext = image.filename.rsplit('.', 1)[1].lower()
            image_filename = f"{sku}.{ext}"
            STATIC_IMG_DIR.mkdir(parents=True, exist_ok=True)
            image.save(STATIC_IMG_DIR / image_filename)

        try:
            conn.execute("""
                INSERT INTO products (sku, name, category, subcategory, price, stock, description, image)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (sku, name, category, subcategory, price, stock, description, image_filename))
            conn.commit()
            flash("✅ New product added successfully!", "success")
            return redirect(url_for('manage_product', action='add'))
        except sqlite3.IntegrityError:
            flash("⚠️ Product with this SKU already exists.", "warning")
        except Exception as e:
            flash(f"❌ Error adding product: {e}", "danger")

    # EDIT PRODUCT
    elif request.method == 'POST' and action == 'edit':
        name = request.form.get('name')
        price = request.form.get('price')
        description = request.form.get('description')
        stock = request.form.get('stock')

        image = request.files.get('image')
        image_filename = None
        if image and image.filename:
            if allowed_file(image.filename):
                ext = image.filename.rsplit('.', 1)[1].lower()
                image_filename = f"{sku}.{ext}"
                STATIC_IMG_DIR.mkdir(parents=True, exist_ok=True)
                image.save(STATIC_IMG_DIR / image_filename)
                flash(f"Image '{image_filename}' uploaded successfully.", "success")
            else:
                flash("Invalid image type. Please upload a valid image.", "danger")
                conn.close()
                return redirect(request.url)

        try:
            if image_filename:
                conn.execute("""
                    UPDATE products
                    SET name = ?, price = ?, description = ?, stock = ?, image = ?
                    WHERE sku = ?
                """, (name, price, description, stock, image_filename, sku))
            else:
                conn.execute("""
                    UPDATE products
                    SET name = ?, price = ?, description = ?, stock = ?
                    WHERE sku = ?
                """, (name, price, description, stock, sku))
            conn.commit()
            flash("Product updated successfully.", "success")
        except sqlite3.Error as e:
            flash(f"Error updating product: {e}", "danger")

        conn.close()
        return redirect(url_for('manage_product', sku=sku, action='edit'))

    # GET REQUEST
    product = None
    if sku and action == 'edit':
        product = conn.execute('SELECT * FROM products WHERE sku = ?', (sku,)).fetchone()
    conn.close()

    return render_template('edit_product.html', product=product, action=action)

# Helpers for products and cart
def get_product_by_id(product_id):
    conn = get_db_connection()
    row = conn.execute("SELECT id, name, price, image FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_cart():
    return session.get('cart', {})

def set_cart(cart):
    session['cart'] = cart

def cart_totals(cart):
    total = sum(item['price'] * item['quantity'] for item in cart.values())
    count = sum(item['quantity'] for item in cart.values())
    return total, count

# Replace the broken add_to_cart (was using SQLAlchemy 'Product')
@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    product = get_product_by_id(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404

    cart = get_cart()
    key = str(product_id)
    if key in cart:
        cart[key]['quantity'] += 1
    else:
        cart[key] = {
            'id': product['id'],
            'name': product['name'],
            'price': float(product['price']),
            'image': product.get('image'),
            'quantity': 1
        }
    set_cart(cart)
    total, count = cart_totals(cart)
    return jsonify({'message': 'Added to cart', 'cart_count': count, 'cart_total': total})

# Optional alias to support /cart/add/<id> if your JS uses it
@app.route('/cart/add/<int:product_id>', methods=['POST'])
def cart_add_alias(product_id):
    return add_to_cart(product_id)

@app.route('/cart')
def view_cart():
    cart = get_cart()
    total, count = cart_totals(cart)
    return render_template('cart.html', cart=cart, total=total, count=count)

@app.route('/cart/update/<int:product_id>', methods=['POST'])
def update_cart(product_id):
    cart = get_cart()
    key = str(product_id)
    qty = int(request.form.get('quantity', 0))
    if key in cart:
        if qty > 0:
            cart[key]['quantity'] = qty
        else:
            cart.pop(key)
        set_cart(cart)
    return redirect(url_for('view_cart'))

@app.route('/cart/clear', methods=['POST'])
def clear_cart():
    session['cart'] = {}
    return redirect(url_for('view_cart'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart = get_cart()
    if not cart:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('view_cart'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()

        if not name or not email or not address:
            flash('Name, email and address are required.', 'danger')
            return redirect(url_for('checkout'))

        conn = get_db_connection()
        cur = conn.cursor()
        # get or create customer by email
        cur.execute("SELECT id FROM customers WHERE email = ?", (email,))
        row = cur.fetchone()
        if row:
            customer_id = row['id']
            cur.execute("UPDATE customers SET name = ?, phone = ?, address = ? WHERE id = ?", (name, phone, address, customer_id))
        else:
            cur.execute("INSERT INTO customers (name, email, phone, address) VALUES (?, ?, ?, ?)", (name, email, phone, address))
            customer_id = cur.lastrowid

        # create order
        total, _ = cart_totals(cart)
        cur.execute("INSERT INTO orders (customer_id, status, total) VALUES (?, ?, ?)", (customer_id, 'pending', total))
        order_id = cur.lastrowid

        # add order_items and decrement stock
        for item in cart.values():
            product_id = item['id']
            qty = item['quantity']
            unit_price = item['price']
            cur.execute("INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
                        (order_id, product_id, qty, unit_price))
            # decrement stock if present
            cur.execute("""
                UPDATE products
                SET stock = CASE WHEN stock IS NOT NULL THEN MAX(stock - ?, 0) ELSE stock END
                WHERE id = ?
            """, (qty, product_id))

        conn.commit()
        conn.close()

        # clear cart
        session['cart'] = {}
        return redirect(url_for('order_success', order_id=order_id))

    total, count = cart_totals(cart)
    return render_template('checkout.html', cart=cart, total=total, count=count)

@app.route('/order/<int:order_id>')
def order_success(order_id):
    conn = get_db_connection()
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    items = conn.execute("""
        SELECT p.name, oi.quantity, oi.unit_price, p.image
        FROM order_items oi
        JOIN products p ON p.id = oi.product_id
        WHERE oi.order_id = ?
    """, (order_id,)).fetchall()
    conn.close()
    if not order:
        flash('Order not found.', 'danger')
        return redirect(url_for('index'))
    return render_template('order_success.html', order=order, items=items)

@app.route('/cart/mini')
def cart_mini():
    cart = get_cart()
    total, count = cart_totals(cart)
    return render_template('partials/mini_cart.html', cart=cart, total=total, count=count)

@app.route('/cart/count')
def cart_count():
    cart = get_cart()
    _, count = cart_totals(cart)
    return jsonify({'count': count})

if __name__ == '__main__':
    app.debug = True
    app.run()