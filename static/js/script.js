// Replace all alert() calls with Bootstrap alerts
function showAlert(message, type = 'danger') {
    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        <i class="bi ${type === 'success' ? 'bi-check-circle' : type === 'danger' ? 'bi-exclamation-triangle' : type === 'warning' ? 'bi-exclamation-circle' : 'bi-info-circle'} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    // Add to the top of main content
    const mainContent = document.querySelector('.main-content');
    mainContent.insertBefore(alertDiv, mainContent.firstChild);

    // Auto remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

// Set theme color
function setThemeColor(color) {
    const html = document.documentElement;

    // Remove all color themes
    html.classList.remove('blue', 'purple', 'green', 'orange', 'red');

    // Add selected color theme
    if (color !== 'blue') {
        html.classList.add(color);
    }

    // Update active state
    document.querySelectorAll('.theme-color').forEach(el => {
        el.classList.remove('active');
    });
    document.querySelector(`.theme-color.${color}`).classList.add('active');

    // Save preference to localStorage
    localStorage.setItem('themeColor', color);
}

// Toggle theme between light and dark
function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-bs-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-bs-theme', newTheme);

    // Update icon
    const icon = document.querySelector('.theme-toggle-btn i');
    icon.className = newTheme === 'dark' ? 'bi bi-moon-stars' : 'bi bi-sun';

    // Update button text
    const text = document.querySelector('.theme-toggle-btn span');
    text.textContent = newTheme === 'dark' ? 'Dark Mode' : 'Light Mode';

    // Save preference to localStorage
    localStorage.setItem('theme', newTheme);
}

// Load saved theme preference
document.addEventListener('DOMContentLoaded', function() {
    // Set default theme to light
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-bs-theme', savedTheme);

    // Set saved color theme
    const savedColor = localStorage.getItem('themeColor') || 'blue';
    setThemeColor(savedColor);

    // Update theme toggle button
    const themeToggleBtn = document.querySelector('.theme-toggle-btn');
    if (themeToggleBtn) {
        const icon = themeToggleBtn.querySelector('i');
        const text = themeToggleBtn.querySelector('span');
        icon.className = savedTheme === 'dark' ? 'bi bi-moon-stars' : 'bi bi-sun';
        text.textContent = savedTheme === 'dark' ? 'Dark Mode' : 'Light Mode';
    }

    // Calculate totals on page load
    calculateTotals();

    // Set up event listeners
    setupEventListeners();
});

function setupEventListeners() {
    // Calculate totals button
    const calculateTotalsBtn = document.getElementById('calculateTotals');
    if (calculateTotalsBtn) {
        calculateTotalsBtn.addEventListener('click', calculateTotals);
    }

    // Theme toggle button
    const themeToggleBtn = document.querySelector('.theme-toggle-btn');
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', toggleTheme);
    }

    // Theme color buttons
    document.querySelectorAll('.theme-color').forEach(button => {
        button.addEventListener('click', function() {
            setThemeColor(this.dataset.color);
        });
    });

    // Payment method change event
    const paymentMethodSelect = document.getElementById('paymentMethod');
    if (paymentMethodSelect) {
        paymentMethodSelect.addEventListener('change', function() {
            updatePaymentOptions(this.value, document.getElementById('paymentOption'));
        });
    }

    // Edit payment method change event
    const editPaymentMethod = document.getElementById('editPaymentMethod');
    if (editPaymentMethod) {
        editPaymentMethod.addEventListener('change', function() {
            updatePaymentOptions(this.value, document.getElementById('editPaymentOption'));
        });
    }

    // Product form calculation events
    const productInputs = document.querySelectorAll('#addProductModal input');
    productInputs.forEach(input => {
        if (input.name === 'quantity' || input.name === 'unit_price' || input.name === 'vat_percentage' || input.name === 'discount') {
            input.addEventListener('input', calculateEstimatedTotal);
        }
    });

    // Edit product form calculation events
    const editProductInputs = document.querySelectorAll('#editProductModal input');
    editProductInputs.forEach(input => {
        if (input.name === 'quantity' || input.name === 'unit_price' || input.name === 'vat_percentage' || input.name === 'discount') {
            input.addEventListener('input', calculateEditEstimatedTotal);
        }
    });

    // Item lookup form
    const itemLookupForm = document.getElementById('itemLookupForm');
    if (itemLookupForm) {
        itemLookupForm.addEventListener('submit', function(e) {
            e.preventDefault();
            handleItemLookup();
        });
    }

    // Database test connection
    const testDatabaseBtn = document.getElementById('testDatabase');
    if (testDatabaseBtn) {
        testDatabaseBtn.addEventListener('click', testDatabaseConnection);
    }

    // Test all endpoints
    const testAllEndpointsBtn = document.getElementById('testAllEndpoints');
    if (testAllEndpointsBtn) {
        testAllEndpointsBtn.addEventListener('click', testAllEndpoints);
    }

    // Single endpoint test buttons
    document.querySelectorAll('.test-single-endpoint').forEach(button => {
        button.addEventListener('click', function() {
            testSingleEndpoint(this.dataset.name, this.dataset.url);
        });
    });

    // Edit product buttons
    document.querySelectorAll('.edit-product').forEach(button => {
        button.addEventListener('click', function() {
            editProduct(this.dataset.index);
        });
    });

    // Edit payment buttons
    document.querySelectorAll('.edit-payment').forEach(button => {
        button.addEventListener('click', function() {
            editPayment(this.dataset.index);
        });
    });
}

// Update the item lookup error handling
function handleItemLookup() {
    const formData = new FormData(document.getElementById('itemLookupForm'));
    const params = new URLSearchParams(formData);

    fetch('/get-item-details?' + params)
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showAlert('Error: ' + data.error, 'danger');
        } else {
            // Display item details
            const itemDetails = document.getElementById('itemDetails');
            itemDetails.innerHTML = `
                <tr><th>Item Code</th><td>${data.item_code}</td></tr>
                <tr><th>Barcode</th><td>${data.item_Barcode}</td></tr>
                <tr><th>English Name</th><td>${data.item_EN_Name}</td></tr>
                <tr><th>Arabic Name</th><td>${data.item_AR_Name}</td></tr>
                <tr><th>Unit Price</th><td>${data.unit_price}</td></tr>
                <tr><th>VAT %</th><td>${data.vat_percentage}</td></tr>
                <tr><th>Net Price</th><td>${data.net_price}</td></tr>
            `;

            document.getElementById('itemResults').style.display = 'block';

            // Set up add to order button
            document.getElementById('addItemToOrder').onclick = function() {
                fetch('/add-product-from-db', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data)
                })
                .then(response => response.json())
                .then(result => {
                    if (result.success) {
                        showAlert('Product added successfully!', 'success');
                        setTimeout(() => {
                            window.location.reload();
                        }, 1500);
                    } else {
                        showAlert('Error adding product: ' + result.error, 'danger');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showAlert('Error adding product', 'danger');
                });
            };
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('Error fetching item details', 'danger');
    });
}

// Update database connection test
function testDatabaseConnection() {
    const formData = new FormData(document.getElementById('databaseForm'));
    const data = Object.fromEntries(formData.entries());

    fetch('/test-database-connection', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Database connection successful!', 'success');
        } else {
            showAlert('Database connection failed: ' + data.message, 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('Error testing database connection', 'danger');
    });
}

// Update edit product functionality
function editProduct(index) {
    fetch('/update-product/' + index)
        .then(response => response.json())
        .then(data => {
            if (!data.error) {
                document.getElementById('editItemCode').value = data.item_code;
                document.getElementById('editItemName').value = data.item_name;
                document.getElementById('editQuantity').value = data.quantity;
                document.getElementById('editUnitPrice').value = data.unit_price;
                document.getElementById('editVatPercentage').value = data.vat_percentage * 100; // Convert to percentage
                document.getElementById('editDiscount').value = data.row_total_discount;
                document.getElementById('editOfferCode').value = data.offer_code;
                document.getElementById('editOfferMessage').value = data.offer_message;

                // Update form action
                document.getElementById('editProductForm').action = '/update-product/' + index;

                // Show modal
                const editProductModal = new bootstrap.Modal(document.getElementById('editProductModal'));
                editProductModal.show();

                // Calculate estimated total
                calculateEditEstimatedTotal();
            } else {
                showAlert('Error loading product: ' + data.error, 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Error loading product details', 'danger');
        });
}

// Update edit payment functionality
function editPayment(index) {
    fetch('/update-payment/' + index)
        .then(response => response.json())
        .then(data => {
            if (!data.error) {
                document.getElementById('editPaymentMethod').value = data.payment_method;
                document.getElementById('editPaymentStatus').value = data.payment_status;
                document.getElementById('editPaymentAmount').value = data.payment_amount;
                document.getElementById('editTransactionId').value = data.transaction_id;
                document.getElementById('editPaymentOption').value = data.payment_option;
                document.getElementById('editOptionCommission').value = data.option_commission;
                document.getElementById('editCardName').value = data.card_name;
                document.getElementById('editBankCode').value = data.bank_code;

                // Set credit customer info if available
                if (data.credit_customer_info) {
                    document.getElementById('editCustomerNumber').value = data.credit_customer_info.customer_number;
                    document.getElementById('editCustomerName').value = data.credit_customer_info.customer_name;
                    document.getElementById('editCreditCustomerInfo').style.display = 'flex';
                } else {
                    document.getElementById('editCreditCustomerInfo').style.display = 'none';
                }

                // Update payment options
                updatePaymentOptions(data.payment_method, document.getElementById('editPaymentOption'));

                // Update form action
                document.getElementById('editPaymentForm').action = '/update-payment/' + index;

                // Show modal
                const editPaymentModal = new bootstrap.Modal(document.getElementById('editPaymentModal'));
                editPaymentModal.show();
            } else {
                showAlert('Error loading payment: ' + data.error, 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Error loading payment details', 'danger');
        });
}

// Update calculate totals error handling
function calculateTotals() {
    fetch('/calculate-totals')
        .then(response => response.json())
        .then(data => {
            if (!data.error) {
                document.getElementById('productsTotal').textContent = data.products_total.toFixed(2);
                document.getElementById('orderDiscount').textContent = data.order_discount.toFixed(2);
                document.getElementById('deliveryCost').textContent = data.delivery_cost.toFixed(2);
                document.getElementById('finalTotal').textContent = data.final_total.toFixed(2);

                // Update sidebar total
                const sidebarTotal = document.getElementById('sidebar-total');
                if (sidebarTotal) {
                    sidebarTotal.textContent = data.final_total.toFixed(2);
                }
            } else {
                showAlert('Error calculating totals: ' + data.error, 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Error calculating totals', 'danger');
        });
}

function calculateEstimatedTotal() {
    const quantity = parseFloat(document.querySelector('input[name="quantity"]').value) || 0;
    const unitPrice = parseFloat(document.querySelector('input[name="unit_price"]').value) || 0;
    const vatPercent = parseFloat(document.querySelector('input[name="vat_percentage"]').value) || 0;
    const discount = parseFloat(document.querySelector('input[name="discount"]').value) || 0;

    const vatAmount = (quantity * unitPrice - discount) * (vatPercent / 100);
    const total = (quantity * unitPrice - discount) + vatAmount;

    document.getElementById('estimatedTotal').value = '$' + total.toFixed(2);
}

function calculateEditEstimatedTotal() {
    const quantity = parseFloat(document.getElementById('editQuantity').value) || 0;
    const unitPrice = parseFloat(document.getElementById('editUnitPrice').value) || 0;
    const vatPercent = parseFloat(document.getElementById('editVatPercentage').value) || 0;
    const discount = parseFloat(document.getElementById('editDiscount').value) || 0;

    const vatAmount = (quantity * unitPrice - discount) * (vatPercent / 100);
    const total = (quantity * unitPrice - discount) + vatAmount;

    document.getElementById('editEstimatedTotal').value = '$' + total.toFixed(2);
}

function updatePaymentOptions(method, optionSelect) {
    if (!optionSelect) return;

    const paymentOptionsData = document.getElementById('paymentOptionsData');
    if (!paymentOptionsData) return;

    const options = JSON.parse(paymentOptionsData.textContent);

    optionSelect.innerHTML = '<option value="">Select Option</option>';

    if (method && options[method]) {
        options[method].forEach(option => {
            const optionElement = document.createElement('option');
            optionElement.value = option;
            optionElement.textContent = option;
            optionSelect.appendChild(optionElement);
        });
    }

    // Show/hide credit customer info based on payment method
    const creditCustomerInfo = document.getElementById('creditCustomerInfo');
    if (creditCustomerInfo) {
        if (method === 'PostToCredit') {
            creditCustomerInfo.style.display = 'flex';
        } else {
            creditCustomerInfo.style.display = 'none';
        }
    }
}

function testAllEndpoints() {
    const endpointsTable = document.getElementById('endpointsTable');
    if (!endpointsTable) return;

    const rows = endpointsTable.querySelectorAll('tr');

    rows.forEach(row => {
        const statusCell = row.querySelector('td:nth-child(3)');
        const testButton = row.querySelector('.test-single-endpoint');

        if (statusCell && testButton) {
            statusCell.innerHTML = '<span class="badge bg-info">Testing...</span>';
            testButton.disabled = true;

            const name = testButton.dataset.name;
            const url = testButton.dataset.url;

            testSingleEndpoint(name, url).then(result => {
                statusCell.innerHTML = `<span class="badge bg-${result.status === 'Online' ? 'success' : 'danger'}">${result.status}</span>`;
                testButton.disabled = false;
            });
        }
    });
}

function testSingleEndpoint(name, url) {
    return fetch('/test-single-endpoint', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, url })
    })
    .then(response => response.json())
    .then(data => {
        return data;
    })
    .catch(error => {
        console.error('Error:', error);
        return { status: 'Error', error: error.message };
    });
}

// Add payment options data to the page
document.addEventListener('DOMContentLoaded', function() {
    const paymentOptionsData = document.createElement('div');
    paymentOptionsData.id = 'paymentOptionsData';
    paymentOptionsData.style.display = 'none';
    paymentOptionsData.textContent = JSON.stringify({{ payment_options|tojson }});
    document.body.appendChild(paymentOptionsData);

    // Trigger change event on page load if there's a selected value
    const paymentMethodSelect = document.getElementById('paymentMethod');
    if (paymentMethodSelect) {
        paymentMethodSelect.dispatchEvent(new Event('change'));
    }
});