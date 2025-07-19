function getCart() {
  const cart = localStorage.getItem('cart');
  return cart ? JSON.parse(cart) : [];
}
function saveCart(cart) {
  localStorage.setItem('cart', JSON.stringify(cart));
}
function addToCart(product) {
  const cart = getCart();
  const existing = cart.find(item => item.id === product.id);
  if (existing) {
    existing.qty += 1;
  } else {
    cart.push({...product, qty:1});
  }
  saveCart(cart);
  alert('Added to cart');
  updateCartCount();
}
function removeFromCart(id) {
  let cart = getCart();
  cart = cart.filter(item => item.id !== id);
  saveCart(cart);
  renderCart();
  updateCartCount();
}
function updateQuantity(id, qty) {
  const cart = getCart();
  const item = cart.find(i => i.id === id);
  if (item) {
    item.qty = qty;
  }
  saveCart(cart);
  renderCart();
  updateCartCount();
}
function renderCart() {
  const cart = getCart();
  const container = document.getElementById('cart-items');
  const totalEl = document.getElementById('cart-total');
  if (!container) return;
  container.innerHTML = '';
  let total = 0;
  cart.forEach(item => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${item.name}</td>
      <td><input type="number" min="1" value="${item.qty}" onchange="updateQuantity(${item.id}, this.value)"></td>
      <td>$${item.price}</td>
      <td><button class="btn btn-sm btn-danger" onclick="removeFromCart(${item.id})">Remove</button></td>
    `;
    container.appendChild(row);
    total += item.price * item.qty;
  });
  if (totalEl) totalEl.textContent = '$' + total.toFixed(2);
}
function updateCartCount() {
  const countEl = document.getElementById('cart-count');
  if (!countEl) return;
  const cart = getCart();
  const count = cart.reduce((sum, item) => sum + item.qty, 0);
  countEl.textContent = count;
}

document.addEventListener('DOMContentLoaded', () => {
  updateCartCount();
  renderCart();
});
