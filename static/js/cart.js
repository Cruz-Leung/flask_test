console.log('✅ cart.js file loaded successfully!');

const Cart = {
    // Add product to cart
    async add(productId) {
        console.log('Cart.add called with productId:', productId);
        
        try {
            const response = await fetch('/cart/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ product_id: parseInt(productId) })
            });

            const data = await response.json();
            console.log('Server response:', data);
            
            if (data.success) {
                // Show success message
                this.showNotification('✅ Product added to cart!', 'success');
                // Refresh mini cart
                MiniCart.refresh();
            } else {
                this.showNotification('❌ ' + (data.message || 'Failed to add product'), 'error');
            }
        } catch (error) {
            console.error('Error adding to cart:', error);
            this.showNotification('❌ Error adding to cart', 'error');
        }
    },

    // Update quantity in cart
    async update(productId, quantity) {
        console.log('Cart.update called:', productId, quantity);
        
        try {
            const response = await fetch('/cart/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    product_id: parseInt(productId),
                    quantity: parseInt(quantity)
                })
            });

            const data = await response.json();
            
            if (data.success) {
                // Reload page to show updated cart
                window.location.reload();
            } else {
                this.showNotification('❌ ' + (data.message || 'Failed to update cart'), 'error');
            }
        } catch (error) {
            console.error('Error updating cart:', error);
            this.showNotification('❌ Error updating cart', 'error');
        }
    },

    // Remove product from cart
    async remove(productId) {
        console.log('Cart.remove called:', productId);
        
        try {
            const response = await fetch('/cart/remove', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ product_id: parseInt(productId) })
            });

            const data = await response.json();
            
            if (data.success) {
                // Reload page to show updated cart
                window.location.reload();
            } else {
                this.showNotification('❌ ' + (data.message || 'Failed to remove product'), 'error');
            }
        } catch (error) {
            console.error('Error removing from cart:', error);
            this.showNotification('❌ Error removing from cart', 'error');
        }
    },

    // Show notification
    showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'success' ? 'success' : 'danger'} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 80px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
};

const MiniCart = {
    // Refresh mini cart display
    async refresh() {
        console.log('MiniCart.refresh called');
        
        try {
            const response = await fetch('/cart/mini');
            const data = await response.json();
            
            console.log('Mini cart data:', data);
            
            if (data.success) {
                this.render(data.cart_items, data.total);
            }
        } catch (error) {
            console.error('Error refreshing mini cart:', error);
        }
    },

    // Render mini cart content
    render(items, total) {
        console.log('MiniCart.render called with', items.length, 'items');
        
        const miniCartBody = document.querySelector('.mini-cart-body');
        const cartCount = document.getElementById('mini-cart-count');
        
        if (!miniCartBody || !cartCount) {
            console.error('Mini cart elements not found!');
            return;
        }

        // Update cart count
        const totalItems = items.reduce((sum, item) => sum + item.quantity, 0);
        cartCount.textContent = totalItems;

        // Render cart items
        if (items.length === 0) {
            miniCartBody.innerHTML = '<div class="mini-cart-empty">Your cart is empty.</div>';
        } else {
            let html = '';
            items.forEach(item => {
                html += `
                    <div class="mini-cart-item d-flex mb-2 pb-2 border-bottom">
                        <img src="/static/img/${item.image || 'placeholder.jpg'}" 
                             alt="${item.name}" 
                             style="width: 50px; height: 50px; object-fit: cover;" 
                             class="me-2 rounded">
                        <div class="flex-grow-1">
                            <h6 class="mb-0 small">${item.name}</h6>
                            <small class="text-muted">Qty: ${item.quantity} × $${item.price.toFixed(2)}</small>
                        </div>
                        <button class="btn btn-sm btn-link text-danger" 
                                onclick="Cart.remove(${item.product_id})"
                                title="Remove">
                            ×
                        </button>
                    </div>
                `;
            });
            html += `
                <div class="mini-cart-total mt-2 pt-2 border-top">
                    <strong>Total: $${total.toFixed(2)}</strong>
                </div>
            `;
            miniCartBody.innerHTML = html;
        }
    }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 DOMContentLoaded - Initializing cart system');
    
    // Add click handlers to all "Add to Cart" buttons
    const buttons = document.querySelectorAll('.add-to-cart-btn');
    console.log(`Found ${buttons.length} add-to-cart buttons`);
    
    buttons.forEach((button, index) => {
        const productId = button.getAttribute('data-product-id');
        console.log(`Button ${index}: product ID = ${productId}`);
        
        button.addEventListener('click', (e) => {
            e.preventDefault();
            console.log('🛒 Button clicked! Product ID:', productId);
            
            if (productId) {
                Cart.add(productId);
            } else {
                console.error('❌ No product ID found on button!');
            }
        });
    });

    // Refresh mini cart on page load
    MiniCart.refresh();
    console.log('✅ Cart system initialized');
});

console.log('✅ Cart and MiniCart objects defined');

