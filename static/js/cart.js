<script>
const MiniCart = (() => {
  const contentEl = () => document.getElementById('mini-cart-content');
  const countEl = () => document.getElementById('mini-cart-count');

  async function refresh() {
    try {
      const [miniHtml, countData] = await Promise.all([
        fetch('/cart/mini', { credentials: 'same-origin' }).then(r => r.text()),
        fetch('/cart/count', { credentials: 'same-origin' }).then(r => r.json())
      ]);
      if (contentEl()) contentEl().innerHTML = miniHtml;
      if (countEl()) countEl().textContent = countData.count;
    } catch (e) {
      console.error('MiniCart refresh failed', e);
    }
  }

  return { refresh };
})();

async function addToCart(productId) {
  try {
    const res = await fetch(`/cart/add/${productId}`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest' 
      },
      credentials: 'same-origin'
    });
    
    const data = await res.json();
    
    if (!res.ok || data.error) {
      console.error('Add to cart error:', data.error || 'Unknown error');
      alert('Failed to add to cart: ' + (data.error || 'Unknown error'));
      return;
    }
    
    // Success - refresh the mini cart
    await MiniCart.refresh();
    console.log('Added to cart:', data);
    
  } catch (e) {
    console.error('Add to cart exception:', e);
    alert('Error adding to cart. Please try again.');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  // Wire up add-to-cart buttons
  document.body.addEventListener('click', (e) => {
    const btn = e.target.closest('.add-to-cart');
    if (btn) {
      e.preventDefault();
      const productId = btn.getAttribute('data-product-id');
      if (productId) {
        console.log('Adding product ID to cart:', productId);
        addToCart(productId);
      } else {
        console.error('No product ID found on button');
      }
    }
  });

  // Initial cart count load
  MiniCart.refresh();
});
</script>
