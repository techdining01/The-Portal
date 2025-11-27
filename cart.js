// Cart-specific JavaScript functionality

class CartManager {
    constructor() {
        this.cartItems = [];
        this.init();
    }

    init() {
        this.loadCartFromStorage();
        this.bindEvents();
        this.updateCartDisplay();
    }

    bindEvents() {
        // Quantity changes
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('quantity-increase')) {
                this.changeQuantity(e.target.dataset.itemId, 1);
            } else if (e.target.classList.contains('quantity-decrease')) {
                this.changeQuantity(e.target.dataset.itemId, -1);
            }
        });

        // Remove items
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('remove-item')) {
                this.removeItem(e.target.dataset.itemId);
            }
        });

        // Input changes
        document.addEventListener('change', (e) => {
            if (e.target.classList.contains('quantity-input')) {
                this.setQuantity(e.target.dataset.itemId, parseInt(e.target.value));
            }
        });

        // Clear cart
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('clear-cart')) {
                this.clearCart();
            }
        });
    }

    async changeQuantity(itemId, change) {
        const item = this.cartItems.find(item => item.id == itemId);
        if (!item) return;

        const newQuantity = item.quantity + change;
        if (newQuantity < 1) {
            this.removeItem(itemId);
            return;
        }

        await this.setQuantity(itemId, newQuantity);
    }

    async setQuantity(itemId, quantity) {
        try {
            const response = await fetch('/api/cart/update/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    item_id: itemId,
                    quantity: quantity
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.updateLocalCart(data);
                this.updateCartDisplay();
                this.showNotification('Cart updated successfully', 'success');
            } else {
                this.showNotification('Error updating cart', 'error');
            }
        } catch (error) {
            console.error('Error updating cart:', error);
            this.showNotification('Error updating cart', 'error');
        }
    }

    async removeItem(itemId) {
        if (!confirm('Are you sure you want to remove this item from your cart?')) {
            return;
        }

        try {
            const response = await fetch('/api/cart/update/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    item_id: itemId,
                    quantity: 0
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.updateLocalCart(data, true);
                this.updateCartDisplay();
                this.showNotification('Item removed from cart', 'success');
            } else {
                this.showNotification('Error removing item', 'error');
            }
        } catch (error) {
            console.error('Error removing item:', error);
            this.showNotification('Error removing item', 'error');
        }
    }

    async clearCart() {
        if (!confirm('Are you sure you want to clear your entire cart?')) {
            return;
        }

        try {
            // Remove all items one by one
            for (const item of this.cartItems) {
                await this.removeItem(item.id);
            }
            
            this.showNotification('Cart cleared successfully', 'success');
        } catch (error) {
            console.error('Error clearing cart:', error);
            this.showNotification('Error clearing cart', 'error');
        }
    }

    updateLocalCart(data, isRemoval = false) {
        if (isRemoval) {
            this.cartItems = this.cartItems.filter(item => item.id != data.item_id);
        } else {
            const itemIndex = this.cartItems.findIndex(item => item.id == data.item_id);
            if (itemIndex > -1) {
                this.cartItems[itemIndex].quantity = data.quantity;
                this.cartItems[itemIndex].total_price = data.item_total;
            }
        }

        this.saveCartToStorage();
    }

    updateCartDisplay() {
        this.updateCartBadge();
        this.updateCartTotals();
        this.updateCheckoutButton();
    }

    updateCartBadge() {
        const totalItems = this.cartItems.reduce((sum, item) => sum + item.quantity, 0);
        const badges = document.querySelectorAll('.cart-badge');
        
        badges.forEach(badge => {
            badge.textContent = totalItems;
            badge.style.display = totalItems > 0 ? 'inline' : 'none';
        });
    }

    updateCartTotals() {
        const totalPrice = this.cartItems.reduce((sum, item) => sum + item.total_price, 0);
        const totalItems = this.cartItems.reduce((sum, item) => sum + item.quantity, 0);

        // Update cart page totals
        const cartTotalElement = document.querySelector('.cart-total-price');
        if (cartTotalElement) {
            cartTotalElement.textContent = this.formatCurrency(totalPrice);
        }

        const cartCountElement = document.querySelector('.cart-total-items');
        if (cartCountElement) {
            cartCountElement.textContent = totalItems;
        }

        // Update checkout page totals
        const checkoutTotalElement = document.querySelector('.checkout-total');
        if (checkoutTotalElement) {
            checkoutTotalElement.textContent = this.formatCurrency(totalPrice);
        }

        // Update mini-cart if exists
        this.updateMiniCart();
    }

    updateMiniCart() {
        const miniCart = document.getElementById('mini-cart');
        if (!miniCart) return;

        let html = '';
        
        if (this.cartItems.length === 0) {
            html = '<div class="text-center p-3">Your cart is empty</div>';
        } else {
            this.cartItems.forEach(item => {
                html += `
                    <div class="mini-cart-item d-flex align-items-center py-2 border-bottom">
                        <img src="${item.image}" alt="${item.name}" class="rounded" style="width: 50px; height: 50px; object-fit: cover;">
                        <div class="ms-2 flex-grow-1">
                            <h6 class="mb-0">${item.name}</h6>
                            <small class="text-muted">${this.formatCurrency(item.price)} x ${item.quantity}</small>
                        </div>
                        <div class="text-end">
                            <div class="fw-bold">${this.formatCurrency(item.total_price)}</div>
                            <button class="btn btn-sm btn-outline-danger remove-item" data-item-id="${item.id}">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                `;
            });

            html += `
                <div class="p-2 border-top">
                    <div class="d-flex justify-content-between mb-2">
                        <strong>Total:</strong>
                        <strong>${this.formatCurrency(this.getTotalPrice())}</strong>
                    </div>
                    <a href="/checkout/" class="btn btn-primary w-100">Checkout</a>
                </div>
            `;
        }

        miniCart.innerHTML = html;
    }

    updateCheckoutButton() {
        const checkoutBtn = document.querySelector('.checkout-btn');
        if (checkoutBtn) {
            const isCartEmpty = this.cartItems.length === 0;
            checkoutBtn.disabled = isCartEmpty;
            
            if (isCartEmpty) {
                checkoutBtn.classList.add('disabled');
            } else {
                checkoutBtn.classList.remove('disabled');
            }
        }
    }

    getTotalPrice() {
        return this.cartItems.reduce((sum, item) => sum + item.total_price, 0);
    }

    loadCartFromStorage() {
        const savedCart = localStorage.getItem('schoolEcommerceCart');
        if (savedCart) {
            this.cartItems = JSON.parse(savedCart);
        }
    }

    saveCartToStorage() {
        localStorage.setItem('schoolEcommerceCart', JSON.stringify(this.cartItems));
    }

    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('en-NG', {
            style: 'currency',
            currency: 'NGN'
        }).format(amount);
    }

    showNotification(message, type = 'info') {
        // Use the main.js toast function if available
        if (window.Ecommerce && typeof window.Ecommerce.showToast === 'function') {
            window.Ecommerce.showToast(message, type);
        } else {
            alert(message); // Fallback
        }
    }

    // Public methods
    addItem(product) {
        const existingItem = this.cartItems.find(item => item.id === product.id);
        
        if (existingItem) {
            existingItem.quantity += 1;
            existingItem.total_price = existingItem.price * existingItem.quantity;
        } else {
            this.cartItems.push({
                ...product,
                quantity: 1,
                total_price: product.price
            });
        }
        
        this.saveCartToStorage();
        this.updateCartDisplay();
        this.showNotification('Item added to cart', 'success');
    }

    getCartSummary() {
        return {
            totalItems: this.cartItems.reduce((sum, item) => sum + item.quantity, 0),
            totalPrice: this.getTotalPrice(),
            items: this.cartItems
        };
    }
}

// Initialize cart manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.cartManager = new CartManager();
});

// Quick add to cart functionality
function quickAddToCart(productId, productName, productPrice, productImage) {
    if (window.cartManager) {
        const product = {
            id: productId,
            name: productName,
            price: parseFloat(productPrice),
            image: productImage
        };
        
        window.cartManager.addItem(product);
    }
}

// Cart animation effects
function animateCartUpdate(itemId, type) {
    const itemElement = document.querySelector(`[data-item-id="${itemId}"]`);
    if (!itemElement) return;

    if (type === 'add') {
        itemElement.classList.add('highlight-add');
        setTimeout(() => itemElement.classList.remove('highlight-add'), 1000);
    } else if (type === 'remove') {
        itemElement.classList.add('highlight-remove');
        setTimeout(() => itemElement.classList.remove('highlight-remove'), 1000);
    }
}

// Export for global access
window.CartManager = CartManager;
window.quickAddToCart = quickAddToCart;