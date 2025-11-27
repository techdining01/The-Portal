// Admin-specific JavaScript functionality

class AdminDashboard {
    constructor() {
        this.init();
    }

    init() {
        this.initializeCharts();
        this.initializeDataTables();
        this.initializeFilters();
        this.initializeRealTimeUpdates();
        this.bindEvents();
    }

    bindEvents() {
        // Sidebar toggle for mobile
        const sidebarToggle = document.getElementById('sidebarToggle');
        if (sidebarToggle) {
            sidebarToggle.addEventListener('click', () => this.toggleSidebar());
        }

        // Search functionality
        const searchInput = document.getElementById('adminSearch');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => this.handleSearch(e.target.value));
        }

        // Bulk actions
        const bulkActionSelect = document.getElementById('bulkActions');
        if (bulkActionSelect) {
            bulkActionSelect.addEventListener('change', (e) => this.handleBulkAction(e.target.value));
        }

        // Export buttons
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('export-btn')) {
                this.handleExport(e.target.dataset.type);
            }
        });

        // Backup actions
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('backup-btn')) {
                this.handleBackup(e.target.dataset.type);
            }
        });
    }

    initializeCharts() {
        // Sales Chart
        const salesCtx = document.getElementById('salesChart');
        if (salesCtx) {
            this.salesChart = new Chart(salesCtx, {
                type: 'line',
                data: {
                    labels: this.getLast7Days(),
                    datasets: [{
                        label: 'Daily Sales',
                        data: this.generateSampleData(7, 1000, 5000),
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'top',
                        },
                        title: {
                            display: true,
                            text: 'Sales Overview (Last 7 Days)'
                        }
                    }
                }
            });
        }

        // Revenue Chart
        const revenueCtx = document.getElementById('revenueChart');
        if (revenueCtx) {
            this.revenueChart = new Chart(revenueCtx, {
                type: 'bar',
                data: {
                    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                    datasets: [{
                        label: 'Revenue',
                        data: this.generateSampleData(6, 50000, 200000),
                        backgroundColor: '#27ae60'
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'top',
                        },
                        title: {
                            display: true,
                            text: 'Monthly Revenue'
                        }
                    }
                }
            });
        }

        // Product Categories Chart
        const categoriesCtx = document.getElementById('categoriesChart');
        if (categoriesCtx) {
            this.categoriesChart = new Chart(categoriesCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Electronics', 'Books', 'Clothing', 'Food', 'Other'],
                    datasets: [{
                        data: [30, 25, 20, 15, 10],
                        backgroundColor: [
                            '#3498db',
                            '#27ae60',
                            '#f39c12',
                            '#e74c3c',
                            '#9b59b6'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'bottom',
                        },
                        title: {
                            display: true,
                            text: 'Sales by Category'
                        }
                    }
                }
            });
        }
    }

    initializeDataTables() {
        // Initialize DataTables if library is available
        if (typeof $.fn.DataTable !== 'undefined') {
            $('.admin-table').DataTable({
                pageLength: 25,
                responsive: true,
                order: [[0, 'desc']],
                language: {
                    search: "Search:",
                    lengthMenu: "Show _MENU_ entries",
                    info: "Showing _START_ to _END_ of _TOTAL_ entries",
                    paginate: {
                        first: "First",
                        last: "Last",
                        next: "Next",
                        previous: "Previous"
                    }
                }
            });
        }
    }

    initializeFilters() {
        // Date range filter
        const dateRangePicker = document.getElementById('dateRangePicker');
        if (dateRangePicker) {
            // Initialize date range picker
            $(dateRangePicker).daterangepicker({
                opens: 'left',
                ranges: {
                    'Today': [moment(), moment()],
                    'Yesterday': [moment().subtract(1, 'days'), moment().subtract(1, 'days')],
                    'Last 7 Days': [moment().subtract(6, 'days'), moment()],
                    'Last 30 Days': [moment().subtract(29, 'days'), moment()],
                    'This Month': [moment().startOf('month'), moment().endOf('month')],
                    'Last Month': [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')]
                }
            });
        }

        // Status filter
        const statusFilter = document.getElementById('statusFilter');
        if (statusFilter) {
            statusFilter.addEventListener('change', () => this.applyFilters());
        }

        // Category filter
        const categoryFilter = document.getElementById('categoryFilter');
        if (categoryFilter) {
            categoryFilter.addEventListener('change', () => this.applyFilters());
        }
    }

    initializeRealTimeUpdates() {
        // Update dashboard stats every 30 seconds
        setInterval(() => {
            this.updateDashboardStats();
        }, 30000);

        // Check for new orders
        setInterval(() => {
            this.checkNewOrders();
        }, 60000);
    }

    async updateDashboardStats() {
        try {
            const response = await fetch('/admin/api/dashboard-stats/');
            const data = await response.json();
            
            this.updateStatsDisplay(data);
        } catch (error) {
            console.error('Error updating dashboard stats:', error);
        }
    }

    updateStatsDisplay(stats) {
        // Update total sales
        const totalSalesElement = document.getElementById('totalSales');
        if (totalSalesElement) {
            totalSalesElement.textContent = this.formatCurrency(stats.total_sales);
        }

        // Update total orders
        const totalOrdersElement = document.getElementById('totalOrders');
        if (totalOrdersElement) {
            totalOrdersElement.textContent = stats.total_orders;
        }

        // Update total products
        const totalProductsElement = document.getElementById('totalProducts');
        if (totalProductsElement) {
            totalProductsElement.textContent = stats.total_products;
        }

        // Update total customers
        const totalCustomersElement = document.getElementById('totalCustomers');
        if (totalCustomersElement) {
            totalCustomersElement.textContent = stats.total_customers;
        }
    }

    async checkNewOrders() {
        try {
            const response = await fetch('/admin/api/new-orders-count/');
            const data = await response.json();
            
            if (data.new_orders_count > 0) {
                this.showNewOrdersNotification(data.new_orders_count);
            }
        } catch (error) {
            console.error('Error checking new orders:', error);
        }
    }

    showNewOrdersNotification(count) {
        // Create or update notification badge
        let notificationBadge = document.getElementById('newOrdersBadge');
        if (!notificationBadge) {
            notificationBadge = document.createElement('span');
            notificationBadge.id = 'newOrdersBadge';
            notificationBadge.className = 'badge bg-danger ms-2';
            document.querySelector('.orders-menu-item').appendChild(notificationBadge);
        }
        
        notificationBadge.textContent = count;
        
        // Show toast notification
        this.showToast(`You have ${count} new order(s)`, 'info');
    }

    toggleSidebar() {
        const sidebar = document.querySelector('.admin-sidebar');
        const main = document.querySelector('.admin-main');
        
        sidebar.classList.toggle('collapsed');
        main.classList.toggle('sidebar-collapsed');
    }

    handleSearch(query) {
        const tables = document.querySelectorAll('.admin-table');
        
        tables.forEach(table => {
            const rows = table.querySelectorAll('tbody tr');
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(query.toLowerCase()) ? '' : 'none';
            });
        });
    }

    handleBulkAction(action) {
        const selectedItems = this.getSelectedItems();
        
        if (selectedItems.length === 0) {
            this.showToast('Please select items to perform this action', 'warning');
            return;
        }

        switch (action) {
            case 'delete':
                this.confirmBulkDelete(selectedItems);
                break;
            case 'export':
                this.exportSelectedItems(selectedItems);
                break;
            case 'update_status':
                this.showStatusUpdateModal(selectedItems);
                break;
        }
    }

    getSelectedItems() {
        const selectedItems = [];
        document.querySelectorAll('.item-checkbox:checked').forEach(checkbox => {
            selectedItems.push(checkbox.value);
        });
        return selectedItems;
    }

    confirmBulkDelete(selectedItems) {
        if (confirm(`Are you sure you want to delete ${selectedItems.length} selected item(s)?`)) {
            this.performBulkAction('delete', selectedItems);
        }
    }

    async performBulkAction(action, items) {
        try {
            const response = await fetch('/admin/api/bulk-action/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    action: action,
                    items: items
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showToast(`Successfully ${action}d ${items.length} item(s)`, 'success');
                location.reload(); // Reload to reflect changes
            } else {
                this.showToast(`Error performing bulk action: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Error performing bulk action:', error);
            this.showToast('Error performing bulk action', 'error');
        }
    }

    async handleExport(type) {
        try {
            const response = await fetch(`/admin/api/export/${type}/`);
            const blob = await response.blob();
            
            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${type}_export_${new Date().toISOString().split('T')[0]}.xlsx`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            this.showToast(`Export completed successfully`, 'success');
        } catch (error) {
            console.error('Export error:', error);
            this.showToast('Error generating export', 'error');
        }
    }

    async handleBackup(type) {
        if (!confirm(`Are you sure you want to create a ${type} backup?`)) {
            return;
        }

        try {
            this.showLoading(`Creating ${type} backup...`);
            
            const response = await fetch('/admin/api/create-backup/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    backup_type: type
                })
            });

            const data = await response.json();
            
            this.hideLoading();
            
            if (data.success) {
                this.showToast(`${type} backup created successfully`, 'success');
                this.updateBackupList();
            } else {
                this.showToast(`Error creating backup: ${data.error}`, 'error');
            }
        } catch (error) {
            this.hideLoading();
            console.error('Backup error:', error);
            this.showToast('Error creating backup', 'error');
        }
    }

    applyFilters() {
        const filters = {
            date_range: document.getElementById('dateRangePicker')?.value,
            status: document.getElementById('statusFilter')?.value,
            category: document.getElementById('categoryFilter')?.value
        };

        // Reload page with filter parameters or make AJAX call
        const url = new URL(window.location);
        
        Object.entries(filters).forEach(([key, value]) => {
            if (value) {
                url.searchParams.set(key, value);
            } else {
                url.searchParams.delete(key);
            }
        });

        window.location.href = url.toString();
    }

    // Utility methods
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('en-NG', {
            style: 'currency',
            currency: 'NGN'
        }).format(amount);
    }

    formatDate(date) {
        return new Date(date).toLocaleDateString('en-NG');
    }

    getLast7Days() {
        const days = [];
        for (let i = 6; i >= 0; i--) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            days.push(date.toLocaleDateString('en-NG', { weekday: 'short' }));
        }
        return days;
    }

    generateSampleData(count, min, max) {
        return Array.from({ length: count }, () => 
            Math.floor(Math.random() * (max - min + 1)) + min
        );
    }

    showToast(message, type = 'info') {
        // Create toast container if it doesn't exist
        let toastContainer = document.getElementById('admin-toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'admin-toast-container';
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }

        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type}`;
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        toastContainer.appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();

        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }

    showLoading(message = 'Loading...') {
        let loadingModal = document.getElementById('loadingModal');
        if (!loadingModal) {
            loadingModal = document.createElement('div');
            loadingModal.id = 'loadingModal';
            loadingModal.className = 'modal fade show d-block';
            loadingModal.innerHTML = `
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-body text-center">
                            <div class="spinner-border text-primary mb-3"></div>
                            <p>${message}</p>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(loadingModal);
        }
    }

    hideLoading() {
        const loadingModal = document.getElementById('loadingModal');
        if (loadingModal) {
            loadingModal.remove();
        }
    }
}

// Initialize admin dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.adminDashboard = new AdminDashboard();
});

// Quick action functions
function quickEdit(itemId, model) {
    // Implement quick edit functionality
    console.log(`Quick editing ${model} with ID: ${itemId}`);
}

function quickDelete(itemId, model) {
    if (confirm(`Are you sure you want to delete this ${model}?`)) {
        // Implement quick delete functionality
        console.log(`Deleting ${model} with ID: ${itemId}`);
    }
}

function updateOrderStatus(orderId, status) {
    // Implement order status update
    console.log(`Updating order ${orderId} to status: ${status}`);
}

// Export functions for global access
window.AdminDashboard = AdminDashboard;
window.quickEdit = quickEdit;
window.quickDelete = quickDelete;
window.updateOrderStatus = updateOrderStatus;