// Main JavaScript for School E-Commerce

document.addEventListener('DOMContentLoaded', function() {
    initializeCartFunctionality();
    initializePaymentMethods();
    initializeProductFilters();
    initializeFormValidations();
});

// Cart Functionality
function initializeCartFunctionality() {
    // Update cart item quantity
    document.querySelectorAll('.quantity-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const itemId = this.dataset.itemId;
            const action = this.dataset.action;
            updateCartItem(itemId, action);
        });
    });

    // Remove item from cart
    document.querySelectorAll('.remove-item-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const itemId = this.dataset.itemId;
            removeCartItem(itemId);
        });
    });

    // Real-time quantity input updates
    document.querySelectorAll('.quantity-input').forEach(input => {
        input.addEventListener('change', function() {
            const itemId = this.dataset.itemId;
            const quantity = parseInt(this.value);
            updateCartItemQuantity(itemId, quantity);
        });
    });
}

// Update cart item via AJAX
async function updateCartItem(itemId, action) {
    try {
        const response = await fetch('/api/cart/update/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                item_id: itemId,
                action: action
            })
        });

        const data = await response.json();
        
        if (data.success) {
            updateCartUI(data);
            showToast('Cart updated successfully', 'success');
        } else {
            showToast('Error updating cart', 'error');
        }
    } catch (error) {
        console.error('Error updating cart:', error);
        showToast('Error updating cart', 'error');
    }
}

// Update cart item quantity via AJAX
async function updateCartItemQuantity(itemId, quantity) {
    try {
        const response = await fetch('/api/cart/update/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                item_id: itemId,
                quantity: quantity
            })
        });

        const data = await response.json();
        
        if (data.success) {
            updateCartUI(data);
            showToast('Cart updated successfully', 'success');
        } else {
            showToast('Error updating cart', 'error');
        }
    } catch (error) {
        console.error('Error updating cart:', error);
        showToast('Error updating cart', 'error');
    }
}

// Remove cart item via AJAX
async function removeCartItem(itemId) {
    if (!confirm('Are you sure you want to remove this item from your cart?')) {
        return;
    }

    try {
        const response = await fetch('/api/cart/update/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                item_id: itemId,
                quantity: 0
            })
        });

        const data = await response.json();
        
        if (data.success) {
            updateCartUI(data);
            showToast('Item removed from cart', 'success');
            
            // Remove the item row from UI
            const itemRow = document.querySelector(`[data-item-id="${itemId}"]`).closest('.cart-item');
            if (itemRow) {
                itemRow.remove();
            }
        } else {
            showToast('Error removing item from cart', 'error');
        }
    } catch (error) {
        console.error('Error removing cart item:', error);
        showToast('Error removing item from cart', 'error');
    }
}

// Update cart UI elements
function updateCartUI(data) {
    // Update cart badge
    const cartBadge = document.querySelector('.cart-badge');
    if (cartBadge) {
        cartBadge.textContent = data.total_items;
    }

    // Update cart totals
    const cartTotalElement = document.querySelector('.cart-total-price');
    if (cartTotalElement) {
        cartTotalElement.textContent = formatCurrency(data.cart_total);
    }

    // Update item total if not deleted
    if (!data.deleted) {
        const itemTotalElement = document.querySelector(`[data-item-id="${data.item_id}"] .item-total`);
        if (itemTotalElement) {
            itemTotalElement.textContent = formatCurrency(data.item_total);
        }
    }

    // Update checkout summary
    const checkoutTotalElement = document.querySelector('.checkout-total');
    if (checkoutTotalElement) {
        checkoutTotalElement.textContent = formatCurrency(data.cart_total);
    }
}

// Payment Method Selection
function initializePaymentMethods() {
    const paymentMethods = document.querySelectorAll('input[name="payment_method"]');
    
    paymentMethods.forEach(method => {
        method.addEventListener('change', function() {
            updatePaymentMethodUI(this.value);
        });
    });

    // Initialize payment method UI
    const selectedMethod = document.querySelector('input[name="payment_method"]:checked');
    if (selectedMethod) {
        updatePaymentMethodUI(selectedMethod.value);
    }
}

function updatePaymentMethodUI(method) {
    // Hide all payment method details
    document.querySelectorAll('.payment-details').forEach(detail => {
        detail.style.display = 'none';
    });

    // Show selected payment method details
    const selectedDetail = document.getElementById(`${method}-details`);
    if (selectedDetail) {
        selectedDetail.style.display = 'block';
    }

    // Update payment method cards styling
    document.querySelectorAll('.payment-method').forEach(card => {
        card.classList.remove('selected');
    });
    
    const selectedCard = document.querySelector(`[data-method="${method}"]`);
    if (selectedCard) {
        selectedCard.classList.add('selected');
    }
}

// Product Filters
function initializeProductFilters() {
    const categoryFilter = document.getElementById('category-filter');
    if (categoryFilter) {
        categoryFilter.addEventListener('change', function() {
            this.form.submit();
        });
    }

    // Price range filter
    const priceRange = document.getElementById('price-range');
    if (priceRange) {
        const priceValue = document.getElementById('price-value');
        priceValue.textContent = formatCurrency(priceRange.value);
        
        priceRange.addEventListener('input', function() {
            priceValue.textContent = formatCurrency(this.value);
        });
    }
}

// Form Validations
function initializeFormValidations() {
    // Real-time form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(this)) {
                e.preventDefault();
            }
        });
    });

    // File upload validation
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            validateFileInput(this);
        });
    });
}

function validateForm(form) {
    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            markFieldInvalid(field, 'This field is required');
            isValid = false;
        } else {
            markFieldValid(field);
        }
    });

    // Email validation
    const emailFields = form.querySelectorAll('input[type="email"]');
    emailFields.forEach(field => {
        if (field.value && !isValidEmail(field.value)) {
            markFieldInvalid(field, 'Please enter a valid email address');
            isValid = false;
        }
    });

    return isValid;
}

function validateFileInput(input) {
    const file = input.files[0];
    if (!file) return;

    const maxSize = 5 * 1024 * 1024; // 5MB
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif'];

    if (file.size > maxSize) {
        markFieldInvalid(input, 'File size must be less than 5MB');
        input.value = '';
    } else if (!allowedTypes.includes(file.type)) {
        markFieldInvalid(input, 'Please select a valid image file (JPEG, PNG, GIF)');
        input.value = '';
    } else {
        markFieldValid(input);
        
        // Preview image if it's a payment proof
        if (input.name === 'payment_proof') {
            previewImage(file, 'payment-proof-preview');
        }
    }
}

function markFieldInvalid(field, message) {
    field.classList.add('is-invalid');
    field.classList.remove('is-valid');
    
    let feedback = field.nextElementSibling;
    if (!feedback || !feedback.classList.contains('invalid-feedback')) {
        feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        field.parentNode.appendChild(feedback);
    }
    feedback.textContent = message;
}

function markFieldValid(field) {
    field.classList.add('is-valid');
    field.classList.remove('is-invalid');
}

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Utility Functions
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-NG', {
        style: 'currency',
        currency: 'NGN'
    }).format(amount);
}

function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }

    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');

    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;

    toastContainer.appendChild(toast);

    // Initialize and show toast
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();

    // Remove toast from DOM after it's hidden
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

// Image Preview
function previewImage(file, previewId) {
    const preview = document.getElementById(previewId);
    if (preview) {
        const reader = new FileReader();
        reader.onload = function(e) {
            preview.innerHTML = `<img src="${e.target.result}" class="img-thumbnail" style="max-height: 200px;">`;
        };
        reader.readAsDataURL(file);
    }
}

// Search Functionality
function initializeSearch() {
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        let searchTimeout;
        
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                performSearch(this.value);
            }, 500);
        });
    }
}

async function performSearch(query) {
    if (query.length < 2) {
        clearSearchResults();
        return;
    }

    try {
        const response = await fetch(`/api/search/?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        displaySearchResults(data);
    } catch (error) {
        console.error('Search error:', error);
    }
}

function displaySearchResults(results) {
    // Implement search results display
    console.log('Search results:', results);
}

function clearSearchResults() {
    // Implement clear search results
}

// Order Tracking
function trackOrder(orderNumber) {
    // Implement order tracking functionality
    console.log('Tracking order:', orderNumber);
}

// Export functions for global access
window.Ecommerce = {
    updateCartItem,
    removeCartItem,
    showToast,
    formatCurrency,
    trackOrder
};