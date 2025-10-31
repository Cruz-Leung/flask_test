<script>
const MiniCart = (() => {
  const panel = () => document.getElementById('mini-cart-panel');
  const content = () => document.getElementById('mini-cart-content');
  const countEl = () => document.getElementById('mini-cart-count');

  async function refresh() {
    try {
      const [mini, cnt] = await Promise.all([
        fetch('/cart/mini', { credentials: 'same-origin' }).then(r => r.text()),
        fetch('/cart/count', { credentials: 'same-origin' }).then(r => r.json()),
      ]);
      content().innerHTML = mini;
      if (countEl()) countEl().textContent = cnt.count;
    } catch (e) {
      console.error('MiniCart refresh failed', e);
    }
  }
  function show() {
    panel().style.display = 'block';
  }
  function hide() {
    panel().style.display = 'none';
  }
  return { refresh, show, hide };
})();

async function addToCart(productId) {
  try {
    const res = await fetch(`/cart/add/${productId}`, {
      method: 'POST',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'same-origin'
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      console.error(data.error || 'Add to cart failed');
      alert('Failed to add to cart.');
      return;
    }
    await MiniCart.refresh();
    MiniCart.show();
  } catch (e) {
    console.error('Add to cart error', e);
    alert('Error adding to cart.');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  // Wire buttons
  document.body.addEventListener('click', (e) => {
    const btn = e.target.closest('.add-to-cart');
    if (btn) {
      const id = btn.getAttribute('data-product-id');
      if (id) addToCart(id);
    }
  });

  // Mini-cart toggle
  const toggle = document.getElementById('mini-cart-toggle');
  if (toggle) {
    toggle.addEventListener('click', async () => {
      const panel = document.getElementById('mini-cart-panel');
      if (panel.style.display === 'none' || !panel.style.display) {
        await MiniCart.refresh();
        MiniCart.show();
      } else {
        MiniCart.hide();
      }
    });
  }

  // Initial count
  MiniCart.refresh();
});
</script>
