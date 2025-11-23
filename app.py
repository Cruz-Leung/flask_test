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
from werkzeug.security import generate_password_hash, check_password_hash
from pathlib import Path
from functools import wraps
from datetime import datetime
import difflib  # Add this to your imports at the top



app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-this-in-production'
app.config['SESSION_TYPE'] = 'filesystem'

STATIC_IMG_DIR = Path(__file__).parent / "static" / "img"
STATIC_DIR = Path(__file__).parent / 'static'
STATIC_JS_DIR = STATIC_DIR / 'js'
ALLOWED_EXT = {"png", "jpeg", "webp", "gif", "avif", "jpg"} 

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
    """Hash a password using pbkdf2 with salt (same as registration)"""
    return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

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

def log_activity(action, product_id=None, product_sku=None, product_name=None, details=None):
    """Log admin/manager activity"""
    if session.get('user_role') not in ['admin', 'manager']:
        return  # Only log admin/manager actions
    
    conn = get_db_connection()
    conn.execute("""
        INSERT INTO activity_log 
        (user_id, user_name, user_role, action, product_id, product_sku, product_name, details)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session.get('user_id'),
        session.get('user_name'),
        session.get('user_role'),
        action,
        product_id,
        product_sku,
        product_name,
        details
    ))
    conn.commit()
    conn.close()

# ===========================
# CONTEXT PROCESSOR
# ===========================

@app.context_processor
def utility_processor():
    """Make utility functions available to all templates"""
    def get_breville_id():
        """Get the product ID for Breville Barista Express (M-BRE003)"""
        conn = get_db_connection()
        product = conn.execute("""
            SELECT id FROM products 
            WHERE sku = 'M-BRE003'
            LIMIT 1
        """).fetchone()
        conn.close()
        return product['id'] if product else 1  # Fallback to ID 1 if not found
    
    def get_summer_blend_id():
        """Get the product ID for Summer Blend (B-FB-SUM-001)"""
        conn = get_db_connection()
        product = conn.execute("""
            SELECT id FROM products 
            WHERE sku = 'B-FB-SUM-001'
            LIMIT 1
        """).fetchone()
        conn.close()
        return product['id'] if product else 1  # Fallback to ID 1 if not found
    
    def get_cruzy_beans_id():  # ADD THIS FUNCTION
        conn = get_db_connection()
        product = conn.execute("SELECT id FROM products WHERE sku = 'B-CZY-001' LIMIT 1").fetchone()
        conn.close()
        return product['id'] if product else 1
    
    return dict(
        get_summer_blend_id=get_summer_blend_id,
        get_breville_id=get_breville_id,
        get_cruzy_beans_id=get_cruzy_beans_id  # ADD THIS
    )


# ===========================
# PUBLIC ROUTES
# ===========================

@app.route("/")
def index():
    """Homepage"""
    conn = get_db_connection()
    
    # Fetch trending products from different categories
    # Get 3 machines, 3 beans, and 2 accessories for variety
    machines = conn.execute("""
        SELECT * FROM products 
        WHERE category = 'machines' AND stock > 0
        ORDER BY 
            CASE WHEN discount_percentage > 0 THEN 0 ELSE 1 END,
            RANDOM()
        LIMIT 3
    """).fetchall()
    
    beans = conn.execute("""
        SELECT * FROM products 
        WHERE category = 'beans' AND stock > 0
        ORDER BY 
            CASE WHEN discount_percentage > 0 THEN 0 ELSE 1 END,
            RANDOM()
        LIMIT 3
    """).fetchall()
    
    accessories = conn.execute("""
        SELECT * FROM products 
        WHERE category = 'accessories' AND stock > 0
        ORDER BY 
            CASE WHEN discount_percentage > 0 THEN 0 ELSE 1 END,
            RANDOM()
        LIMIT 2
    """).fetchall()
    
    # Combine all products into one list
    trending_products = list(machines) + list(beans) + list(accessories)
    
    conn.close()
    
    return render_template(
        "index.html",
        trending_products=trending_products,
        year=datetime.now().year
    )

@app.route("/machines")
@app.route("/machines/<category>")
def machines(category='semi-auto'):
    """Display coffee machines by category with tab switching"""
    conn = get_db_connection()
    
    # Fetch ALL machine products (all categories)
    all_products = conn.execute("""
        SELECT * FROM products 
        WHERE category IN ('semi-auto', 'fully-auto', 'pod')
           OR subcategory IN ('semi-auto', 'fully-auto', 'pod')
           OR (category = 'machines' AND subcategory IN ('semi-auto', 'fully-auto', 'pod'))
        ORDER BY category, name
    """).fetchall()
    
    conn.close()
    
    # Convert products to list of dicts for JSON serialization
    products_list = []
    for product in all_products:
        products_list.append({
            'id': product['id'],
            'sku': product['sku'],
            'name': product['name'],
            'category': product['category'],
            'subcategory': product['subcategory'],
            'price': product['price'],
            'stock': product['stock'],
            'description': product['description'],
            'image': product['image'],
            'discount_percentage': product['discount_percentage']
        })
    
    import json
    products_json = json.dumps(products_list)
    
    # Validate category
    valid_categories = ['semi-auto', 'fully-auto', 'pod']
    if category not in valid_categories:
        category = 'semi-auto'
    
    return render_template(
        "machines.html",
        products_json=products_json,
        category=category,
        year=datetime.now().year
    )

@app.route("/beans")
@app.route("/beans/<subcategory>")
def beans(subcategory=None):
    """Display coffee beans with subcategory filtering"""
    conn = get_db_connection()
    
    # If subcategory is provided, filter by it
    if subcategory:
        products = conn.execute('''
            SELECT * FROM products 
            WHERE category = "beans" 
            AND subcategory = ? 
            ORDER BY name
        ''', (subcategory,)).fetchall()
    else:
        # Show all beans products
        products = conn.execute('''
            SELECT * FROM products 
            WHERE category = "beans" 
            ORDER BY subcategory, name
        ''').fetchall()
    
    conn.close()
    
    subcategories = {
        'coffee-beans': 'Coffee Beans',
        'ground-coffee': 'Ground Coffee'
    }
    
    return render_template(
        "beans.html",
        products=products,
        subcategory=subcategory,
        subcategories=subcategories,
        title=subcategories.get(subcategory, 'All Coffee Beans'),
        year=datetime.now().year
    )

@app.route("/accessories")
@app.route("/accessories/<subcategory>")
def accessories(subcategory=None):
    """Display accessories with optional subcategory filter"""
    conn = get_db_connection()
    
    if subcategory:
        # Filter by subcategory
        products = conn.execute(
            "SELECT * FROM products WHERE category = 'accessories' AND subcategory = ? ORDER BY name",
            (subcategory,)
        ).fetchall()
    else:
        # Show all accessories (default to brewing-equipment)
        subcategory = 'brewing-equipment'
        products = conn.execute(
            "SELECT * FROM products WHERE category = 'accessories' AND subcategory = ? ORDER BY name",
            (subcategory,)
        ).fetchall()
    
    conn.close()
    
    return render_template(
        "accessories.html",
        products=products,
        subcategory=subcategory,
        year=datetime.now().year
    )

@app.route("/about")
def about():
    return render_template("about.html", year=datetime.now().year)

@app.route("/report-bug", methods=['GET', 'POST'])
def report_bug():
    """Bug report page - requires login"""
    # Check if user is logged in
    if 'user_id' not in session:
        flash("⚠️ Please sign in to report a bug.", "warning")
        return redirect(url_for('login', next=request.url))
    
    if request.method == 'POST':
        bug_title = request.form.get('bug_title')
        bug_category = request.form.get('bug_category')
        bug_description = request.form.get('bug_description')
        bug_device = request.form.get('bug_device', 'Not specified')
        bug_severity = request.form.get('bug_severity', 'medium')
        
        user_id = session.get('user_id')
        username = session.get('user_name')
        
        conn = get_db_connection()
        
        # Create bug_reports table if it doesn't exist
        conn.execute('''
            CREATE TABLE IF NOT EXISTS bug_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                device TEXT,
                severity TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Insert bug report
        conn.execute('''
            INSERT INTO bug_reports (user_id, username, title, category, description, device, severity)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, bug_title, bug_category, bug_description, bug_device, bug_severity))
        
        conn.commit()
        conn.close()
        
        flash(f"✅ Thank you, {username}! Your bug report has been submitted successfully.", "success")
        return redirect(url_for('about'))
    
    return render_template('report_bug.html', year=datetime.now().year)

@app.route("/manager/reports")
@admin_required  # Both admin and manager can access
def reports():
    """Reports dashboard - Bugs and Missing Products"""
    conn = get_db_connection()
    
    # Get all bug reports, sorted by severity and date
    bugs = conn.execute('''
        SELECT * FROM bug_reports 
        ORDER BY 
            CASE severity 
                WHEN 'high' THEN 1 
                WHEN 'medium' THEN 2 
                WHEN 'low' THEN 3 
            END,
            created_at DESC
    ''').fetchall()
    
    # Get all missing product requests
    missing_products = conn.execute('''
        SELECT * FROM missing_products 
        ORDER BY created_at DESC
    ''').fetchall()
    
    conn.close()
    
    return render_template('reports.html',
                         bugs=bugs,
                         missing_products=missing_products,
                         year=datetime.now().year)


@app.route("/manager/reports/bug/<int:bug_id>/update", methods=['POST'])
@admin_required
def update_bug_status(bug_id):
    """Update bug report status"""
    new_status = request.form.get('status')
    
    if new_status not in ['open', 'in-progress', 'resolved', 'closed']:
        flash("Invalid status.", "danger")
        return redirect(url_for('reports'))
    
    conn = get_db_connection()
    conn.execute('''
        UPDATE bug_reports 
        SET status = ? 
        WHERE id = ?
    ''', (new_status, bug_id))
    conn.commit()
    conn.close()
    
    flash(f"✅ Bug report #{bug_id} status updated to '{new_status}'", "success")
    return redirect(url_for('reports'))


@app.route("/manager/reports/missing/<int:request_id>/update", methods=['POST'])
@admin_required
def update_missing_product_status(request_id):
    """Update missing product request status"""
    new_status = request.form.get('status')
    
    if new_status not in ['pending', 'reviewing', 'added', 'declined']:
        flash("Invalid status.", "danger")
        return redirect(url_for('reports') + '?tab=missing')
    
    conn = get_db_connection()
    conn.execute('''
        UPDATE missing_products 
        SET status = ? 
        WHERE id = ?
    ''', (new_status, request_id))
    conn.commit()
    conn.close()
    
    flash(f"✅ Product request #{request_id} status updated to '{new_status}'", "success")
    return redirect(url_for('reports') + '?tab=missing')


@app.route("/request-product", methods=['GET', 'POST'])
def request_product():
    """Request a missing product"""
    # Check if user is logged in
    if 'user_id' not in session:
        flash("⚠️ Please sign in to request a product.", "warning")
        return redirect(url_for('login', next=request.url))
    
    if request.method == 'POST':
        product_name = request.form.get('product_name')
        product_category = request.form.get('product_category')
        description = request.form.get('description')
        additional_info = request.form.get('additional_info', 'None provided')
        priority = request.form.get('priority', 'medium')
        
        user_id = session.get('user_id')
        username = session.get('user_name')  # FIXED: using user_name
        
        conn = get_db_connection()
        
        # Create missing_products table if it doesn't exist
        conn.execute('''
            CREATE TABLE IF NOT EXISTS missing_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                product_name TEXT NOT NULL,
                product_category TEXT NOT NULL,
                description TEXT NOT NULL,
                additional_info TEXT,
                priority TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES customers (id)
            )
        ''')
        
        # Insert missing product request
        conn.execute('''
            INSERT INTO missing_products (user_id, username, product_name, product_category, description, additional_info, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, product_name, product_category, description, additional_info, priority))
        
        conn.commit()
        conn.close()
        
        flash(f"✅ Thank you, {username}! Your product request has been submitted successfully.", "success")
        return redirect(url_for('index'))
    
    return render_template('request_product.html', year=datetime.now().year)

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

@app.route("/register", methods=["GET", "POST"])
def register():
    """User registration with strong password requirements"""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        
        # Basic validation
        if not name or not email or not password:
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for("register"))
        
        # Password match check
        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for("register"))
        
        # SERVER-SIDE PASSWORD VALIDATION
        password_errors = validate_password(password, name, email)
        if password_errors:
            for error in password_errors:
                flash(error, "danger")
            return redirect(url_for("register"))
        
        # Check if user exists
        conn = get_db_connection()
        existing_user = conn.execute("SELECT * FROM customers WHERE email = ?", (email,)).fetchone()
        
        if existing_user:
            conn.close()
            flash("Email already registered. Please log in.", "warning")
            return redirect(url_for("login"))
        
        # Hash password with salt
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
        
        # Insert new user
        try:
            conn.execute(
                "INSERT INTO customers (name, email, password, phone, address) VALUES (?, ?, ?, ?, ?)",
                (name, email, hashed_password, phone, address)
            )
            conn.commit()
            
            # Get the new user
            user = conn.execute("SELECT * FROM customers WHERE email = ?", (email,)).fetchone()
            conn.close()
            
            # Log the user in
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            session['user_role'] = user['role']
            
            flash(f"Welcome, {name}! Your account has been created.", "success")
            return redirect(url_for('index'))
            
        except Exception as e:
            conn.close()
            flash("An error occurred during registration. Please try again.", "danger")
            return redirect(url_for("register"))
    
    return render_template("register.html", year=datetime.now().year)


def validate_password(password, name="", email=""):
    """
    Validate password against professional security requirements.
    Returns list of error messages (empty list if valid).
    """
    errors = []
    
    # Common weak passwords
    COMMON_PASSWORDS = [
        'password', 'password123', '123456', '12345678', 'qwerty', 'abc123',
        'monkey', 'letmein', 'trustno1', 'dragon', 'baseball', 'iloveyou',
        'master', 'sunshine', 'ashley', 'bailey', 'shadow', 'superman',
        'coffee', 'espresso', 'cappuccino', 'latte', 'cruzy', 'admin',
        'qwertyuiop', 'asdfghjkl', 'zxcvbnm', '1234567890',
        'passw0rd', 'p@ssword', 'p@ssw0rd', 'welcome', 'login'
    ]
    
    SEQUENTIAL_PATTERNS = [
        'abcd', 'bcde', 'cdef', 'defg', '1234', '2345', '3456', '4567',
        'qwer', 'wert', 'erty', 'asdf', 'sdfg', 'dfgh'
    ]
    
    # 1. Length check
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long.")
    
    # 2. Uppercase letter check
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter (A-Z).")
    
    # 3. Lowercase letter check
    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter (a-z).")
    
    # 4. Number check
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one number (0-9).")
    
    # 5. Special character check
    special_chars = set("!@#$%^&*()_+-=[]{};':\"\\|,.<>/?")
    if not any(c in special_chars for c in password):
        errors.append("Password must contain at least one special character (!@#$%^&*).")
    
    # 6. No leading/trailing spaces
    if password != password.strip():
        errors.append("Password cannot have leading or trailing spaces.")
    
    # 7. Check for common passwords
    if password.lower() in COMMON_PASSWORDS:
        errors.append("This password is too common. Please choose a stronger password.")
    
    # 8. Check for sequential patterns
    password_lower = password.lower()
    for pattern in SEQUENTIAL_PATTERNS:
        if pattern in password_lower:
            errors.append("Password cannot contain sequential characters (e.g., abcd, 1234).")
            break
    
    # 9. Check for repeating characters (e.g., aaaa, 1111)
    import re
    if re.search(r'(.)\1{3,}', password):
        errors.append("Password cannot contain repeating characters (e.g., aaaa, 1111).")
    
    # 10. Check if password contains user's name
    if name and name.lower() in password.lower():
        errors.append("Password cannot contain your name.")
    
    # 11. Check if password contains email username
    if email:
        email_username = email.split('@')[0].lower()
        if email_username in password.lower():
            errors.append("Password cannot contain your email address.")
    
    return errors


@app.route("/login", methods=["GET", "POST"])
def login():
    """User login"""
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return redirect(url_for("login"))
        
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM customers WHERE email = ?", (email,)).fetchone()
        conn.close()
        
        # Verify password using check_password_hash (secure comparison with salt)
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            session['user_role'] = user['role']  # ← ADD THIS LINE!
            
            flash(f"Welcome back, {user['name']}!", "success")
            
            # Redirect to 'next' page if it exists, otherwise go to index
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash("Invalid email or password.", "danger")
            return redirect(url_for("login"))
    
    return render_template("login.html", year=datetime.now().year)


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
        
        # Password change (optional)
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        try:
            # If user wants to change password
            if new_password:
                # Get current user data
                user = conn.execute("SELECT * FROM customers WHERE id = ?", (session['user_id'],)).fetchone()
                
                # Verify current password
                if not current_password:
                    flash('Please enter your current password to change it.', 'danger')
                    conn.close()
                    return redirect(url_for('edit_account'))
                
                if not check_password_hash(user['password'], current_password):
                    flash('Current password is incorrect.', 'danger')
                    conn.close()
                    return redirect(url_for('edit_account'))
                
                # Check passwords match
                if new_password != confirm_password:
                    flash('New passwords do not match.', 'danger')
                    conn.close()
                    return redirect(url_for('edit_account'))
                
                # SERVER-SIDE PASSWORD VALIDATION (using same function as registration)
                password_errors = validate_password(new_password, name, user['email'])
                if password_errors:
                    for error in password_errors:
                        flash(error, 'danger')
                    conn.close()
                    return redirect(url_for('edit_account'))
                
                # Hash new password
                hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256', salt_length=16)
                
                # Update with new password
                conn.execute("""
                    UPDATE customers 
                    SET name = ?, phone = ?, address = ?, city = ?, state = ?, postcode = ?, password = ?
                    WHERE id = ?
                """, (name, phone, address, city, state, postcode, hashed_password, session['user_id']))
                
                flash('✅ Profile and password updated successfully!', 'success')
            else:
                # Update without changing password
                conn.execute("""
                    UPDATE customers 
                    SET name = ?, phone = ?, address = ?, city = ?, state = ?, postcode = ?
                    WHERE id = ?
                """, (name, phone, address, city, state, postcode, session['user_id']))
                
                flash('✅ Profile updated successfully!', 'success')
            
            conn.commit()
            session['user_name'] = name
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



@app.route("/activity-log")
@login_required
def activity_log():
    """View activity log - Manager only"""
    if session.get('user_role') != 'manager':
        flash("Access denied. Manager privileges required.", "danger")
        return redirect(url_for('index'))
    
    # Get filter parameters
    filter_action = request.args.get('action', '')
    filter_user = request.args.get('user', '')
    search_query = request.args.get('search', '')
    
    conn = get_db_connection()
    
    # Build query
    query = "SELECT * FROM activity_log WHERE 1=1"
    params = []
    
    if filter_action:
        query += " AND action = ?"
        params.append(filter_action)
    
    if filter_user:
        query += " AND user_name = ?"
        params.append(filter_user)
    
    if search_query:
        query += " AND (product_name LIKE ? OR product_sku LIKE ? OR details LIKE ?)"
        params.extend([f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'])
    
    query += " ORDER BY timestamp DESC LIMIT 200"
    
    logs = conn.execute(query, params).fetchall()
    
    # Get unique users for filter
    all_users = conn.execute("""
        SELECT DISTINCT user_name FROM activity_log ORDER BY user_name
    """).fetchall()
    
    conn.close()
    
    return render_template('activity_log.html',
                         logs=logs,
                         all_users=all_users,
                         filter_action=filter_action,
                         filter_user=filter_user,
                         search_query=search_query,
                         year=datetime.now().year)
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
        
        # Calculate discounted price
        original_price = product['price']
        discount_percentage = product['discount_percentage'] if product['discount_percentage'] else 0
        
        if discount_percentage > 0:
            final_price = original_price * (1 - discount_percentage / 100)
        else:
            final_price = original_price
        
        # Initialize cart if it doesn't exist
        if 'cart' not in session:
            session['cart'] = {}
        
        # Create cart key
        cart_key = str(product_id)
        
        # Add or update item in cart - NOW WITH NAME AND IMAGE
        if cart_key in session['cart']:
            session['cart'][cart_key]['quantity'] += quantity
        else:
            session['cart'][cart_key] = {
                'product_id': product_id,
                'name': product['name'],              # ADD THIS
                'image': product['image'],            # ADD THIS
                'quantity': quantity,
                'price': final_price,
                'original_price': original_price,
                'discount_percentage': discount_percentage
            }
        
        # Mark session as modified
        session.modified = True
        
        # Calculate cart count
        cart_count = sum(item['quantity'] for item in session['cart'].values())
        
        return jsonify({
            'success': True,
            'message': f'Added {product["name"]} to cart',
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
    """Return mini cart HTML fragment"""
    cart = session.get('cart', {})
    cart_items = {}
    total = 0
    
    if cart:
        conn = get_db_connection()
        for cart_key, item_data in cart.items():
            product_id = item_data['product_id']
            quantity = item_data['quantity']
            
            product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
            if product:
                # Use stored price from cart (which is already discounted)
                price = item_data.get('price', product['price'])
                subtotal = price * quantity
                
                cart_items[cart_key] = {
                    'id': product_id,
                    'cart_key': cart_key,
                    'name': product['name'],
                    'price': price,
                    'quantity': quantity,
                    'subtotal': subtotal,
                    'image': product['image']
                }
                total += subtotal
        conn.close()
    
    # Render the mini cart partial and return HTML
    return render_template('partials/mini_cart.html', 
                         cart=cart_items,
                         total=total,
                         count=len(cart))


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
                # Use stored price from cart (which is already discounted)
                price = item_data.get('price', product['price'])
                item_subtotal = price * quantity
                
                cart_items.append({
                    'product_id': product_id,
                    'sku': product['sku'],
                    'name': product['name'],
                    'price': price,  # Use discounted price
                    'original_price': item_data.get('original_price', product['price']),
                    'discount_percentage': item_data.get('discount_percentage', 0),
                    'quantity': quantity,
                    'subtotal': item_subtotal,
                    'image': product['image'],
                    'stock': product['stock']
                })
                subtotal += item_subtotal
        conn.close()
    
    # Dynamic Shipping Calculation Algorithm
    FREE_SHIPPING_THRESHOLD = 80.00
    
    if subtotal >= FREE_SHIPPING_THRESHOLD:
        shipping = 0  # FREE shipping
        shipping_message = "FREE Shipping!"
    elif subtotal == 0:
        shipping = 0
        shipping_message = "Add items to calculate shipping"
    else:
        # Dynamic shipping based on cart value
        # Base rate: $15
        # Reduced as cart value increases
        # Formula: Base rate - (discount based on how close to threshold)
        BASE_SHIPPING = 15.00
        DISCOUNT_RATE = 0.05  # 5% discount per $10 towards threshold
        
        # Calculate how much customer needs to reach free shipping
        amount_to_free_shipping = FREE_SHIPPING_THRESHOLD - subtotal
        
        # Calculate discount based on cart value
        discount_factor = subtotal / FREE_SHIPPING_THRESHOLD
        shipping_discount = BASE_SHIPPING * discount_factor * 0.3  # Max 30% discount on shipping
        
        shipping = max(BASE_SHIPPING - shipping_discount, 8.00)  # Minimum $8 shipping
        shipping = round(shipping, 2)
        shipping_message = f"${amount_to_free_shipping:.2f} away from FREE shipping!"
    
    # Calculate GST and total
    tax_rate = 0.10
    tax = subtotal * tax_rate
    total = subtotal + tax + shipping
    
    return render_template('cart.html',
                         cart_items=cart_items,
                         subtotal=subtotal,
                         tax=tax,
                         shipping=shipping,
                         shipping_message=shipping_message,
                         free_shipping_threshold=FREE_SHIPPING_THRESHOLD,
                         total=total,
                         year=datetime.now().year)


# Update the checkout route (around line 650)
@app.route("/checkout")
@login_required  # ADD THIS LINE
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
            # Use stored price from cart (which is already discounted)
            price = item_data.get('price', product['price'])
            item_subtotal = price * quantity
            
            cart_items.append({
                'sku': product['sku'],
                'name': product['name'],
                'price': price,  # Use discounted price
                'original_price': item_data.get('original_price', product['price']),
                'discount_percentage': item_data.get('discount_percentage', 0),
                'quantity': quantity,
                'subtotal': item_subtotal,
                'image': product['image']
            })
            subtotal += item_subtotal
    
    conn.close()
    
    # Dynamic Shipping Calculation Algorithm
    FREE_SHIPPING_THRESHOLD = 80.00
    
    if subtotal >= FREE_SHIPPING_THRESHOLD:
        shipping = 0
        shipping_message = "FREE Shipping!"
    else:
        BASE_SHIPPING = 15.00
        discount_factor = subtotal / FREE_SHIPPING_THRESHOLD
        shipping_discount = BASE_SHIPPING * discount_factor * 0.3
        shipping = max(BASE_SHIPPING - shipping_discount, 8.00)
        shipping = round(shipping, 2)
        amount_to_free_shipping = FREE_SHIPPING_THRESHOLD - subtotal
        shipping_message = f"${amount_to_free_shipping:.2f} away from FREE shipping!"
    
    # Calculate GST and total
    tax_rate = 0.10
    tax = subtotal * tax_rate
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
                'email': user['email'],
                'phone': user['phone'] if user['phone'] else '',
                'address': user['address'] if user['address'] else '',
                'city': user['city'] if user['city'] else '',
                'state': user['state'] if user['state'] else '',
                'postcode': user['postcode'] if user['postcode'] else ''
            }
    
    return render_template('checkout.html',
                         cart_items=cart_items,
                         subtotal=subtotal,
                         tax=tax,
                         shipping=shipping,
                         shipping_message=shipping_message,
                         free_shipping_threshold=FREE_SHIPPING_THRESHOLD,
                         total=total,
                         user_info=user_info,
                         year=datetime.now().year)


# Update the place_order route (around line 720)
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
                
                # USE THE STORED DISCOUNTED PRICE FROM CART
                price = item_data.get('price', product['price'])
                item_subtotal = price * quantity
                
                order_items.append({
                    'sku': product['sku'],
                    'name': product['name'],
                    'price': price,  # This is the discounted price
                    'quantity': quantity,
                    'subtotal': item_subtotal
                })
                subtotal += item_subtotal
        
        # Dynamic Shipping Calculation Algorithm
        FREE_SHIPPING_THRESHOLD = 80.00
        
        if subtotal >= FREE_SHIPPING_THRESHOLD:
            shipping_cost = 0
        else:
            BASE_SHIPPING = 15.00
            discount_factor = subtotal / FREE_SHIPPING_THRESHOLD
            shipping_discount = BASE_SHIPPING * discount_factor * 0.3
            shipping_cost = max(BASE_SHIPPING - shipping_discount, 8.00)
            shipping_cost = round(shipping_cost, 2)
        
        # Calculate GST and total
        tax_rate = 0.10
        tax = subtotal * tax_rate
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


@app.route("/membership")
def membership():
    return render_template("member.html", year=datetime.now().year)


# ===========================
# ADMIN ROUTES - Products
# ===========================

@app.route("/admin/product/add", methods=['GET', 'POST'])
@admin_required
def add_product():
    """Add a new product"""
    if request.method == 'POST':
        sku = request.form.get('sku')
        name = request.form.get('name')
        category = request.form.get('category')
        subcategory = request.form.get('subcategory')
        price = request.form.get('price')
        description = request.form.get('description')
        stock = request.form.get('stock', 0)
        discount_percentage = request.form.get('discount_percentage', 0)
        
        # Get taste profile data (only for beans)
        taste_sweetness = request.form.get('taste_sweetness') if category == 'beans' else None
        taste_aroma = request.form.get('taste_aroma') if category == 'beans' else None
        taste_body = request.form.get('taste_body') if category == 'beans' else None
        
        # Convert empty strings to None
        taste_sweetness = int(taste_sweetness) if taste_sweetness and taste_sweetness != '' else None
        taste_aroma = int(taste_aroma) if taste_aroma and taste_aroma != '' else None
        taste_body = int(taste_body) if taste_body and taste_body != '' else None

        image = request.files.get('image')
        image_filename = None
        if image and image.filename:
            if allowed_file(image.filename):
                ext = image.filename.rsplit('.', 1)[1].lower()
                image_filename = f"{sku}.{ext}"
                STATIC_IMG_DIR.mkdir(parents=True, exist_ok=True)
                image.save(STATIC_IMG_DIR / image_filename)
            else:
                flash("Invalid image type. Allowed: jpg, png, webp, gif, avif", "danger")
                return redirect(request.url)

        conn = get_db_connection()
        
        existing = conn.execute("SELECT id FROM products WHERE sku = ?", (sku,)).fetchone()
        if existing:
            flash(f"⚠️ A product with SKU '{sku}' already exists.", "warning")
            conn.close()
            return redirect(url_for('add_product'))

        try:
            conn.execute("""
                INSERT INTO products (sku, name, category, subcategory, price, description, stock, image, discount_percentage, 
                                     taste_sweetness, taste_aroma, taste_body)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (sku, name, category, subcategory, price, description, stock, image_filename, discount_percentage,
                  taste_sweetness, taste_aroma, taste_body))
            conn.commit()

            log_activity(
                action='PRODUCT_ADDED',
                product_id=None,
                product_sku=sku,
                product_name=name,
                details=f"Added {name} ({sku}) - Category: {category}, Price: ${price}, Stock: {stock}"
            )

            flash(f"✅ Product '{name}' added successfully!", "success")
            conn.close()
            return redirect(url_for('edit_product'))
        except sqlite3.Error as e:
            flash(f"❌ Error adding product: {e}", "danger")
            conn.close()
            return redirect(url_for('add_product'))

    return render_template('manage_product.html', year=datetime.now().year)


@app.route("/admin/product/edit", methods=['GET', 'POST'])
@admin_required
def edit_product():
    """Edit an existing product"""
    
    # Get filter parameters
    search = request.args.get('search', '').strip()
    category_filter = request.args.get('category', '')
    sku = request.args.get('sku', '')
    
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
        discount_percentage = request.form.get('discount_percentage', 0)
        
        # Get taste profile data (only for beans)
        taste_sweetness = request.form.get('taste_sweetness') if category == 'beans' else None
        taste_aroma = request.form.get('taste_aroma') if category == 'beans' else None
        taste_body = request.form.get('taste_body') if category == 'beans' else None
        
        # Convert empty strings to None
        taste_sweetness = int(taste_sweetness) if taste_sweetness and taste_sweetness != '' else None
        taste_aroma = int(taste_aroma) if taste_aroma and taste_aroma != '' else None
        taste_body = int(taste_body) if taste_body and taste_body != '' else None

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
                    return redirect(url_for('edit_product', sku=old_sku, search=search, category=category_filter))
            
            if image_filename:
                conn.execute("""
                    UPDATE products
                    SET sku = ?, name = ?, category = ?, subcategory = ?, price = ?, description = ?, stock = ?, image = ?, discount_percentage = ?,
                        taste_sweetness = ?, taste_aroma = ?, taste_body = ?
                    WHERE sku = ?
                """, (new_sku, name, category, subcategory, price, description, stock, image_filename, discount_percentage,
                      taste_sweetness, taste_aroma, taste_body, old_sku))
            else:
                conn.execute("""
                    UPDATE products
                    SET sku = ?, name = ?, category = ?, subcategory = ?, price = ?, description = ?, stock = ?, discount_percentage = ?,
                        taste_sweetness = ?, taste_aroma = ?, taste_body = ?
                    WHERE sku = ?
                """, (new_sku, name, category, subcategory, price, description, stock, discount_percentage,
                      taste_sweetness, taste_aroma, taste_body, old_sku))
            conn.commit()

            log_activity(
                action='PRODUCT_EDITED',
                product_id=None,
                product_sku=new_sku,
                product_name=name,
                details=f"Updated {name} ({new_sku})" + (f" - SKU changed from {old_sku}" if sku_changed else f" - Price: ${price}, Stock: {stock}")
            )

            flash("✅ Product updated successfully.", "success")
            conn.close()
            # Redirect WITH search parameters preserved
            return redirect(url_for('edit_product', sku=new_sku, search=search, category=category_filter))
        except sqlite3.Error as e:
            flash(f"❌ Error updating product: {e}", "danger")
            conn.close()
            return redirect(url_for('edit_product', sku=old_sku, search=search, category=category_filter))

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
        
                
        log_activity(
            action='PRODUCT_DELETED',
            product_id=product['id'],
            product_sku=product['sku'],
            product_name=product['name'],
            details=f"Deleted {product['name']} ({product['sku']}) - Category: {product['category']}, Stock: {product['stock']}"
        )

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
# ADMIN ROUTES - ORDERS
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
    
def init_reports_db():
    """Initialize bug reports and missing products tables"""
    conn = get_db_connection()
    
    # Drop old missing_products table if it exists (to add new columns)
    conn.execute('DROP TABLE IF EXISTS missing_products')
    
    # Create bug_reports table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS bug_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            device TEXT,
            severity TEXT NOT NULL,
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES customers (id)
        )
    ''')
    
    # Create missing_products table with all columns
    conn.execute('''
        CREATE TABLE IF NOT EXISTS missing_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            product_name TEXT NOT NULL,
            product_category TEXT NOT NULL,
            description TEXT NOT NULL,
            additional_info TEXT,
            priority TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES customers (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Reports tables initialized")

def add_discount_column():
    """Add discount column to products table if it doesn't exist"""
    conn = get_db_connection()
    try:
        # Check if discount column exists
        cursor = conn.execute("PRAGMA table_info(products)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'discount_percentage' not in columns:
            conn.execute('''
                ALTER TABLE products 
                ADD COLUMN discount_percentage INTEGER DEFAULT 0
            ''')
            conn.commit()
            print("✅ Discount column added to products table")
        else:
            print("ℹ️  Discount column already exists")
    except Exception as e:
        print(f"Error adding discount column: {e}")
    finally:
        conn.close()

def set_product_discount():
    """Set 10% discount ONLY on Breville Barista Express (M-BRE003)"""
    conn = get_db_connection()
    try:
        # First, clear ALL discounts
        conn.execute('UPDATE products SET discount_percentage = 0')
        conn.commit()
        print("✅ All discounts cleared")
        
        # Then set discount ONLY on Breville Barista Express with SKU M-BRE003
        conn.execute('''
            UPDATE products 
            SET discount_percentage = 10 
            WHERE sku = 'M-BRE003'
        ''')
        conn.commit()
        
        # Verify which products have discounts
        discounted = conn.execute('''
            SELECT id, name, sku, price, discount_percentage 
            FROM products 
            WHERE discount_percentage > 0
        ''').fetchall()
        
        if discounted:
            for product in discounted:
                original_price = product['price']
                discounted_price = original_price * (1 - product['discount_percentage'] / 100)
                print(f"✅ Discount applied to: {product['name']}")
                print(f"   ID: {product['id']}, SKU: {product['sku']}")
                print(f"   Original Price: ${original_price:.2f}")
                print(f"   Discounted Price: ${discounted_price:.2f} ({product['discount_percentage']}% off)")
        else:
            print("⚠️  Product with SKU M-BRE003 not found in database")
            
    except Exception as e:
        print(f"❌ Error setting discount: {e}")
    finally:
        conn.close()


def add_beans_subcategories():
    """Update existing beans products with subcategories"""
    conn = get_db_connection()
    try:
        # Check if any beans products exist without subcategories
        beans = conn.execute('''
            SELECT id, name FROM products 
            WHERE category = 'beans' AND (subcategory IS NULL OR subcategory = '')
        ''').fetchall()
        
        if beans:
            print(f"Found {len(beans)} beans products without subcategories")
            # You can manually categorize them or set a default
            # For now, set them all to 'coffee-beans' as default
            conn.execute('''
                UPDATE products 
                SET subcategory = 'coffee-beans' 
                WHERE category = 'beans' AND (subcategory IS NULL OR subcategory = '')
            ''')
            conn.commit()
            print("✅ Updated beans products with default subcategory 'coffee-beans'")
        else:
            print("ℹ️  All beans products already have subcategories")
            
    except Exception as e:
        print(f"❌ Error updating beans subcategories: {e}")
    finally:
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


@app.route("/cart/items")
def cart_items_api():
    """API endpoint to get cart items for mini cart"""
    cart = session.get('cart', {})
    items = []
    total = 0
    
    if cart:
        conn = get_db_connection()
        for cart_key, item_data in cart.items():
            product_id = item_data['product_id']
            quantity = item_data['quantity']
            
            product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
            if product:
                price = item_data.get('price', product['price'])
                subtotal = price * quantity
                
                items.append({
                    'product_id': product_id,
                    'name': product['name'],
                    'price': price,
                    'quantity': quantity,
                    'subtotal': subtotal,
                    'image': product['image']
                })
                total += subtotal
        conn.close()
    
    return jsonify({
        'items': items,
        'total': total,
        'count': len(cart)
    })


@app.route("/coming-soon")
def coming_soon():
    """Coming soon page"""
    return render_template("coming_soon.html", year=datetime.now().year)

# ===========================
# SEARCH UTILITY FUNCTIONS
# ===========================

def calculate_similarity(s1, s2):
    """Calculate similarity ratio between two strings (0-1)"""
    return difflib.SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

def get_search_suggestions(query, all_terms):
    """Get 'Did you mean?' suggestions for potential typos"""
    suggestions = []
    query_lower = query.lower().strip()
    
    # Filter out single characters and very short terms (less than 2 characters)
    unique_terms = list(set([term for term in all_terms if term and len(term) > 2]))
    
    for term in unique_terms:
        if not term:  # Skip empty terms
            continue
        term_lower = term.lower().strip()
        
        # Skip if exact match
        if query_lower == term_lower:
            continue
        
        # Skip single character terms
        if len(term) <= 2:
            continue
        
        # Calculate similarity
        similarity = calculate_similarity(query_lower, term_lower)
        
        # Lower threshold for better typo detection (50% instead of 60%)
        # But require minimum length similarity
        if 0.5 <= similarity < 1.0 and len(term) >= len(query) - 2:
            suggestions.append((term, similarity))
        
        # Also check if query is contained in term or vice versa
        # e.g., "summar" in "summer"
        # But only if both are reasonable length (more than 3 chars)
        if len(query) > 3 and len(term) > 3:
            if query_lower in term_lower or term_lower in query_lower:
                if (term, similarity) not in suggestions:
                    suggestions.append((term, 0.9))  # High similarity for partial matches
    
    # Sort by similarity and return top 3 unique suggestions
    suggestions.sort(key=lambda x: x[1], reverse=True)
    unique_suggestions = []
    seen = set()
    for s, _ in suggestions:
        s_lower = s.lower()
        if s_lower not in seen and len(s) > 2:  # Double-check no short terms
            unique_suggestions.append(s)
            seen.add(s_lower)
        if len(unique_suggestions) >= 3:
            break
    
    return unique_suggestions

def expand_query_with_synonyms(query):
    """Expand search query with common synonyms"""
    synonyms = {
        'espresso': ['coffee', 'espresso machine', 'barista'],
        'coffee': ['espresso', 'brew', 'java', 'caffeine'],
        'machine': ['maker', 'brewer', 'equipment'],
        'beans': ['grounds', 'roast', 'coffee beans'],
        'grinder': ['mill', 'burr grinder'],
        'milk': ['frother', 'steamer', 'foam'],
        'frother': ['milk frother', 'steamer', 'milk steamer', 'foam maker'],
        'cup': ['mug', 'glass'],
        'roast': ['beans', 'blend', 'coffee'],
        'blend': ['mix', 'roast', 'beans'],
        'dark': ['bold', 'strong', 'intense'],
        'light': ['mild', 'smooth', 'medium'],
        'summer': ['seasonal', 'limited'],
        'summar': ['summer'],  # Common typo
        'winter': ['seasonal', 'limited'],
        'automatic': ['auto', 'electric'],
        'manual': ['hand', 'lever'],
        'brewville': ['breville'],  # Common typo
        'expresso': ['espresso'],   # Common typo
    }
    
    # Get all words from query
    words = query.lower().split()
    expanded_terms = set(words)
    
    # Add synonyms
    for word in words:
        if word in synonyms:
            expanded_terms.update(synonyms[word])
    
    return list(expanded_terms)

@app.route("/search")
def search():
    """Advanced search with typo tolerance, synonyms, and suggestions"""
    query = request.args.get('q', '').strip()
    category_filter = request.args.get('category', '').strip().lower()
    
    if not query:
        return render_template('search_results.html', 
                             products=[], 
                             query='', 
                             category_filter=category_filter,
                             suggestions=[],
                             year=datetime.now().year)
    
    conn = get_db_connection()
    
    # Normalize the search query
    normalized_query = ' '.join(query.lower().split())
    no_space_query = normalized_query.replace(' ', '')
    
    # Expand query with synonyms for better matching
    expanded_terms = expand_query_with_synonyms(normalized_query)
    
    # Get all unique product names and brands for typo detection
    all_products = conn.execute("SELECT DISTINCT name, brand FROM products").fetchall()
    all_terms = []
    for p in all_products:
        if p['name']:
            all_terms.append(p['name'])
            # Only add individual words if they're meaningful (longer than 3 chars)
            words = p['name'].split()
            all_terms.extend([w for w in words if len(w) > 3])
        if p['brand']:
            all_terms.append(p['brand'])
    
    # ALWAYS get suggestions for potential typos (whether results found or not)
    suggestions = get_search_suggestions(normalized_query, all_terms)
    
    # Build comprehensive search with typo tolerance and synonyms
    if category_filter:
        # Create dynamic SQL with synonym matching
        synonym_conditions = []
        synonym_params = []
        for term in expanded_terms:
            synonym_conditions.append("LOWER(p.name) LIKE ?")
            synonym_conditions.append("LOWER(p.description) LIKE ?")
            synonym_conditions.append("LOWER(p.brand) LIKE ?")
            synonym_params.extend([f'%{term}%', f'%{term}%', f'%{term}%'])
        
        synonym_sql = " OR ".join(synonym_conditions) if synonym_conditions else "1=0"
        
        sql = f"""
            SELECT DISTINCT p.* FROM products p
            WHERE p.category = ?
            AND (
                -- Exact match (case-insensitive)
                LOWER(p.name) LIKE ? OR
                LOWER(p.description) LIKE ? OR
                LOWER(p.brand) LIKE ? OR
                LOWER(p.subcategory) LIKE ? OR
                
                -- Space-insensitive match
                REPLACE(LOWER(p.name), ' ', '') LIKE ? OR
                REPLACE(LOWER(p.description), ' ', '') LIKE ? OR
                REPLACE(LOWER(p.brand), ' ', '') LIKE ? OR
                
                -- Partial word match
                LOWER(p.name) LIKE ? OR
                LOWER(p.description) LIKE ? OR
                LOWER(p.brand) LIKE ? OR
                
                -- Synonym matching
                {synonym_sql}
            )
            ORDER BY
                CASE
                    WHEN LOWER(p.name) = ? THEN 1
                    WHEN LOWER(p.brand) = ? THEN 2
                    WHEN LOWER(p.name) LIKE ? THEN 3
                    WHEN LOWER(p.brand) LIKE ? THEN 4
                    ELSE 5
                END,
                p.name ASC
        """
        params = [
            category_filter,
            f'%{normalized_query}%', f'%{normalized_query}%', f'%{normalized_query}%', f'%{normalized_query}%',
            f'%{no_space_query}%', f'%{no_space_query}%', f'%{no_space_query}%',
            f'%{normalized_query}%', f'%{normalized_query}%', f'%{normalized_query}%',
            *synonym_params,
            normalized_query, normalized_query, f'{normalized_query}%', f'{normalized_query}%'
        ]
    else:
        # Create dynamic SQL with synonym matching
        synonym_conditions = []
        synonym_params = []
        for term in expanded_terms:
            synonym_conditions.append("LOWER(p.name) LIKE ?")
            synonym_conditions.append("LOWER(p.description) LIKE ?")
            synonym_conditions.append("LOWER(p.brand) LIKE ?")
            synonym_params.extend([f'%{term}%', f'%{term}%', f'%{term}%'])
        
        synonym_sql = " OR ".join(synonym_conditions) if synonym_conditions else "1=0"
        
        sql = f"""
            SELECT DISTINCT p.* FROM products p
            WHERE
                -- Exact match (case-insensitive)
                LOWER(p.name) LIKE ? OR
                LOWER(p.description) LIKE ? OR
                LOWER(p.brand) LIKE ? OR
                LOWER(p.category) LIKE ? OR
                LOWER(p.subcategory) LIKE ? OR
                
                -- Space-insensitive match
                REPLACE(LOWER(p.name), ' ', '') LIKE ? OR
                REPLACE(LOWER(p.description), ' ', '') LIKE ? OR
                REPLACE(LOWER(p.brand), ' ', '') LIKE ? OR
                
                -- Partial word match
                LOWER(p.name) LIKE ? OR
                LOWER(p.description) LIKE ? OR
                LOWER(p.brand) LIKE ? OR
                LOWER(p.category) LIKE ? OR
                
                -- Synonym matching
                {synonym_sql}
            ORDER BY
                CASE
                    WHEN LOWER(p.name) = ? THEN 1
                    WHEN LOWER(p.brand) = ? THEN 2
                    WHEN LOWER(p.name) LIKE ? THEN 3
                    WHEN LOWER(p.brand) LIKE ? THEN 4
                    ELSE 5
                END,
                p.name ASC
        """
        params = [
            f'%{normalized_query}%', f'%{normalized_query}%', f'%{normalized_query}%', 
            f'%{normalized_query}%', f'%{normalized_query}%',
            f'%{no_space_query}%', f'%{no_space_query}%', f'%{no_space_query}%',
            f'%{normalized_query}%', f'%{normalized_query}%', f'%{normalized_query}%', f'%{normalized_query}%',
            *synonym_params,
            normalized_query, normalized_query, f'{normalized_query}%', f'{normalized_query}%'
        ]
    
    products = conn.execute(sql, params).fetchall()
    conn.close()
    
    return render_template('search_results.html', 
                         products=products, 
                         query=query,
                         category_filter=category_filter,
                         suggestions=suggestions,
                         year=datetime.now().year)

@app.route("/brewing-guide")
def brewing_guide():
    return render_template("brewing_guide.html", year=datetime.now().year)

@app.route("/manifest.json")
def manifest():
    """Serve PWA manifest"""
    return app.send_static_file('manifest.json')

if __name__ == "__main__":
    init_db()
    init_orders_db()
    init_reports_db() 
    add_discount_column()
    add_beans_subcategories()
    app.run(debug=True)