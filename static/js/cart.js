console.log('✅ cart.js loaded');

// Add to cart (simple version for product cards)
function addToCart(productId) {
    console.log('Adding product:', productId);
    
    fetch(`/cart/add/${productId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ quantity: 1 })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Response:', data);
        if (data.success) {
            updateCartCount(data.cart_count);
            showToast('Success', 'Item added to cart!', 'success');
            loadMiniCart();
        } else {
            showToast('Error', data.message || 'Failed to add item', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error', 'Could not add item to cart', 'danger');
    });
}

// Add to cart with custom quantity (for product detail page)
function addToCartDetail(productId) {
    const quantityInput = document.getElementById(`quantity-${productId}`);
    const quantity = parseInt(quantityInput.value) || 1;
    
    console.log('Adding product with quantity:', productId, quantity);
    
    fetch(`/cart/add/${productId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ quantity: quantity })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateCartCount(data.cart_count);
            showToast('Success', `${quantity} item(s) added to cart!`, 'success');
            quantityInput.value = 1;
            loadMiniCart();
        } else {
            showToast('Error', data.message || 'Failed to add item', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error', 'Could not add item to cart', 'danger');
    });
}

// Update cart count badge
function updateCartCount(count) {
    const cartCountElement = document.getElementById('mini-cart-count');
    if (cartCountElement) {
        cartCountElement.textContent = count;
        console.log('Cart count updated to:', count);
    } else {
        console.error('Cart count element not found');
    }
}

// Load mini cart dropdown
function loadMiniCart() {
    fetch('/cart/mini')
    .then(response => response.json())
    .then(data => {
        console.log('Mini cart data:', data);
        
        // Update cart count
        updateCartCount(data.count);
        
        const cartContent = document.getElementById('mini-cart-content');
        if (!cartContent) return;
        
        if (data.items && data.items.length > 0) {
            let html = '<div class="mini-cart--dark">';
            html += '<div class="mini-cart-header d-flex justify-content-between align-items-center">';
            html += '<strong>Cart</strong>';
            html += '<button type="button" class="btn-close btn-close-white" aria-label="Close" onclick="document.querySelector(\'#cartDropdown\').click()"></button>';
            html += '</div>';
            html += '<div class="mini-cart-body mt-2">';
            
            data.items.forEach(item => {
                html += `
                    <div class="d-flex align-items-center mb-3 pb-3 border-bottom">
                        <img src="/static/img/${item.image || 'placeholder.jpg'}" 
                             alt="${item.name}" 
                             class="rounded me-3" 
                             style="width: 50px; height: 50px; object-fit: cover;">
                        <div class="flex-grow-1">
                            <h6 class="mb-0 small">${item.name}</h6>
                            <small class="text-muted">Qty: ${item.quantity} × $${item.price.toFixed(2)}</small>
                        </div>
                        <div class="text-end">
                            <strong>$${item.subtotal.toFixed(2)}</strong>
                            <button class="btn btn-sm btn-link text-danger p-0 d-block" 
                                    onclick="removeFromCart('${item.cart_key}')">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </div>
                `;
            });
            
            html += '</div>';
            html += `<div class="border-top pt-3 mt-2">
                        <div class="d-flex justify-content-between mb-2">
                            <strong>Total:</strong>
                            <strong class="text-success">$${data.total.toFixed(2)}</strong>
                        </div>
                     </div>`;
            html += '<div class="mt-3 d-grid gap-2">';
            html += '<a href="/cart" class="btn btn-outline-dark btn-sm">View Cart</a>';
            html += '<a href="/checkout" class="btn btn-dark btn-sm">Checkout</a>';
            html += '</div>';
            html += '</div>';
            
            cartContent.innerHTML = html;
        } else {
            cartContent.innerHTML = `
                <div class="mini-cart--dark">
                    <div class="mini-cart-header d-flex justify-content-between align-items-center">
                        <strong>Cart</strong>
                        <button type="button" class="btn-close btn-close-white" aria-label="Close" onclick="document.querySelector('#cartDropdown').click()"></button>
                    </div>
                    <div class="mini-cart-body mt-2">
                        <div class="mini-cart-empty text-center py-4">Your cart is empty.</div>
                    </div>
                    <div class="mt-3 d-grid gap-2">
                        <a href="/cart" class="btn btn-outline-dark btn-sm">View Cart</a>
                        <a href="/checkout" class="btn btn-dark btn-sm">Checkout</a>
                    </div>
                </div>
            `;
        }
    })
    .catch(error => {
        console.error('Error loading mini cart:', error);
    });
}

// Remove from cart
function removeFromCart(cartKey) {
    fetch(`/cart/remove/${cartKey}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateCartCount(data.cart_count);
            loadMiniCart();
            showToast('Success', 'Item removed from cart', 'success');
        } else {
            showToast('Error', 'Failed to remove item', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error', 'An error occurred', 'danger');
    });
}

// Show toast notification
function showToast(title, message, type) {
    const bgColor = type === 'success' ? 'bg-success' : 'bg-danger';
    const icon = type === 'success' ? 'bi-check-circle-fill' : 'bi-exclamation-triangle-fill';
    
    const toast = document.createElement('div');
    toast.className = 'position-fixed bottom-0 end-0 p-3';
    toast.style.zIndex = '9999';
    toast.innerHTML = `
        <div class="toast show" role="alert">
            <div class="toast-header ${bgColor} text-white">
                <i class="bi ${icon} me-2"></i>
                <strong class="me-auto">${title}</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// Load mini cart on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, loading mini cart...');
    loadMiniCart();
    
    // Also update cart count immediately
    fetch('/cart/mini')
        .then(response => response.json())
        .then(data => {
            updateCartCount(data.count);
        })
        .catch(error => {
            console.error('Error getting cart count:', error);
        });
});