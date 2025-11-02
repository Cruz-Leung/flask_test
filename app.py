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
    abort,
    jsonify,
    session
)
from werkzeug.utils import secure_filename
from pathlib import Path
from functools import wraps
from datetime import datetime


app = Flask(__name__)

# Configure your secret key for session management
app.secret_key = 'your_secret_key_here_change_in_production'

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

# ADMIN ROUTES - Product Management
@app.route("/admin/product", methods=['GET', 'POST'])
@admin_required
def manage_product():
    action = request.args.get('action', 'edit')
    sku = request.args.get('sku') or request.form.get('sku')
    search = request.args.get('search', '').strip()
    category_filter = request.args.get('category', 'all')
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
            conn.close()
            return redirect(url_for('manage_product', action='add'))
        except sqlite3.IntegrityError:
            flash("⚠️ Product with this SKU already exists.", "warning")
        except Exception as e:
            flash(f"❌ Error adding product: {e}", "danger")

    # EDIT PRODUCT
    elif request.method == 'POST' and action == 'edit':
        old_sku = request.form.get('old_sku')  # Hidden field with original SKU
        new_sku = request.form.get('sku')
        name = request.form.get('name')
        price = request.form.get('price')
        description = request.form.get('description')
        stock = request.form.get('stock')

        # Check if SKU is being changed (managers only)
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
                # Check if new SKU already exists
                existing = conn.execute("SELECT id FROM products WHERE sku = ?", (new_sku,)).fetchone()
                if existing:
                    flash("⚠️ A product with this SKU already exists.", "warning")
                    conn.close()
                    return redirect(url_for('manage_product', sku=old_sku, action='edit'))
            
            if image_filename:
                conn.execute("""
                    UPDATE products
                    SET sku = ?, name = ?, price = ?, description = ?, stock = ?, image = ?
                    WHERE sku = ?
                """, (new_sku, name, price, description, stock, image_filename, old_sku))
            else:
                conn.execute("""
                    UPDATE products
                    SET sku = ?, name = ?, price = ?, description = ?, stock = ?
                    WHERE sku = ?
                """, (new_sku, name, price, description, stock, old_sku))
            conn.commit()
            flash("✅ Product updated successfully.", "success")
            
            # Redirect to the new SKU if it changed
            sku = new_sku
        except sqlite3.Error as e:
            flash(f"❌ Error updating product: {e}", "danger")

        conn.close()
        return redirect(url_for('manage_product', sku=sku, action='edit'))

    # GET product list for edit mode with filtering
    products = []
    if action == 'edit':
        query = 'SELECT * FROM products WHERE 1=1'
        params = []
        
        # Apply category filter
        if category_filter != 'all':
            query += ' AND category = ?'
            params.append(category_filter)
        
        # Apply search filter
        if search:
            query += ' AND (sku LIKE ? OR name LIKE ?)'
            search_term = f'%{search}%'
            params.extend([search_term, search_term])
        
        query += ' ORDER BY category, name'
        products = conn.execute(query, params).fetchall()
    
    # GET specific product if editing
    product = None
    if sku and action == 'edit':
        product = conn.execute('SELECT * FROM products WHERE sku = ?', (sku,)).fetchone()
    
    conn.close()
    return render_template('edit_product.html', 
                         product=product, 
                         products=products, 
                         action=action,
                         search=search,
                         category_filter=category_filter)

@app.route("/admin/product/delete/<sku>", methods=['POST'])
@admin_required
def delete_product(sku):
    conn = get_db_connection()
    try:
        # Check if product exists
        product = conn.execute("SELECT * FROM products WHERE sku = ?", (sku,)).fetchone()
        if not product:
            flash("Product not found.", "danger")
            return redirect(url_for('manage_product', action='edit'))
        
        # Delete the product
        conn.execute("DELETE FROM products WHERE sku = ?", (sku,))
        conn.commit()
        
        # Try to delete the image file if it exists
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
    
    return redirect(url_for('manage_product', action='add'))

# MANAGER ROUTES - Staff Management
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
    return render_template('manage_staff.html', staff=staff, year=2025)

@app.route("/manager/staff/add", methods=['GET', 'POST'])
@manager_required
def add_staff():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        role = request.form.get('role', 'admin')
        phone = request.form.get('phone', '').strip()
        
        # Validate
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
    
    return render_template('add_staff.html', year=2025)

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
    
    return render_template('edit_staff.html', staff=staff_member, year=2025)

@app.route("/manager/staff/delete/<int:staff_id>", methods=['POST'])
@manager_required
def delete_staff(staff_id):
    # Prevent deleting yourself
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

# CA    S - Consolidated
@app.route('/cart')
def view_cart():
    """Main cart page"""
    cart = session.get('cart', {})
    cart_items = list(cart.values())
    cart_total = sum(item['price'] * item['quantity'] for item in cart_items)
    
    return render_template('view_cart.html', 
                         cart_items=cart_items, 
                         cart_total=cart_total,
                         year=datetime.now().year)

@app.route("/cart/add", methods=['POST'])
def cart_add():
    """Add product to cart via AJAX"""
    data = request.get_json()
    product_id = data.get('product_id')
    
    if not product_id:
        return jsonify({'success': False, 'message': 'Product ID required'}), 400
    
    # Get product from database
    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    conn.close()    # ...existing code...
    
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
    
    # ...existing code...
    
    if not product:
        return jsonify({'success': False, 'message': 'Product not found'}), 404
    
    if product['stock'] <= 0:
        return jsonify({'success': False, 'message': 'Product out of stock'}), 400
    
    # Initialize cart in session if not exists
    if 'cart' not in session:
        session['cart'] = {}
    
    cart = session['cart']
    product_id_str = str(product_id)
    
    # Add or increment quantity
    if product_id_str in cart:
        cart[product_id_str]['quantity'] += 1
    else:
        cart[product_id_str] = {
            'product_id': product['id'],
            'name': product['name'],
            'price': float(product['price']),
            'image': product['image'],
            'quantity': 1
        }
    
    session['cart'] = cart
    session.modified = True
    
    return jsonify({
        'success': True,
        'message': 'Product added to cart',
        'cart_count': sum(item['quantity'] for item in cart.values())
    })

@app.route("/cart/update", methods=['POST'])
def cart_update():
    """Update cart quantity via AJAX"""
    data = request.get_json()
    product_id = str(data.get('product_id'))
    quantity = data.get('quantity', 1)
    
    if 'cart' not in session:
        return jsonify({'success': False, 'message': 'Cart is empty'}), 400
    
    cart = session['cart']
    
    if product_id in cart:
        if quantity <= 0:
            del cart[product_id]
        else:
            cart[product_id]['quantity'] = quantity
        
        session['cart'] = cart
        session.modified = True
        return jsonify({'success': True, 'message': 'Cart updated'})
    
    return jsonify({'success': False, 'message': 'Product not in cart'}), 400

@app.route("/cart/remove", methods=['POST'])
def cart_remove():
    """Remove product from cart via AJAX"""
    data = request.get_json()
    product_id = str(data.get('product_id'))
    
    if 'cart' not in session:
        return jsonify({'success': False, 'message': 'Cart is empty'}), 400
    
    cart = session['cart']
    
    if product_id in cart:
        del cart[product_id]
        session['cart'] = cart
        session.modified = True
        return jsonify({'success': True, 'message': 'Product removed'})
    
    return jsonify({'success': False, 'message': 'Product not in cart'}), 400

@app.route("/cart/mini")
def cart_mini():
    """API endpoint for mini cart data (AJAX)"""
    if 'cart' not in session or not session['cart']:
        return jsonify({
            'success': True,
            'cart_items': [],
            'total': 0.0
        })
    
    cart = session['cart']
    cart_items = list(cart.values())
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    
    return jsonify({
        'success': True,
        'cart_items': cart_items,
        'total': total
    })

@app.route('/cart/clear', methods=['POST'])
def clear_cart():
    """Clear entire cart"""
    session['cart'] = {}
    flash('Cart cleared.', 'info')
    return redirect(url_for('view_cart'))

# Checkout and orders
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart = session.get('cart', {})  # Changed from get_cart()
    if not cart:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('view_cart'))

    if request.method == 'POST':
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
            cur.execute("SELECT id FROM customers WHERE email = ?", (email,))
            row = cur.fetchone()
            if row:
                customer_id = row['id']
                cur.execute("UPDATE customers SET name = ?, phone = ?, address = ? WHERE id = ?", (name, phone, address, customer_id))
            else:
                temp_password = hash_password(email + "temp")
                cur.execute("INSERT INTO customers (name, email, password, phone, address) VALUES (?, ?, ?, ?, ?)", 
                           (name, email, temp_password, phone, address))
                customer_id = cur.lastrowid
            conn.commit()
            conn.close()

        conn = get_db_connection()
        cur = conn.cursor()
        
        # Calculate totals inline instead of using cart_totals()
        total = sum(item['price'] * item['quantity'] for item in cart.values())
        
        cur.execute("INSERT INTO orders (customer_id, status, total) VALUES (?, ?, ?)", (customer_id, 'pending', total))
        order_id = cur.lastrowid

        for item in cart.values():
            product_id = item['product_id']  # Changed from item['id']
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

        session['cart'] = {}
        return redirect(url_for('order_success', order_id=order_id))

    user_data = None
    if 'user_id' in session:
        conn = get_db_connection()
        user_data = conn.execute("SELECT * FROM customers WHERE id = ?", (session['user_id'],)).fetchone()
        conn.close()

    # Calculate totals inline
    total = sum(item['price'] * item['quantity'] for item in cart.values())
    count = sum(item['quantity'] for item in cart.values())
    
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

        if not name or not email or not password:
            flash('Name, email, and password are required.', 'danger')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return redirect(url_for('register'))

        hashed_password = hash_password(password)
        
        conn = get_db_connection()
        try:
            # All new registrations are customers by default
            conn.execute("""
                INSERT INTO customers (name, email, password, phone, address, role)
                VALUES (?, ?, ?, ?, ?, 'customer')
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
            SELECT id, name, email, role FROM customers 
            WHERE email = ? AND password = ?
        """, (email, hashed_password)).fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            session['user_role'] = user['role']
            
            # Role-specific welcome message
            if user['role'] == 'manager':
                flash(f'Welcome back, Manager {user["name"]}!', 'success')
            elif user['role'] == 'admin':
                flash(f'Welcome back, Admin {user["name"]}!', 'success')
            else:
                flash(f'Welcome back, {user["name"]}!', 'success')
            
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

# Error handlers
@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403

@app.errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404

if __name__ == '__main__':
    app.debug = True
    app.run()
