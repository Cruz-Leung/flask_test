import os
import sqlite3
import hashlib
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
from functools import wraps


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

# Authentication helper functions
def hash_password(password):
    """Hash a password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    """Decorator to require login for certain routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

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

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    conn = get_db_connection()
    product = conn.execute('''
        SELECT * FROM products WHERE id = ?
    ''', (product_id,)).fetchone()
    conn.close()
    
    if product is None:
        flash('Product not found', 'danger')
        return redirect(url_for('index'))
    
    return render_template('product_detail.html', product=product, year=2025)

# Helpers for products and cart
def get_product_by_id(product_id):
    conn = get_db_connection()
    row = conn.execute("SELECT id, name, price, image FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_product_by_sku(sku):
    conn = get_db_connection()
    row = conn.execute("SELECT id, name, price, image FROM products WHERE sku = ?", (sku,)).fetchone()
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

# Cart routes
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

# Checkout and orders (SINGLE DEFINITION)
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart = get_cart()
    if not cart:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('view_cart'))

    if request.method == 'POST':
        # If user is logged in, use their ID, otherwise create/find customer
        if 'user_id' in session:
            customer_id = session['user_id']
        else:
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
                # Create temporary password for guest checkout
                temp_password = hash_password(email + "temp")
                cur.execute("INSERT INTO customers (name, email, password, phone, address) VALUES (?, ?, ?, ?, ?)", 
                           (name, email, temp_password, phone, address))
                customer_id = cur.lastrowid
            conn.commit()
            conn.close()

        # Create order
        conn = get_db_connection()
        cur = conn.cursor()
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

    # Pre-fill form if user is logged in
    user_data = None
    if 'user_id' in session:
        conn = get_db_connection()
        user_data = conn.execute("SELECT * FROM customers WHERE id = ?", (session['user_id'],)).fetchone()
        conn.close()

    total, count = cart_totals(cart)
    return render_template('checkout.html', cart=cart, total=total, count=count, user=user_data)

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

# Authentication routes
@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()

        # Validation
        if not name or not email or not password:
            flash('Name, email, and password are required.', 'danger')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return redirect(url_for('register'))

        # Hash password and create account
        hashed_password = hash_password(password)
        
        conn = get_db_connection()
        try:
            conn.execute("""
                INSERT INTO customers (name, email, password, phone, address)
                VALUES (?, ?, ?, ?, ?)
            """, (name, email, hashed_password, phone, address))
            conn.commit()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('An account with this email already exists.', 'danger')
        except Exception as e:
            flash(f'Error creating account: {e}', 'danger')
        finally:
            conn.close()

        return redirect(url_for('register'))

    return render_template('register.html', year=2025)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Email and password are required.', 'danger')
            return redirect(url_for('login'))

        hashed_password = hash_password(password)
        
        conn = get_db_connection()
        user = conn.execute("""
            SELECT id, name, email FROM customers 
            WHERE email = ? AND password = ?
        """, (email, hashed_password)).fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            flash(f'Welcome back, {user["name"]}!', 'success')
            
            # Redirect to 'next' page if it exists, otherwise to index
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('index'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html', year=2025)

@app.route("/logout")
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route("/account")
@login_required
def account():
    conn = get_db_connection()
    user = conn.execute("""
        SELECT * FROM customers WHERE id = ?
    """, (session['user_id'],)).fetchone()
    
    orders = conn.execute("""
        SELECT * FROM orders 
        WHERE customer_id = ? 
        ORDER BY created_at DESC
    """, (session['user_id'],)).fetchall()
    
    conn.close()
    return render_template('account.html', user=user, orders=orders, year=2025)

@app.route("/account/edit", methods=['GET', 'POST'])
@login_required
def edit_account():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        
        conn = get_db_connection()
        try:
            conn.execute("""
                UPDATE customers 
                SET name = ?, phone = ?, address = ?
                WHERE id = ?
            """, (name, phone, address, session['user_id']))
            conn.commit()
            session['user_name'] = name
            flash('Account updated successfully!', 'success')
        except Exception as e:
            flash(f'Error updating account: {e}', 'danger')
        finally:
            conn.close()
        
        return redirect(url_for('account'))

    conn = get_db_connection()
    user = conn.execute("""
        SELECT * FROM customers WHERE id = ?
    """, (session['user_id'],)).fetchone()
    conn.close()
    
    return render_template('edit_account.html', user=user, year=2025)

if __name__ == '__main__':
    app.debug = True
    app.run()
