/**
 * Brillspay Admin Custom JavaScript
 * Handles admin dashboard functionality, analytics, and admin-specific features
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all admin functionality
    initAdminDashboard();
    initAnalyticsCharts();
    initUserManagement();
    initTransactionManagement();
    initSettingsPanel();
    initNotificationSystem();
});

/**
 * Initialize Admin Dashboard
 */
function initAdminDashboard() {
    console.log('Initializing Brillspay Admin Dashboard...');
    
    // Dashboard widgets toggle
    const dashboardWidgets = document.querySelectorAll('.dashboard-widget');
    if (dashboardWidgets.length > 0) {
        dashboardWidgets.forEach(widget => {
            const header = widget.querySelector('.widget-header');
            if (header) {
                header.addEventListener('click', () => {
                    widget.classList.toggle('collapsed');
                });
            }
        });
    }
    
    // Quick stats update
    updateQuickStats();
    
    // Refresh dashboard data every 5 minutes
    setInterval(updateDashboardData, 300000);
}

/**
 * Initialize Analytics Charts
 */
function initAnalyticsCharts() {
    const analyticsTabs = document.querySelectorAll('.analytics-tab');
    const chartContainers = document.querySelectorAll('.chart-container');
    
    if (analyticsTabs.length > 0) {
        analyticsTabs.forEach(tab => {
            tab.addEventListener('click', function() {
                const target = this.getAttribute('data-target');
                
                // Update active tab
                analyticsTabs.forEach(t => t.classList.remove('active'));
                this.classList.add('active');
                
                // Show target chart
                chartContainers.forEach(container => {
                    container.style.display = 'none';
                });
                
                const targetContainer = document.getElementById(target);
                if (targetContainer) {
                    targetContainer.style.display = 'block';
                    renderChart(target);
                }
            });
        });
        
        // Load default chart
        if (analyticsTabs.length > 0) {
            const defaultTab = analyticsTabs[0];
            const defaultTarget = defaultTab.getAttribute('data-target');
            renderChart(defaultTarget);
        }
    }
    
    // Date range picker for analytics
    const dateRangePicker = document.getElementById('analytics-date-range');
    if (dateRangePicker) {
        dateRangePicker.addEventListener('change', function() {
            const range = this.value;
            updateAnalyticsData(range);
        });
    }
}

/**
 * Render specific chart
 */
function renderChart(chartType) {
    const container = document.getElementById(chartType);
    if (!container) return;
    
    // Clear previous chart
    container.innerHTML = '<div class="chart-loading">Loading chart...</div>';
    
    // Simulate API call
    setTimeout(() => {
        container.innerHTML = `<canvas id="${chartType}-chart"></canvas>`;
        
        // Initialize Chart.js based on chart type
        const ctx = document.getElementById(`${chartType}-chart`).getContext('2d');
        
        let chartConfig = getChartConfig(chartType);
        
        if (chartConfig) {
            new Chart(ctx, chartConfig);
        }
    }, 500);
}

/**
 * Get chart configuration based on type
 */
function getChartConfig(chartType) {
    const colors = {
        primary: '#4361ee',
        success: '#00ab55',
        warning: '#ffb300',
        danger: '#ff5630',
        info: '#00b8d9',
        secondary: '#6c757d'
    };
    
    const configs = {
        'revenue-chart': {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
                datasets: [{
                    label: 'Revenue',
                    data: [12000, 19000, 15000, 25000, 22000, 30000, 28000],
                    borderColor: colors.primary,
                    backgroundColor: 'rgba(67, 97, 238, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return '$' + value.toLocaleString();
                            }
                        }
                    }
                }
            }
        },
        
        'transactions-chart': {
            type: 'bar',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
                datasets: [{
                    label: 'Transactions',
                    data: [450, 520, 480, 600, 550, 700, 650],
                    backgroundColor: colors.success,
                    borderColor: colors.success,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return value.toLocaleString();
                            }
                        }
                    }
                }
            }
        },
        
        'users-chart': {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
                datasets: [
                    {
                        label: 'New Users',
                        data: [120, 150, 180, 200, 220, 250, 280],
                        borderColor: colors.info,
                        backgroundColor: 'rgba(0, 184, 217, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Active Users',
                        data: [1000, 1200, 1100, 1400, 1300, 1600, 1500],
                        borderColor: colors.warning,
                        backgroundColor: 'rgba(255, 179, 0, 0.1)',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return value.toLocaleString();
                            }
                        }
                    }
                }
            }
        },
        
        'merchants-chart': {
            type: 'doughnut',
            data: {
                labels: ['Active', 'Pending', 'Suspended', 'Inactive'],
                datasets: [{
                    data: [65, 15, 10, 10],
                    backgroundColor: [
                        colors.success,
                        colors.warning,
                        colors.danger,
                        colors.secondary
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        }
    };
    
    return configs[chartType] || null;
}

/**
 * Update analytics data based on date range
 */
function updateAnalyticsData(range) {
    const loadingIndicator = document.querySelector('.analytics-loading');
    if (loadingIndicator) {
        loadingIndicator.style.display = 'block';
    }
    
    // Simulate API call
    setTimeout(() => {
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
        }
        
        // Re-render all visible charts
        document.querySelectorAll('.chart-container[style*="display: block"]').forEach(container => {
            const chartId = container.id;
            renderChart(chartId);
        });
        
        // Update quick stats
        updateQuickStats();
    }, 1000);
}

/**
 * Initialize User Management
 */
function initUserManagement() {
    const userTable = document.getElementById('users-table');
    if (!userTable) return;
    
    // User search
    const userSearch = document.getElementById('user-search');
    if (userSearch) {
        userSearch.addEventListener('input', debounce(function() {
            filterUsers(this.value);
        }, 300));
    }
    
    // User status filter
    const statusFilter = document.getElementById('user-status-filter');
    if (statusFilter) {
        statusFilter.addEventListener('change', function() {
            filterUsersByStatus(this.value);
        });
    }
    
    // User actions
    userTable.addEventListener('click', function(e) {
        const target = e.target;
        
        // Edit user
        if (target.classList.contains('edit-user')) {
            const userId = target.getAttribute('data-user-id');
            editUser(userId);
        }
        
        // Delete user
        if (target.classList.contains('delete-user')) {
            const userId = target.getAttribute('data-user-id');
            deleteUser(userId);
        }
        
        // View user details
        if (target.classList.contains('view-user')) {
            const userId = target.getAttribute('data-user-id');
            viewUserDetails(userId);
        }
    });
    
    // Bulk actions
    const bulkActions = document.querySelector('.bulk-actions');
    if (bulkActions) {
        const selectAll = bulkActions.querySelector('.select-all');
        const bulkActionSelect = bulkActions.querySelector('.bulk-action-select');
        const applyBulkAction = bulkActions.querySelector('.apply-bulk-action');
        
        if (selectAll) {
            selectAll.addEventListener('change', function() {
                const checkboxes = userTable.querySelectorAll('input[type="checkbox"]');
                checkboxes.forEach(checkbox => {
                    checkbox.checked = this.checked;
                });
            });
        }
        
        if (applyBulkAction && bulkActionSelect) {
            applyBulkAction.addEventListener('click', function() {
                const action = bulkActionSelect.value;
                const selectedUsers = getSelectedUsers();
                
                if (selectedUsers.length === 0) {
                    showNotification('Please select at least one user', 'warning');
                    return;
                }
                
                performBulkAction(action, selectedUsers);
            });
        }
    }
}

/**
 * Filter users by search query
 */
function filterUsers(query) {
    const rows = document.querySelectorAll('#users-table tbody tr');
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        if (text.includes(query.toLowerCase())) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

/**
 * Filter users by status
 */
function filterUsersByStatus(status) {
    const rows = document.querySelectorAll('#users-table tbody tr');
    
    rows.forEach(row => {
        if (status === 'all') {
            row.style.display = '';
        } else {
            const rowStatus = row.getAttribute('data-status');
            if (rowStatus === status) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        }
    });
}

/**
 * Get selected users
 */
function getSelectedUsers() {
    const selected = [];
    const checkboxes = document.querySelectorAll('#users-table input[type="checkbox"]:checked');
    
    checkboxes.forEach(checkbox => {
        const userId = checkbox.getAttribute('data-user-id');
        if (userId) {
            selected.push(userId);
        }
    });
    
    return selected;
}

/**
 * Perform bulk action on users
 */
function performBulkAction(action, userIds) {
    if (!confirm(`Are you sure you want to ${action} ${userIds.length} user(s)?`)) {
        return;
    }
    
    showNotification(`Performing ${action} on ${userIds.length} user(s)...`, 'info');
    
    // Simulate API call
    setTimeout(() => {
        showNotification(`Successfully ${action}ed ${userIds.length} user(s)`, 'success');
        
        // Refresh user list
        loadUserList();
    }, 1500);
}

/**
 * Initialize Transaction Management
 */
function initTransactionManagement() {
    const transactionTable = document.getElementById('transactions-table');
    if (!transactionTable) return;
    
    // Transaction search
    const transactionSearch = document.getElementById('transaction-search');
    if (transactionSearch) {
        transactionSearch.addEventListener('input', debounce(function() {
            filterTransactions(this.value);
        }, 300));
    }
    
    // Date filter
    const dateFilter = document.getElementById('transaction-date-filter');
    if (dateFilter) {
        dateFilter.addEventListener('change', function() {
            filterTransactionsByDate(this.value);
        });
    }
    
    // Status filter
    const transactionStatusFilter = document.getElementById('transaction-status-filter');
    if (transactionStatusFilter) {
        transactionStatusFilter.addEventListener('change', function() {
            filterTransactionsByStatus(this.value);
        });
    }
    
    // Export transactions
    const exportBtn = document.getElementById('export-transactions');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportTransactions);
    }
    
    // Transaction actions
    transactionTable.addEventListener('click', function(e) {
        const target = e.target;
        
        // View transaction details
        if (target.classList.contains('view-transaction')) {
            const transactionId = target.getAttribute('data-transaction-id');
            viewTransactionDetails(transactionId);
        }
        
        // Refund transaction
        if (target.classList.contains('refund-transaction')) {
            const transactionId = target.getAttribute('data-transaction-id');
            refundTransaction(transactionId);
        }
    });
}

/**
 * Filter transactions
 */
function filterTransactions(query) {
    const rows = document.querySelectorAll('#transactions-table tbody tr');
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        if (text.includes(query.toLowerCase())) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

/**
 * Filter transactions by date
 */
function filterTransactionsByDate(dateRange) {
    // Implement date filtering logic
    showNotification(`Filtering transactions by ${dateRange}`, 'info');
}

/**
 * Filter transactions by status
 */
function filterTransactionsByStatus(status) {
    const rows = document.querySelectorAll('#transactions-table tbody tr');
    
    rows.forEach(row => {
        if (status === 'all') {
            row.style.display = '';
        } else {
            const rowStatus = row.getAttribute('data-status');
            if (rowStatus === status) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        }
    });
}

/**
 * Export transactions
 */
function exportTransactions() {
    const format = document.getElementById('export-format')?.value || 'csv';
    const dateRange = document.getElementById('transaction-date-filter')?.value || 'all';
    
    showNotification(`Exporting ${format.toUpperCase()} report for ${dateRange}...`, 'info');
    
    // Simulate export process
    setTimeout(() => {
        showNotification(`Report exported successfully`, 'success');
        
        // Create and trigger download
        const blob = new Blob(['Transaction export data'], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `transactions_${new Date().toISOString().split('T')[0]}.${format}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }, 2000);
}

/**
 * Initialize Settings Panel
 */
function initSettingsPanel() {
    const settingsForm = document.getElementById('admin-settings-form');
    if (!settingsForm) return;
    
    // Form submission
    settingsForm.addEventListener('submit', function(e) {
        e.preventDefault();
        saveSettings();
    });
    
    // Tab navigation
    const settingsTabs = document.querySelectorAll('.settings-tab');
    const settingsSections = document.querySelectorAll('.settings-section');
    
    settingsTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const target = this.getAttribute('data-target');
            
            // Update active tab
            settingsTabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            // Show target section
            settingsSections.forEach(section => {
                section.style.display = 'none';
            });
            
            const targetSection = document.getElementById(target);
            if (targetSection) {
                targetSection.style.display = 'block';
            }
        });
    });
    
    // Toggle settings
    const toggleSwitches = document.querySelectorAll('.toggle-switch input[type="checkbox"]');
    toggleSwitches.forEach(switchElement => {
        switchElement.addEventListener('change', function() {
            const settingName = this.getAttribute('name');
            const isEnabled = this.checked;
            
            // Update setting immediately or show preview
            if (this.hasAttribute('data-live-update')) {
                updateSetting(settingName, isEnabled);
            }
        });
    });
}

/**
 * Save admin settings
 */
function saveSettings() {
    const form = document.getElementById('admin-settings-form');
    const formData = new FormData(form);
    
    showNotification('Saving settings...', 'info');
    
    // Simulate API call
    setTimeout(() => {
        showNotification('Settings saved successfully', 'success');
    }, 1500);
}

/**
 * Update individual setting
 */
function updateSetting(name, value) {
    // Send AJAX request to update setting
    console.log(`Updating setting ${name} to ${value}`);
}

/**
 * Initialize Notification System
 */
function initNotificationSystem() {
    const notificationBell = document.querySelector('.notification-bell');
    if (notificationBell) {
        notificationBell.addEventListener('click', toggleNotifications);
    }
    
    // Mark all as read
    const markAllRead = document.querySelector('.mark-all-read');
    if (markAllRead) {
        markAllRead.addEventListener('click', markAllNotificationsAsRead);
    }
    
    // Load notifications
    loadNotifications();
    
    // Poll for new notifications every 30 seconds
    setInterval(checkNewNotifications, 30000);
}

/**
 * Load notifications
 */
function loadNotifications() {
    // Simulate API call
    setTimeout(() => {
        const notificationCount = document.querySelector('.notification-count');
        if (notificationCount) {
            notificationCount.textContent = '3';
            notificationCount.style.display = 'inline-block';
        }
    }, 1000);
}

/**
 * Toggle notifications dropdown
 */
function toggleNotifications() {
    const dropdown = document.querySelector('.notifications-dropdown');
    if (dropdown) {
        dropdown.classList.toggle('show');
    }
}

/**
 * Mark all notifications as read
 */
function markAllNotificationsAsRead() {
    const notificationCount = document.querySelector('.notification-count');
    if (notificationCount) {
        notificationCount.style.display = 'none';
    }
    
    const unreadNotifications = document.querySelectorAll('.notification-item.unread');
    unreadNotifications.forEach(notification => {
        notification.classList.remove('unread');
    });
    
    showNotification('All notifications marked as read', 'success');
}

/**
 * Check for new notifications
 */
function checkNewNotifications() {
    // Implement actual notification check
    console.log('Checking for new notifications...');
}

/**
 * Update quick stats on dashboard
 */
function updateQuickStats() {
    // Simulate API call to get updated stats
    setTimeout(() => {
        const stats = {
            totalRevenue: '$125,430',
            totalTransactions: '12,543',
            activeUsers: '8,432',
            pendingMerchants: '24'
        };
        
        // Update stat elements
        Object.keys(stats).forEach(stat => {
            const element = document.querySelector(`.stat-${stat}`);
            if (element) {
                element.textContent = stats[stat];
            }
        });
    }, 1000);
}

/**
 * Update dashboard data
 */
function updateDashboardData() {
    updateQuickStats();
    
    // Update charts if they're visible
    document.querySelectorAll('.chart-container[style*="display: block"]').forEach(container => {
        const chartId = container.id;
        renderChart(chartId);
    });
}

/**
 * Show notification message
 */
function showNotification(message, type = 'info') {
    // Remove existing notification
    const existingNotification = document.querySelector('.admin-notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `admin-notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <span class="notification-message">${message}</span>
            <button class="notification-close">&times;</button>
        </div>
    `;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Show notification
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 300);
    }, 5000);
    
    // Close button
    const closeBtn = notification.querySelector('.notification-close');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            notification.classList.remove('show');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 300);
        });
    }
}

/**
 * Debounce function for search inputs
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Load user list
 */
function loadUserList() {
    // Implement user list loading
    console.log('Loading user list...');
}

/**
 * Edit user
 */
function editUser(userId) {
    showNotification(`Editing user ${userId}`, 'info');
    // Implement edit user functionality
}

/**
 * Delete user
 */
function deleteUser(userId) {
    if (confirm('Are you sure you want to delete this user?')) {
        showNotification(`Deleting user ${userId}...`, 'warning');
        // Implement delete user functionality
    }
}

/**
 * View user details
 */
function viewUserDetails(userId) {
    showNotification(`Viewing details for user ${userId}`, 'info');
    // Implement view user details
}

/**
 * View transaction details
 */
function viewTransactionDetails(transactionId) {
    showNotification(`Viewing transaction ${transactionId}`, 'info');
    // Implement view transaction details
}

/**
 * Refund transaction
 */
function refundTransaction(transactionId) {
    if (confirm('Are you sure you want to refund this transaction?')) {
        showNotification(`Refunding transaction ${transactionId}...`, 'warning');
        // Implement refund functionality
    }
}