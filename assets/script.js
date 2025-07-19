// Basic cart functionality using localStorage
function addToCart(id, name) {
    const cart = JSON.parse(localStorage.getItem('cart') || '[]');
    const existing = cart.find(item => item.id === id);
    if (existing) {
        existing.qty += 1;
    } else {
        cart.push({id, name, qty: 1});
    }
    localStorage.setItem('cart', JSON.stringify(cart));
    alert('Added to cart');
}

function loadCart() {
    const cart = JSON.parse(localStorage.getItem('cart') || '[]');
    const container = document.getElementById('cart-items');
    const total = document.getElementById('cart-total');
    if (!container) return;
    container.innerHTML = '';
    let sum = 0;
    cart.forEach(item => {
        const row = document.createElement('div');
        row.className = 'd-flex justify-content-between mb-2';
        row.innerHTML = `${item.name} x ${item.qty}`;
        container.appendChild(row);
        sum += item.qty;
    });
    total.textContent = sum;
}

document.addEventListener('DOMContentLoaded', loadCart);
