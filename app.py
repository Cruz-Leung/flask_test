import os
import sqlite3
import hashlib
import secrets
from flask import (
    Flask, 
    render_template, 
    url_for, 
    request, 
    redirect, 
    flash,
    abort,
    jsonify,
    session
)
from werkzeug.utils import secure_filename
from pathlib import Path
from functools import wraps
from datetime import datetime


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-this-in-production'
app.config['SESSION_TYPE'] = 'filesystem'

STATIC_IMG_DIR = Path(__file__).parent / "static" / "img"
STATIC_DIR = Path(__file__).parent / 'static'
STATIC_JS_DIR = STATIC_DIR / 'js'
ALLOWED_EXT = {"png", "jpg", "jpeg", "webp", "gif", "avif"} 

# Verify static folder exists
STATIC_JS_DIR.mkdir(parents=True, exist_ok=True)

print(f"Static folder: {STATIC_DIR}")
print(f"JS folder: {STATIC_JS_DIR}")
print(f"cart.js exists: {(STATIC_JS_DIR / 'cart.js').exists()}")

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

def get_user_role():
    """Get the current user's role from session"""
    return session.get('user_role', 'customer')

def login_required(f):
    """Decorator to require login for certain routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin or manager role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        
        role = get_user_role()
        if role not in ['admin', 'manager']:
            flash('Access denied. Admin privileges required.', 'danger')
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def manager_required(f):
    """Decorator to require manager role only"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        
        role = get_user_role()
        if role != 'manager':
            flash('Access denied. Manager privileges required.', 'danger')
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


# ===========================
# PUBLIC ROUTES
# ===========================

@app.route("/")
def index():
    return render_template("index.html", year=datetime.now().year)

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
        year=datetime.now().year
    )

@app.route("/beans")
def beans():
    return render_template("beans.html", year=datetime.now().year)

@app.route("/accessories")
def accessories():
    return render_template("accessories.html", year=datetime.now().year)

@app.route("/about")
def about():
    return render_template("about.html", year=datetime.now().year)

@app.route("/terms")
def terms():
    return render_template("terms.html", year=datetime.now().year)

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    conn = get_db_connection()
    product = conn.execute('''
        SELECT * FROM products WHERE id = ?
    ''', (product_id,)).fetchone()
    
    # Get related products from same category
    related_products = []
    if product:
        related_products = conn.execute('''
            SELECT * FROM products 
            WHERE category = ? AND id != ? 
            LIMIT 4
        ''', (product['category'], product_id)).fetchall()
    
    conn.close()
    
    if product is None:
        flash('Product not found', 'danger')
        return redirect(url_for('index'))
    
    return render_template('product_detail.html', 
                         product=product, 
                         related_products=related_products,
                         year=datetime.now().year)


# ===========================
# AUTHENTICATION ROUTES
# ===========================

@app.route("/register", methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        phone = request.form.get('phone', '').strip()
        
        # Validation
        if not name or not email or not password:
            flash('Name, email, and password are required.', 'danger')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return redirect(url_for('register'))
        
        hashed_password = hash_password(password)
        
        conn = get_db_connection()
        try:
            conn.execute("""
                INSERT INTO customers (name, email, password, phone, role)
                VALUES (?, ?, ?, ?, 'customer')
            """, (name, email, hashed_password, phone))
            conn.commit()
            flash('✅ Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('An account with this email already exists.', 'danger')
        except Exception as e:
            flash(f'Error creating account: {e}', 'danger')
        finally:
            conn.close()
    
    return render_template('register.html', year=datetime.now().year)


@app.route("/login", methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Email and password are required.', 'danger')
            return redirect(url_for('login'))
        
        hashed_password = hash_password(password)
        
        conn = get_db_connection()
        user = conn.execute("""
            SELECT * FROM customers WHERE email = ? AND password = ?
        """, (email, hashed_password)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            session['user_role'] = user['role']
            
            flash(f'Welcome back, {user["name"]}!', 'success')
            
            # Redirect based on role
            if user['role'] in ['admin', 'manager']:
                return redirect(url_for('admin_orders'))
            else:
                next_page = request.args.get('next')
                return redirect(next_page if next_page else url_for('index'))
        else:
            flash('Invalid email or password.', 'danger')
    
    return render_template('login.html', year=datetime.now().year)


@app.route("/logout")
def logout():
    """User logout"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route("/account")
@login_required
def account():
    """User account page"""
    conn = get_db_connection()
    user = conn.execute("""
        SELECT * FROM customers WHERE id = ?
    """, (session['user_id'],)).fetchone()
    
    # Get recent orders
    orders = conn.execute('''
        SELECT * FROM orders_new 
        WHERE user_id = ? 
        ORDER BY created_at DESC
        LIMIT 5
    ''', (session['user_id'],)).fetchall()
    
    conn.close()
    
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('logout'))
    
    return render_template('account.html', 
                         user=user, 
                         orders=orders,
                         year=datetime.now().year)


@app.route("/account/edit", methods=['GET', 'POST'])
@login_required
def edit_account():
    """Edit user account"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        state = request.form.get('state', '').strip()
        postcode = request.form.get('postcode', '').strip()
        new_password = request.form.get('new_password', '')
        
        try:
            if new_password:
                if len(new_password) < 6:
                    flash('Password must be at least 6 characters.', 'danger')
                    return redirect(url_for('edit_account'))
                hashed_password = hash_password(new_password)
                conn.execute("""
                    UPDATE customers 
                    SET name = ?, phone = ?, address = ?, city = ?, state = ?, postcode = ?, password = ?
                    WHERE id = ?
                """, (name, phone, address, city, state, postcode, hashed_password, session['user_id']))
            else:
                conn.execute("""
                    UPDATE customers 
                    SET name = ?, phone = ?, address = ?, city = ?, state = ?, postcode = ?
                    WHERE id = ?
                """, (name, phone, address, city, state, postcode, session['user_id']))
            
            conn.commit()
            session['user_name'] = name
            flash('✅ Account updated successfully!', 'success')
            return redirect(url_for('account'))
        except Exception as e:
            flash(f'Error updating account: {e}', 'danger')
        finally:
            conn.close()
    
    user = conn.execute("""
        SELECT * FROM customers WHERE id = ?
    """, (session['user_id'],)).fetchone()
    conn.close()
    
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('logout'))
    
    return render_template('edit_account.html', user=user, year=datetime.now().year)


# ===========================
# CART ROUTES (UNIFIED)
# ===========================

@app.route("/cart/add/<int:product_id>", methods=['POST'])
def cart_add(product_id):
    """Add item to cart via AJAX"""
    try:
        data = request.get_json()
        quantity = data.get('quantity', 1)
        
        # Get product from database
        conn = get_db_connection()
        product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        conn.close()
        
        if not product:
            return jsonify({'success': False, 'message': 'Product not found'}), 404
        
        # Check stock
        if product['stock'] < quantity:
            return jsonify({'success': False, 'message': f'Only {product["stock"]} items available'}), 400
        
        # Initialize cart if it doesn't exist
        if 'cart' not in session:
            session['cart'] = {}
        
        # Create cart key
        cart_key = str(product_id)
        
        # Add or update item in cart
        if cart_key in session['cart']:
            session['cart'][cart_key]['quantity'] += quantity
        else:
            session['cart'][cart_key] = {
                'product_id': product_id,
                'quantity': quantity
            }
        
        # Mark session as modified
        session.modified = True
        
        # Calculate cart count
        cart_count = sum(item['quantity'] for item in session['cart'].values())
        
        return jsonify({
            'success': True,
            'message': 'Item added to cart',
            'cart_count': cart_count
        })
        
    except Exception as e:
        print(f"Error adding to cart: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route("/cart/remove/<cart_key>", methods=['POST'])
def cart_remove(cart_key):
    """Remove item from cart"""
    try:
        if 'cart' in session and cart_key in session['cart']:
            del session['cart'][cart_key]
            session.modified = True
        
        cart_count = sum(item['quantity'] for item in session.get('cart', {}).values())
        
        return jsonify({
            'success': True,
            'cart_count': cart_count
        })
    except Exception as e:
        print(f"Error removing from cart: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route("/cart/update/<int:product_id>", methods=['POST'])
def cart_update(product_id):
    """Update cart item quantity"""
    try:
        data = request.get_json()
        quantity = data.get('quantity', 1)
        cart_key = str(product_id)
        
        if 'cart' in session and cart_key in session['cart']:
            if quantity <= 0:
                del session['cart'][cart_key]
            else:
                session['cart'][cart_key]['quantity'] = quantity
            session.modified = True
        
        cart_count = sum(item['quantity'] for item in session.get('cart', {}).values())
        
        return jsonify({
            'success': True,
            'cart_count': cart_count
        })
    except Exception as e:
        print(f"Error updating cart: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route("/cart/mini")
def cart_mini():
    """Get mini cart data for dropdown"""
    try:
        cart = session.get('cart', {})
        cart_items = []
        total = 0
        
        if cart:
            conn = get_db_connection()
            for cart_key, item_data in cart.items():
                product_id = item_data['product_id']
                quantity = item_data['quantity']
                
                product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
                if product:
                    subtotal = product['price'] * quantity
                    cart_items.append({
                        'cart_key': cart_key,
                        'product_id': product_id,
                        'name': product['name'],
                        'price': product['price'],
                        'quantity': quantity,
                        'subtotal': subtotal,
                        'image': product['image']
                    })
                    total += subtotal
            conn.close()
        
        return jsonify({
            'items': cart_items,
            'total': total,
            'count': sum(item['quantity'] for item in cart_items)
        })
        
    except Exception as e:
        print(f"Error loading mini cart: {e}")
        return jsonify({'items': [], 'total': 0, 'count': 0})


@app.route("/cart")
def view_cart():
    """Display shopping cart page"""
    cart = session.get('cart', {})
    cart_items = []
    subtotal = 0
    
    if cart:
        conn = get_db_connection()
        for cart_key, item_data in cart.items():
            product_id = item_data['product_id']
            quantity = item_data['quantity']
            
            product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
            if product:
                item_subtotal = product['price'] * quantity
                cart_items.append({
                    'product_id': product_id,
                    'sku': product['sku'],
                    'name': product['name'],
                    'price': product['price'],
                    'quantity': quantity,
                    'subtotal': item_subtotal,
                    'image': product['image'],
                    'stock': product['stock']
                })
                subtotal += item_subtotal
        conn.close()
    
    # Calculate tax and shipping
    tax_rate = 0.10
    tax = subtotal * tax_rate
    shipping = 15.00 if subtotal < 100 and subtotal > 0 else 0
    total = subtotal + tax + shipping
    
    return render_template('cart.html',
                         cart_items=cart_items,
                         subtotal=subtotal,
                         tax=tax,
                         shipping=shipping,
                         total=total,
                         year=datetime.now().year)


# ===========================
# CHECKOUT & ORDERS
# ===========================

@app.route("/checkout")
def checkout():
    """Display checkout form"""
    cart = session.get('cart', {})
    
    if not cart:
        flash("Your cart is empty. Add some products first!", "warning")
        return redirect(url_for('index'))
    
    # Calculate totals
    conn = get_db_connection()
    cart_items = []
    subtotal = 0
    
    for cart_key, item_data in cart.items():
        product_id = item_data['product_id']
        quantity = item_data['quantity']
        
        product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if product:
            item_subtotal = product['price'] * quantity
            cart_items.append({
                'sku': product['sku'],
                'name': product['name'],
                'price': product['price'],
                'quantity': quantity,
                'subtotal': item_subtotal,
                'image': product['image']
            })
            subtotal += item_subtotal
    
    conn.close()
    
    # Calculate tax and shipping
    tax_rate = 0.10
    tax = subtotal * tax_rate
    shipping = 15.00 if subtotal < 100 else 0
    total = subtotal + tax + shipping
    
    # Get user info if logged in
    user_info = {}
    if session.get('user_id'):
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM customers WHERE id = ?", (session['user_id'],)).fetchone()
        conn.close()
        if user:
            user_info = {
                'name': user['name'],
                'email': user['email']
            }
    
    return render_template('checkout.html',
                         cart_items=cart_items,
                         subtotal=subtotal,
                         tax=tax,
                         shipping=shipping,
                         total=total,
                         user_info=user_info,
                         year=datetime.now().year)


@app.route("/place-order", methods=['POST'])
def place_order():
    """Process the order and save to database"""
    cart = session.get('cart', {})
    
    if not cart:
        flash("Your cart is empty!", "danger")
        return redirect(url_for('index'))
    
    # Get form data
    customer_name = request.form.get('name')
    customer_email = request.form.get('email')
    customer_phone = request.form.get('phone')
    shipping_address = request.form.get('address')
    shipping_city = request.form.get('city')
    shipping_state = request.form.get('state')
    shipping_zip = request.form.get('zip')
    payment_method = request.form.get('payment_method')
    
    # Validate required fields
    if not all([customer_name, customer_email, shipping_address, shipping_city, 
                shipping_state, shipping_zip, payment_method]):
        flash("Please fill in all required fields.", "danger")
        return redirect(url_for('checkout'))
    
    conn = get_db_connection()
    
    try:
        # Calculate totals
        subtotal = 0
        order_items = []
        
        for cart_key, item_data in cart.items():
            product_id = item_data['product_id']
            quantity = item_data['quantity']
            
            product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
            if product:
                if product['stock'] < quantity:
                    flash(f"Sorry, only {product['stock']} units of {product['name']} available.", "danger")
                    conn.close()
                    return redirect(url_for('checkout'))
                
                item_subtotal = product['price'] * quantity
                order_items.append({
                    'sku': product['sku'],
                    'name': product['name'],
                    'price': product['price'],
                    'quantity': quantity,
                    'subtotal': item_subtotal
                })
                subtotal += item_subtotal
        
        # Calculate tax and shipping
        tax_rate = 0.10
        tax = subtotal * tax_rate
        shipping_cost = 15.00 if subtotal < 100 else 0
        total = subtotal + tax + shipping_cost
        
        # Generate unique order number
        order_number = f"ORD-{secrets.token_hex(4).upper()}"
        
        # Insert order
        cursor = conn.execute('''
            INSERT INTO orders_new (
                order_number, user_id, customer_name, customer_email, customer_phone,
                shipping_address, shipping_city, shipping_state, shipping_zip,
                payment_method, subtotal, tax, shipping_cost, total, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            order_number,
            session.get('user_id'),
            customer_name,
            customer_email,
            customer_phone,
            shipping_address,
            shipping_city,
            shipping_state,
            shipping_zip,
            payment_method,
            subtotal,
            tax,
            shipping_cost,
            total,
            'pending'
        ))
        
        order_id = cursor.lastrowid
        
        # Insert order items and update stock
        for item in order_items:
            conn.execute('''
                INSERT INTO order_items_new (order_id, product_sku, product_name, quantity, price, subtotal)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (order_id, item['sku'], item['name'], item['quantity'], item['price'], item['subtotal']))
            
            # Update product stock
            conn.execute('''
                UPDATE products SET stock = stock - ? WHERE sku = ?
            ''', (item['quantity'], item['sku']))
        
        conn.commit()
        
        # Clear cart
        session['cart'] = {}
        session.modified = True
        
        flash(f"✅ Order placed successfully! Order Number: {order_number}", "success")
        return redirect(url_for('order_confirmation', order_number=order_number))
        
    except Exception as e:
        conn.rollback()
        flash(f"❌ Error placing order: {str(e)}", "danger")
        return redirect(url_for('checkout'))
    finally:
        conn.close()


@app.route("/order-confirmation/<order_number>")
def order_confirmation(order_number):
    """Display order confirmation"""
    conn = get_db_connection()
    
    # Get order details
    order = conn.execute('''
        SELECT * FROM orders_new WHERE order_number = ?
    ''', (order_number,)).fetchone()
    
    if not order:
        flash("Order not found.", "danger")
        conn.close()
        return redirect(url_for('index'))
    
    # Get order items
    order_items = conn.execute('''
        SELECT * FROM order_items_new WHERE order_id = ?
    ''', (order['id'],)).fetchall()
    
    conn.close()
    
    return render_template('order_confirmation.html',
                         order=order,
                         order_items=order_items,
                         year=datetime.now().year)


@app.route("/my-orders")
@login_required
def my_orders():
    """Display user's order history"""
    conn = get_db_connection()
    orders = conn.execute('''
        SELECT * FROM orders_new 
        WHERE user_id = ? 
        ORDER BY created_at DESC
    ''', (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('my_orders.html',
                         orders=orders,
                         year=datetime.now().year)


# ===========================
# ADMIN ROUTES - Products
# ===========================

@app.route("/admin/product/add", methods=['GET', 'POST'])
@admin_required
def add_product():
    if request.method == 'POST':
        sku = request.form.get('sku')
        name = request.form.get('name')
        category = request.form.get('category')
        subcategory = request.form.get('subcategory')
        price = request.form.get('price')
        stock = request.form.get('stock')
        description = request.form.get('description')

        image = request.files.get('image')
        image_filename = None
        if image and image.filename and allowed_file(image.filename):
            ext = image.filename.rsplit('.', 1)[1].lower()
            image_filename = f"{sku}.{ext}"
            STATIC_IMG_DIR.mkdir(parents=True, exist_ok=True)
            image.save(STATIC_IMG_DIR / image_filename)

        conn = get_db_connection()
        try:
            conn.execute("""
                INSERT INTO products (sku, name, category, subcategory, price, stock, description, image)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (sku, name, category, subcategory, price, stock, description, image_filename))
            conn.commit()
            flash("✅ New product added successfully!", "success")
            conn.close()
            return redirect(url_for('add_product'))
        except sqlite3.IntegrityError:
            flash("⚠️ Product with this SKU already exists.", "warning")
        except Exception as e:
            flash(f"❌ Error adding product: {e}", "danger")
        finally:
            conn.close()
    
    return render_template('manage_product.html', action='add', year=datetime.now().year)


@app.route("/admin/product/edit", methods=['GET', 'POST'])
@admin_required
def edit_product():
    sku = request.args.get('sku')
    search = request.args.get('search', '').strip()
    category_filter = request.args.get('category', '')
    
    conn = get_db_connection()

    # Handle EDIT submission
    if request.method == 'POST' and sku:
        old_sku = request.form.get('old_sku')
        new_sku = request.form.get('sku')
        name = request.form.get('name')
        category = request.form.get('category')
        subcategory = request.form.get('subcategory')
        price = request.form.get('price')
        description = request.form.get('description')
        stock = request.form.get('stock')

        sku_changed = old_sku != new_sku and session.get('user_role') == 'manager'

        image = request.files.get('image')
        image_filename = None
        if image and image.filename:
            if allowed_file(image.filename):
                ext = image.filename.rsplit('.', 1)[1].lower()
                image_filename = f"{new_sku}.{ext}"
                STATIC_IMG_DIR.mkdir(parents=True, exist_ok=True)
                image.save(STATIC_IMG_DIR / image_filename)
            else:
                flash("Invalid image type.", "danger")
                conn.close()
                return redirect(request.url)

        try:
            if sku_changed:
                existing = conn.execute("SELECT id FROM products WHERE sku = ?", (new_sku,)).fetchone()
                if existing:
                    flash("⚠️ A product with this SKU already exists.", "warning")
                    conn.close()
                    return redirect(url_for('edit_product', sku=old_sku))
            
            if image_filename:
                conn.execute("""
                    UPDATE products
                    SET sku = ?, name = ?, category = ?, subcategory = ?, price = ?, description = ?, stock = ?, image = ?
                    WHERE sku = ?
                """, (new_sku, name, category, subcategory, price, description, stock, image_filename, old_sku))
            else:
                conn.execute("""
                    UPDATE products
                    SET sku = ?, name = ?, category = ?, subcategory = ?, price = ?, description = ?, stock = ?
                    WHERE sku = ?
                """, (new_sku, name, category, subcategory, price, description, stock, old_sku))
            conn.commit()
            flash("✅ Product updated successfully.", "success")
            sku = new_sku
        except sqlite3.Error as e:
            flash(f"❌ Error updating product: {e}", "danger")
        finally:
            conn.close()

        return redirect(url_for('edit_product', sku=sku))

    # GET product list with filtering
    query = 'SELECT * FROM products WHERE 1=1'
    params = []
    
    if category_filter:
        query += ' AND category = ?'
        params.append(category_filter)
    
    if search:
        query += ' AND (sku LIKE ? OR name LIKE ? OR CAST(id AS TEXT) LIKE ?)'
        search_term = f'%{search}%'
        params.extend([search_term, search_term, search_term])
    
    query += ' ORDER BY category, name'
    products = conn.execute(query, params).fetchall()
    
    product = None
    if sku:
        product = conn.execute('SELECT * FROM products WHERE sku = ?', (sku,)).fetchone()
    
    conn.close()
    return render_template('edit_product.html', 
                         product=product, 
                         products=products,
                         search=search,
                         category_filter=category_filter,
                         year=datetime.now().year)


@app.route("/admin/product/delete/<sku>", methods=['POST'])
@admin_required
def delete_product(sku):
    conn = get_db_connection()
    try:
        product = conn.execute("SELECT * FROM products WHERE sku = ?", (sku,)).fetchone()
        if not product:
            flash("Product not found.", "danger")
            return redirect(url_for('edit_product'))
        
        conn.execute("DELETE FROM products WHERE sku = ?", (sku,))
        conn.commit()
        
        if product['image']:
            image_path = STATIC_IMG_DIR / product['image']
            if image_path.exists():
                try:
                    image_path.unlink()
                except Exception as e:
                    print(f"Could not delete image file: {e}")
        
        flash(f"✅ Product '{product['name']}' has been deleted.", "success")
    except Exception as e:
        flash(f"❌ Error deleting product: {e}", "danger")
    finally:
        conn.close()
    
    return redirect(url_for('edit_product'))


# ===========================
# ADMIN ROUTES - Orders
# ===========================

@app.route("/admin/orders")
@admin_required
def admin_orders():
    """Display all orders for admin/manager"""
    conn = get_db_connection()
    orders = conn.execute('''
        SELECT * FROM orders_new 
        ORDER BY created_at DESC
    ''').fetchall()
    conn.close()
    
    return render_template('admin_orders.html',
                         orders=orders,
                         year=datetime.now().year)


@app.route("/admin/order/<int:order_id>")
@admin_required
def admin_order_detail(order_id):
    """Display detailed order information"""
    conn = get_db_connection()
    
    order = conn.execute('''
        SELECT * FROM orders_new WHERE id = ?
    ''', (order_id,)).fetchone()
    
    if not order:
        flash("Order not found.", "danger")
        conn.close()
        return redirect(url_for('admin_orders'))
    
    order_items = conn.execute('''
        SELECT * FROM order_items_new WHERE order_id = ?
    ''', (order_id,)).fetchall()
    
    conn.close()
    
    return render_template('admin_order_detail.html',
                         order=order,
                         order_items=order_items,
                         year=datetime.now().year)


@app.route("/admin/order/<int:order_id>/update-status", methods=['POST'])
@admin_required
def update_order_status(order_id):
    """Update order status"""
    new_status = request.form.get('status')
    
    if new_status not in ['pending', 'processing', 'shipped', 'delivered', 'cancelled']:
        flash("Invalid status.", "danger")
        return redirect(url_for('admin_order_detail', order_id=order_id))
    
    conn = get_db_connection()
    conn.execute('''
        UPDATE orders_new 
        SET status = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    ''', (new_status, order_id))
    conn.commit()
    conn.close()
    
    flash(f"✅ Order status updated to '{new_status}'", "success")
    return redirect(url_for('admin_order_detail', order_id=order_id))


# ===========================
# MANAGER ROUTES - Staff
# ===========================

@app.route("/manager/staff")
@manager_required
def manage_staff():
    conn = get_db_connection()
    staff = conn.execute("""
        SELECT id, name, email, role, created_at 
        FROM customers 
        WHERE role IN ('admin', 'manager')
        ORDER BY 
            CASE role 
                WHEN 'manager' THEN 1 
                WHEN 'admin' THEN 2 
            END,
            name
    """).fetchall()
    conn.close()
    return render_template('manage_staff.html', staff=staff, year=datetime.now().year)

@app.route("/manager/staff/add", methods=['GET', 'POST'])
@manager_required
def add_staff():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        role = request.form.get('role', 'admin')
        phone = request.form.get('phone', '').strip()
        
        if not name or not email or not password:
            flash('Name, email, and password are required.', 'danger')
            return redirect(url_for('add_staff'))
        
        if role not in ['admin', 'manager']:
            flash('Invalid role selected.', 'danger')
            return redirect(url_for('add_staff'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return redirect(url_for('add_staff'))
        
        hashed_password = hash_password(password)
        
        conn = get_db_connection()
        try:
            conn.execute("""
                INSERT INTO customers (name, email, password, phone, role)
                VALUES (?, ?, ?, ?, ?)
            """, (name, email, hashed_password, phone, role))
            conn.commit()
            flash(f'✅ {role.capitalize()} account created for {name}!', 'success')
            return redirect(url_for('manage_staff'))
        except sqlite3.IntegrityError:
            flash('An account with this email already exists.', 'danger')
        except Exception as e:
            flash(f'Error creating account: {e}', 'danger')
        finally:
            conn.close()
    
    return render_template('add_staff.html', year=datetime.now().year)

@app.route("/manager/staff/edit/<int:staff_id>", methods=['GET', 'POST'])
@manager_required
def edit_staff(staff_id):
    conn = get_db_connection()
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        role = request.form.get('role', 'admin')
        new_password = request.form.get('new_password', '')
        
        if role not in ['admin', 'manager']:
            flash('Invalid role selected.', 'danger')
            return redirect(url_for('edit_staff', staff_id=staff_id))
        
        try:
            if new_password:
                if len(new_password) < 6:
                    flash('Password must be at least 6 characters.', 'danger')
                    return redirect(url_for('edit_staff', staff_id=staff_id))
                hashed_password = hash_password(new_password)
                conn.execute("""
                    UPDATE customers 
                    SET name = ?, phone = ?, role = ?, password = ?
                    WHERE id = ?
                """, (name, phone, role, hashed_password, staff_id))
            else:
                conn.execute("""
                    UPDATE customers 
                    SET name = ?, phone = ?, role = ?
                    WHERE id = ?
                """, (name, phone, role, staff_id))
            
            conn.commit()
            flash('Staff member updated successfully!', 'success')
            return redirect(url_for('manage_staff'))
        except Exception as e:
            flash(f'Error updating staff: {e}', 'danger')
        finally:
            conn.close()
    
    staff_member = conn.execute("""
        SELECT * FROM customers WHERE id = ? AND role IN ('admin', 'manager')
    """, (staff_id,)).fetchone()
    conn.close()
    
    if not staff_member:
        flash('Staff member not found.', 'danger')
        return redirect(url_for('manage_staff'))
    
    return render_template('edit_staff.html', staff=staff_member, year=datetime.now().year)

@app.route("/manager/staff/delete/<int:staff_id>", methods=['POST'])
@manager_required
def delete_staff(staff_id):
    if staff_id == session.get('user_id'):
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('manage_staff'))
    
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM customers WHERE id = ? AND role IN ('admin', 'manager')", (staff_id,))
        conn.commit()
        flash('Staff member removed successfully.', 'success')
    except Exception as e:
        flash(f'Error removing staff: {e}', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('manage_staff'))


# ===========================
# DATABASE INITIALIZATION
# ===========================

def init_db():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT,
            brand TEXT,
            price REAL NOT NULL,
            stock INTEGER DEFAULT 0,
            description TEXT,
            image TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            postcode TEXT,
            country TEXT DEFAULT 'Australia',
            role TEXT DEFAULT 'customer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")


def init_orders_db():
    """Initialize orders and order_items tables"""
    conn = get_db_connection()
    
    cursor = conn.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='orders_new'
    """)
    
    if cursor.fetchone() is None:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS orders_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number TEXT UNIQUE NOT NULL,
                user_id INTEGER,
                customer_name TEXT NOT NULL,
                customer_email TEXT NOT NULL,
                customer_phone TEXT,
                shipping_address TEXT NOT NULL,
                shipping_city TEXT NOT NULL,
                shipping_state TEXT NOT NULL,
                shipping_zip TEXT NOT NULL,
                payment_method TEXT NOT NULL,
                subtotal REAL NOT NULL,
                tax REAL NOT NULL,
                shipping_cost REAL NOT NULL,
                total REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES customers(id)
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS order_items_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_sku TEXT NOT NULL,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                subtotal REAL NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders_new(id)
            )
        ''')
        
        conn.commit()
        print("✅ New orders tables created")
    
    conn.close()


# ===========================
# ERROR HANDLERS
# ===========================

@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', error_code=403, error_message="Access Denied", year=datetime.now().year), 403

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', error_code=404, error_message="Page Not Found", year=datetime.now().year), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('error.html', error_code=500, error_message="Internal Server Error", year=datetime.now().year), 500


# ===========================
# RUN APP
# ===========================

if __name__ == "__main__":
    init_db()
    init_orders_db()
    app.run(debug=True)