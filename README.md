# Cruzy Coffee Co. - Flask E-Commerce Web App

Welcome to Cruzy Coffee Co, a full-stack e-commerce platform for coffee lovers. 
This web application lets users browse and purchase coffee machines, beans, and accessories, manage their accounts, and enjoy a seamless shopping experience. 
Admins and managers have access to product management, order tracking, and reporting features.

---

## Features

- **Product Catalog:** Browse coffee machines, beans, and accessories with category and subcategory filtering.
- **Shopping Cart:** Add, update, and remove items; view mini cart; dynamic shipping calculation.
- **Checkout & Orders:** Secure checkout, order confirmation, and order history.
- **User Authentication:** Registration, login, logout, and account management with password hashing.
- **Admin Dashboard:** Add/edit/delete products, manage discounts, view orders, and staff management.
- **Bug & Product Reporting:** Users can report bugs and request new products.
- **Search:** Advanced search with typo tolerance, synonyms, and suggestions.
- **Progressive Web App (PWA):** Installable on desktop and mobile, offline support.
- **Responsive Design:** Mobile-friendly layout using Bootstrap 5 and custom CSS.

---

## Technologies Used

- **Flask:** Python web framework for routing, templates, and backend logic.
- **SQLite:** Lightweight database for storing products, users, orders, and reports.
- **HTML/CSS/Bootstrap:** Frontend structure and styling.
- **JavaScript:** Cart functionality, AJAX, and interactive UI.
- **Jinja2:** Templating engine for dynamic HTML.
- **Werkzeug:** Password hashing and security.
- **PWA:** Manifest and Service Worker for installable app and offline support.

---

## Project Structure

```
flask_test/
├── app.py                  # Main Flask application
├── store.db                # SQLite database
├── requirements.txt        # Python dependencies
├── static/
│   ├── css/styles.css      # Custom styles
│   ├── js/cart.js          # Cart logic
│   ├── img/                # Product and logo images
│   ├── manifest.json       # PWA manifest
│   └── sw.js               # Service Worker
├── templates/
│   ├── base.html           # Main layout
│   ├── index.html          # Homepage
│   ├── machines.html       # Machines catalog
│   ├── beans.html          # Beans catalog
│   ├── accessories.html    # Accessories catalog
│   ├── cart.html           # Shopping cart
│   ├── checkout.html       # Checkout page
│   ├── account.html        # User account
│   ├── edit_product.html   # Product editing
│   ├── manage_product.html # Product management
│   ├── brewing_guide.html  # Brewing guide for beginners
│   ├── report_bug.html     # Bug reporting
│   ├── request_product.html# Product request form
│   ├── admin_orders.html   # Admin order management
│   ├── admin_order_detail.html # Admin order detail
│   ├── manage_staff.html   # Staff management
│   ├── add_staff.html      # Add staff member
│   ├── edit_staff.html     # Edit staff member
│   ├── activity_log.html   # Manager activity log
│   ├── my_orders.html      # User order history
│   ├── order_confirmation.html # Order confirmation
│   ├── member.html         # Membership info
│   ├── about.html          # About page
│   ├── terms.html          # Terms and conditions
│   ├── reports.html        # Bug and product reports
│   ├── coming_soon.html    # Coming soon page
│   ├── search_results.html # Search results
│   └── errors/
│       ├── 403.html        # Forbidden error
│       ├── 404.html        # Not found error
│       └── 500.html        # Server error
```

---

## Setup & Installation

1. **Clone the repository:**
   ```
   git clone https://github.com/Cruz-Leung/flask_test.git
   cd flask_test
   ```

2. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

3. **Run the Flask server:**
   ```
   python3 app.py (mac)
   ```
   ```
   python app.py (windows)
   ```

5. **Access the site:**
   - Open your browser and go to http://127.0.0.1:5000

---

## Usage

- **Browse products:** Navigate through machines, beans, and accessories.
- **Add to cart:** Click on products to add them to your cart.
- **Checkout:** Fill in your details and place an order.
- **Account management:** Register, log in, and edit your profile.
- **Admin/Manager:** Log in with admin/manager credentials to manage products, orders, and staff.
- **Bug/Product reporting:** Submit feedback and requests via dedicated forms.
- **Install as App:** Use the browser’s install prompt to add the site to your device.

---

## License

This project is for educational purposes (school project).  

---

## Author

Cruz Leung  
12SEN School Project  
November 2025

---
