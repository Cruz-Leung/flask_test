console.log('✅ cart.js loaded');

// Add to cart from product detail page
function addToCartDetail(productId) {
    const quantityInput = document.getElementById(`quantity-${productId}`);
    const quantity = parseInt(quantityInput?.value) || 1;
    
    console.log('Adding to cart:', productId, 'Quantity:', quantity);
    
    fetch(`/cart/add/${productId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ quantity: quantity })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Cart response:', data);
        if (data.success) {
            alert(`✅ ${quantity} item(s) added to cart!`);
            // Reload page to update mini cart
            window.location.reload();
        } else {
            alert(data.message || 'Error adding to cart');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error adding to cart. Please try again.');
    });
}

// Change quantity on product detail page
function changeQuantity(productId, change) {
    const input = document.getElementById(`quantity-${productId}`);
    const currentValue = parseInt(input.value);
    const newValue = currentValue + change;
    const max = parseInt(input.max);
    const min = parseInt(input.min);
    
    if (newValue >= min && newValue <= max) {
        input.value = newValue;
    }
}

// Mini Cart functionality
const MiniCart = {
    updateCartCount: async function() {
        try {
            // Refresh the entire mini cart (count + content)
            await this.refreshMiniCart();
            
        } catch (error) {
            console.error('Error updating cart count:', error);
        }
    },
    
    refreshMiniCart: async function() {
        try {
            // Fetch the mini cart HTML from server
            const response = await fetch('/cart/mini');
            const html = await response.text();
            
            // Update the mini cart content
            const miniCartContent = document.getElementById('mini-cart-content');
            if (miniCartContent) {
                miniCartContent.innerHTML = html;
                console.log('✅ Mini cart content refreshed');
            }
            
            // Also update the cart count badge
            const countResponse = await fetch('/cart/count');
            const countData = await countResponse.json();
            const cartBadge = document.getElementById('mini-cart-count');
            if (cartBadge) {
                cartBadge.textContent = countData.count || 0;
            }
            
        } catch (error) {
            console.error('Error refreshing mini cart:', error);
        }
    }
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, loading mini cart...');
    MiniCart.updateCartCount();
});

// Make functions available globally
window.MiniCart = MiniCart;
window.addToCartDetail = addToCartDetail;
window.changeQuantity = changeQuantity;