import json
import os
import socket
from datetime import datetime, timedelta
from urllib.parse import urlparse

import pyodbc
import requests
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Import configuration
from config import API_URLS, DEFAULT_API_ENDPOINT, PAYMENT_METHODS, PAYMENT_STATUSES, PAYMENT_OPTIONS, DEFAULT_DATA


# Database connection function
def get_db_connection():
    try:
        # Try different ODBC drivers
        drivers = [
            'ODBC Driver 18 for SQL Server',
            'ODBC Driver 17 for SQL Server',
            'ODBC Driver 13 for SQL Server',
            'SQL Server Native Client 11.0',
            'SQL Server Native Client 10.0',
            'SQL Server'
        ]

        conn = None
        for driver in drivers:
            try:
                conn_str = (
                    f'DRIVER={{{driver}}};'
                    f'SERVER=.;'
                    f'DATABASE=RMSCashierSrv;'
                    f'UID=sa;'
                    f'PWD=P@ssw0rd'
                )
                conn = pyodbc.connect(conn_str)
                print(f"Connected successfully using {driver}")
                break
            except pyodbc.Error as e:
                print(f"Failed with {driver}: {str(e)}")
                continue

        if conn is None:
            raise Exception("Could not connect with any available driver")

        return conn

    except Exception as e:
        print(f"Database connection error: {str(e)}")
        flash(f'Database connection error: {str(e)}', 'danger')
        return None


# Initialize session data
@app.before_request
def before_request():
    # Initialize session data with defaults or saved values
    if 'order_data' not in session:
        session['order_data'] = session.get('saved_order_data', DEFAULT_DATA.copy())

    # Set current date and time for delivery fields if they're empty or default
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M:%S")
    one_hour_later = (datetime.now() + timedelta(hours=1)).strftime("%H:%M:%S")

    # Check if delivery fields need to be updated
    order_data = session['order_data']

    if not order_data.get('delivery_date') or order_data.get('delivery_date') in ['CURRENT_DATE', '']:
        order_data['delivery_date'] = current_date

    if not order_data.get('delivery_from_time') or order_data.get('delivery_from_time') in ['CURRENT_TIME', '']:
        order_data['delivery_from_time'] = current_time

    if not order_data.get('delivery_to_time') or order_data.get('delivery_to_time') in ['CURRENT_TIME_PLUS_1H', '']:
        order_data['delivery_to_time'] = one_hour_later

    # Update the session
    session['order_data'] = order_data

    if 'products' not in session:
        session['products'] = session.get('saved_products', DEFAULT_DATA['order_products'].copy())

    if 'payments' not in session:
        session['payments'] = session.get('saved_payments', DEFAULT_DATA['payment_methods_with_options'].copy())

    if 'api_endpoint' not in session:
        session['api_endpoint'] = DEFAULT_API_ENDPOINT


@app.route('/')
def index():
    return render_template('base.html',
                           api_urls=API_URLS,
                           payment_methods=PAYMENT_METHODS,
                           payment_statuses=PAYMENT_STATUSES,
                           payment_options=PAYMENT_OPTIONS,
                           data=session.get('order_data', DEFAULT_DATA),
                           products=session.get('products', []),
                           payments=session.get('payments', []),
                           selected_endpoint=session.get('api_endpoint', DEFAULT_API_ENDPOINT))


@app.route('/remove-product/<int:index>')
def remove_product(index):
    try:
        products = session.get('products', [])
        if 0 <= index < len(products):
            products.pop(index)
            session['products'] = products
            session['saved_products'] = products
            flash('Product removed successfully!', 'success')
        else:
            flash('Invalid product index!', 'danger')

        return redirect(url_for('index'))

    except Exception as e:
        flash(f'Error removing product: {str(e)}', 'danger')
        return redirect(url_for('index'))


@app.route('/add-payment', methods=['POST'])
def add_payment():
    try:
        payment = {
            "payment_method": request.form.get('payment_method'),
            "payment_status": request.form.get('payment_status'),
            "payment_amount": float(request.form.get('payment_amount', 0)),
            "transaction_id": request.form.get('transaction_id'),
            "payment_option": request.form.get('payment_option'),
            "option_commission": float(request.form.get('option_commission', 0)),
            "card_name": request.form.get('card_name', ''),
            "bank_code": request.form.get('bank_code', ''),
            "credit_customer_info": {
                "customer_number": request.form.get('customer_number', ''),
                "customer_name": request.form.get('customer_name', '')
            } if request.form.get('payment_method') == 'PostToCredit' else None
        }

        payments = session.get('payments', [])
        payments.append(payment)
        session['payments'] = payments
        session['saved_payments'] = payments

        # If payment status is done_payment, update order payment status
        if payment['payment_status'] == 'done_payment':
            order_data = session.get('order_data', DEFAULT_DATA.copy())
            order_data['order_payment_status'] = 'done_payment'
            session['order_data'] = order_data
            session['saved_order_data'] = order_data

        flash('Payment method added successfully!', 'success')
        return redirect(url_for('index'))

    except Exception as e:
        flash(f'Error adding payment method: {str(e)}', 'danger')
        return redirect(url_for('index'))


@app.route('/remove-payment/<int:index>')
def remove_payment(index):
    try:
        payments = session.get('payments', [])
        if 0 <= index < len(payments):
            payments.pop(index)
            session['payments'] = payments
            session['saved_payments'] = payments
            flash('Payment method removed successfully!', 'success')
        else:
            flash('Invalid payment method index!', 'danger')

        return redirect(url_for('index'))

    except Exception as e:
        flash(f'Error removing payment method: {str(e)}', 'danger')
        return redirect(url_for('index'))


@app.route('/update-order', methods=['POST'])
def update_order():
    try:
        order_data = session.get('order_data', DEFAULT_DATA.copy())

        # Update order information
        order_data['branch_code'] = request.form.get('branch_code', order_data['branch_code'])
        order_data['order_code'] = request.form.get('order_code', order_data['order_code'])
        order_data['parent_order_code'] = request.form.get('parent_order_code', order_data.get('parent_order_code', ''))
        order_data['order_delivery_cost'] = float(request.form.get('delivery_cost', order_data['order_delivery_cost']))
        order_data['is_delivery'] = int(request.form.get('is_delivery', order_data['is_delivery']))
        order_data['order_status'] = request.form.get('order_status', order_data['order_status'])
        order_data['order_payment_status'] = request.form.get('order_payment_status', order_data['order_payment_status'])

        # Update delivery information
        order_data['delivery_date'] = request.form.get('delivery_date', order_data['delivery_date'])
        order_data['delivery_from_time'] = request.form.get('delivery_from_time', order_data['delivery_from_time'])
        order_data['delivery_to_time'] = request.form.get('delivery_to_time', order_data['delivery_to_time'])
        order_data['shipping_address_2'] = request.form.get('shipping_address_2', order_data['shipping_address_2'])
        order_data['fullfilment_plant'] = request.form.get('fulfillment_plant', order_data['fullfilment_plant'])
        order_data['order_notes'] = request.form.get('order_notes', order_data['order_notes'])

        # Update client information
        order_data['client_first_name'] = request.form.get('first_name', order_data['client_first_name'])
        order_data['client_middle_name'] = request.form.get('middle_name', order_data['client_middle_name'])
        order_data['client_last_name'] = request.form.get('last_name', order_data['client_last_name'])
        order_data['client_phone'] = request.form.get('phone', order_data['client_phone'])
        order_data['client_email'] = request.form.get('email', order_data['client_email'])
        order_data['order_address'] = request.form.get('address', order_data['order_address'])
        order_data['client_birthdate'] = request.form.get('birthdate', order_data['client_birthdate'])
        order_data['client_gender'] = request.form.get('gender', order_data['client_gender'])
        order_data['client_country_code'] = request.form.get('country_code', order_data['client_country_code'])

        session['order_data'] = order_data
        session['saved_order_data'] = order_data

        flash('Order details updated successfully!', 'success')
        return redirect(url_for('index'))

    except Exception as e:
        flash(f'Error updating order: {str(e)}', 'danger')
        return redirect(url_for('index'))


@app.route('/calculate-totals')
def calculate_totals():
    try:
        products = session.get('products', [])
        order_data = session.get('order_data', DEFAULT_DATA.copy())

        order_product_total_value = sum(product.get('row_net_total', 0) for product in products)
        order_total_discount = sum(product.get('row_total_discount', 0) for product in products)
        delivery_cost = order_data.get('order_delivery_cost', 0)
        order_final_total_value = order_product_total_value + delivery_cost

        return jsonify({
            'products_total': round(order_product_total_value, 2),
            'order_discount': round(order_total_discount, 2),
            'delivery_cost': round(delivery_cost, 2),
            'final_total': round(order_final_total_value, 2)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/export-json')
def export_json():
    try:
        order_data = prepare_order_data()
        return jsonify(order_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/load-default')
def load_default():
    try:
        # Create a copy of DEFAULT_DATA but with current date/time
        default_data = DEFAULT_DATA.copy()

        current_date = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H:%M:%S")
        one_hour_later = (datetime.now() + timedelta(hours=1)).strftime("%H:%M:%S")

        # Update delivery fields with current values
        default_data['delivery_date'] = current_date
        default_data['delivery_from_time'] = current_time
        default_data['delivery_to_time'] = one_hour_later

        session['order_data'] = default_data
        session['products'] = default_data['order_products'].copy()
        session['payments'] = default_data['payment_methods_with_options'].copy()

        # Clear saved data
        session.pop('saved_order_data', None)
        session.pop('saved_products', None)
        session.pop('saved_payments', None)

        flash('Default data loaded successfully!', 'success')
        return redirect(url_for('index'))

    except Exception as e:
        flash(f'Error loading default data: {str(e)}', 'danger')
        return redirect(url_for('index'))


@app.route('/clear-all')
def clear_all():
    try:
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H:%M:%S")
        one_hour_later = (datetime.now() + timedelta(hours=1)).strftime("%H:%M:%S")

        session['order_data'] = {
            "branch_code": "",
            "order_code": "",
            "parent_order_code": "",
            "order_delivery_cost": 0,
            "is_delivery": 1,
            "order_status": "new",
            "order_payment_status": "not_payment",
            "delivery_date": current_date,
            "delivery_from_time": current_time,
            "delivery_to_time": one_hour_later,
            "shipping_address_2": "",
            "fullfilment_plant": "",
            "order_notes": "",
            "client_first_name": "",
            "client_middle_name": "",
            "client_last_name": "",
            "client_phone": "",
            "client_email": "",
            "client_birthdate": "1989-04-11T12:00:00.000Z",
            "client_gender": "Male",
            "client_country_code": "966",
            "order_address": ""
        }
        session['products'] = []
        session['payments'] = []

        # Clear saved data
        session.pop('saved_order_data', None)
        session.pop('saved_products', None)
        session.pop('saved_payments', None)

        flash('All data cleared successfully!', 'success')
        return redirect(url_for('index'))

    except Exception as e:
        flash('Error clearing data: {str(e))', 'danger')
        return redirect(url_for('index'))


@app.route('/send-request', methods=['POST'])
def send_request():
    try:
        selected_endpoint = request.form.get('api_endpoint')
        custom_url = request.form.get('custom_url', '').strip()

        # Use custom URL if provided, otherwise use the selected endpoint
        if custom_url:
            url = custom_url
        elif selected_endpoint in API_URLS:
            url = API_URLS[selected_endpoint]
        else:
            flash('Please select a valid API endpoint or provide a custom URL', 'danger')
            return redirect(url_for('index'))

        # Save the selected endpoint for next time
        session['api_endpoint'] = selected_endpoint

        # Create the JSON data to send
        order_data = prepare_order_data()

        # Validate the data before sending
        validation_errors = validate_order_data(order_data)
        if validation_errors:
            flash('Validation errors found:', 'danger')
            for error in validation_errors:
                flash(error, 'danger')
            return redirect(url_for('index'))

        # Log the request data for debugging
        print("=== SENDING REQUEST DATA ===")
        print(json.dumps(order_data, indent=2))
        print("============================")

        # Send POST request
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, json=order_data, headers=headers, timeout=30)

        # Prepare response data
        response_data = {
            'status_code': response.status_code,
            'response_text': response.text,
            'url_sent': url
        }

        # Try to parse JSON response
        try:
            response_data['response_json'] = response.json()
        except:
            response_data['response_json'] = None

        # Handle different response statuses
        if response.status_code == 200:
            save_json_file(order_data)
            flash('Request sent successfully! Order created.', 'success')
        elif response.status_code == 400:
            # Try to extract detailed error information
            try:
                error_data = response.json()
                error_message = "Validation Error (400): "

                if 'errors' in error_data:
                    error_message += "Field validation errors detected. "
                    # Format field errors for display
                    for field, errors in error_data['errors'].items():
                        error_message += f"{field}: {', '.join(errors)}. "
                elif 'title' in error_data:
                    error_message += error_data['title']

                flash(error_message, 'warning')

            except:
                flash(f'Validation Error (400): {response.text}', 'warning')

        else:
            flash(f'Server returned status code: {response.status_code}', 'warning')

        return render_template('base.html',
                               api_urls=API_URLS,
                               payment_methods=PAYMENT_METHODS,
                               payment_statuses=PAYMENT_STATUSES,
                               payment_options=PAYMENT_OPTIONS,
                               data=session.get('order_data', DEFAULT_DATA),
                               products=session.get('products', []),
                               payments=session.get('payments', []),
                               selected_endpoint=selected_endpoint,
                               response=response_data)

    except requests.exceptions.RequestException as e:
        error_msg = f'Request Error: {str(e)}'
        if hasattr(e, 'response') and e.response is not None:
            error_msg += f' | Response: {e.response.text}'
        flash(error_msg, 'danger')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'danger')
        return redirect(url_for('index'))


@app.route('/test-minimal-request')
def test_minimal_request():
    """Send a minimal request to test API connectivity"""
    minimal_data = {
        "branch_code": "2000",
        "order_code": f"TEST_{datetime.now().strftime('%H%M%S')}",
        "order_creation_date": datetime.now().isoformat() + 'Z',
        "order_notes": "Test order",
        "order_product_total_value": 10.0,
        "is_delivery": 0,
        "order_delivery_cost": 0.0,
        "order_total_discount": 0.0,
        "order_final_total_value": 10.0,
        "order_payment_method": "cash",
        "order_status": "new",
        "client_country_code": "966",
        "client_phone": "555123456",
        "client_first_name": "Test",
        "client_last_name": "User",
        "client_email": "test@example.com",
        "client_gender": "Male",
        "order_address": "Test Address",
        "order_payment_status": "done_payment",
        "order_gps": [21.779006345949554, 39.08578576461103],
        "order_products": [
            {
                "item_code": "TEST001",
                "item_name": "Test Product",
                "quantity": 1.0,
                "unit_price": 10.0,
                "unit_vat_amount": 0.0,
                "total_vat_amount": 0.0,
                "vat_percentage": 0.0,
                "offer_code": "",
                "offer_message": "",
                "row_total_discount": 0.0,
                "row_net_total": 10.0
            }
        ],
        "payment_methods_with_options": [
            {
                "payment_method": "cash",
                "payment_amount": 10.0,
                "transaction_id": "TEST123",
                "payment_option": "cash",
                "card_name": "",
                "bank_code": "",
                "option_commission": 0.0
            }
        ]
    }

    url = API_URLS.get("Whites Pharmacy - Testing")
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, json=minimal_data, headers=headers, timeout=10)
        return jsonify({
            'status_code': response.status_code,
            'response': response.text,
            'url': url,
            'request_data': minimal_data
        })
    except Exception as e:
        return jsonify({'error': str(e), 'url': url}), 500


@app.route('/check-drivers')
def check_drivers():
    """Check available ODBC drivers"""
    try:
        drivers = pyodbc.drivers()
        return jsonify({
            'available_drivers': drivers,
            'message': f'Found {len(drivers)} drivers'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/get-item-details', methods=['GET'])
def get_item_details():
    try:
        material_number = request.args.get('material_number', type=str)
        customer_number = request.args.get('customer_number', '', type=str)
        sap_tax_code = request.args.get('sap_tax_code', '', type=str)
        sap_mat_generic = request.args.get('sap_mat_generic', '', type=str)

        if not material_number or not material_number.isdigit() or len(material_number) != 6:
            return jsonify({'error': 'Material number must be 6 digits'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = conn.cursor()

        # Build query dynamically based on provided filters
        query = """
        SELECT TOP 1 
            I.MaterialNumber,
            IUOMB.UniversalBarCode,
            I.Name AS EnglishName,
            I.NativeName AS ArabicName,
            IP.Price AS UnitPrice,
            TT.Rate AS VatRate,
            CAST(ROUND(((IP.Price * TT.Rate)/100) + IP.Price, 2) AS DECIMAL(10,2)) AS NetPrice
            FROM dbo.Items AS I
            LEFT JOIN dbo.TaxTypes AS TT ON I.SapTaxCode = TT.Code
            INNER JOIN dbo.ItemUnitOfMeasures AS IUM ON I.Id = IUM.ItemId
            INNER JOIN dbo.ItemUnitOfMeasureBarCodes AS IUOMB ON IUM.Id = IUOMB.ItemUnitOfMeasureId
            LEFT JOIN dbo.ItemPrices AS IP ON IUM.Id = IP.ItemUnitOfMeasureId
            WHERE RIGHT(I.MaterialNumber, 6) = ?
            AND IP.IsActive = 1
            AND IP.Price IS NOT NULL
            AND IP.ToDate > GETDATE()
        """

        params = [material_number]

        # Add optional filters
        if customer_number:
            query += " AND EXISTS (SELECT 1 FROM dbo.Customers WHERE CustomerNumber = ? AND IsActive = 1)"
            params.append(customer_number)

        if sap_tax_code:
            query += " AND I.SapTaxCode = ?"
            params.append(sap_tax_code)

        if sap_mat_generic:
            query += " AND I.SapMatGeneric = ?"
            params.append(sap_mat_generic)

        query += " ORDER BY I.Id DESC"

        cursor.execute(query, params)
        row = cursor.fetchone()

        if not row:
            return jsonify({'error': 'No item found with the specified criteria'}), 404

        # FIX: Correctly map English and Arabic names
        item_details = {
            'item_code': row[0] if row[0] else f"000000000000{material_number}",
            'item_Barcode': row[1] if row[1] else f"BC{material_number}",
            'item_EN_Name': row[2] if row[2] else f"Item {material_number}",  # English name
            'item_AR_Name': row[3] if row[3] else f" صنف{material_number}",  # Arabic name
            'unit_price': float(row[4]) if row[4] else 0.0,
            'vat_percentage': float(row[5]) if row[5] else 0.0,
            'net_price': float(row[6]) if row[6] else 0.0
        }

        conn.close()
        return jsonify(item_details)

    except Exception as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500


@app.route('/update-product/<int:index>', methods=['GET', 'POST'])
def update_product(index):
    try:
        products = session.get('products', [])

        if request.method == 'GET':
            if 0 <= index < len(products):
                product = products[index]
                # Convert decimal VAT back to percentage for display
                product['vat_percentage'] = product['vat_percentage'] * 100
                return jsonify(product)
            else:
                return jsonify({'error': 'Invalid product index'}), 404

        # POST request - update product
        quantity = float(request.form.get('quantity', 0))
        unit_price = float(request.form.get('unit_price', 0))

        # Handle VAT percentage input (both 15 and 0.15 formats)
        vat_input = request.form.get('vat_percentage', '0')
        vat_percentage = float(vat_input)
        if vat_percentage > 1:  # If it's in percentage format (e.g., 15)
            vat_percentage = vat_percentage / 100  # Convert to decimal (0.15)

        discount = float(request.form.get('discount', 0))

        # Calculate values
        subtotal = quantity * unit_price
        vat_amount = subtotal * vat_percentage
        net_total = subtotal - discount + vat_amount

        product = {
            "item_code": request.form.get('item_code'),
            "item_name": request.form.get('item_name'),
            "quantity": quantity,
            "unit_price": unit_price,
            "vat_percentage": vat_percentage,
            "row_total_discount": discount,
            "total_vat_amount": vat_amount,
            "row_net_total": net_total,
            "unit_vat_amount": vat_amount / quantity if quantity > 0 else 0,
            "offer_code": request.form.get('offer_code', ''),
            "offer_message": request.form.get('offer_message', '')
        }

        if 0 <= index < len(products):
            products[index] = product
            session['products'] = products
            session['saved_products'] = products
            flash('Product updated successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid product index!', 'danger')
            return redirect(url_for('index'))

    except Exception as e:
        flash(f'Error updating product: {str(e)}', 'danger')
        return redirect(url_for('index'))


@app.route('/update-payment/<int:index>', methods=['GET', 'POST'])
def update_payment(index):
    try:
        payments = session.get('payments', [])

        if request.method == 'GET':
            if 0 <= index < len(payments):
                payment = payments[index]
                return jsonify(payment)
            else:
                return jsonify({'error': 'Invalid payment index'}), 404

        # POST request - update payment
        payment = {
            "payment_method": request.form.get('payment_method'),
            "payment_status": request.form.get('payment_status'),
            "payment_amount": float(request.form.get('payment_amount', 0)),
            "transaction_id": request.form.get('transaction_id'),
            "payment_option": request.form.get('payment_option'),
            "option_commission": float(request.form.get('option_commission', 0)),
            "card_name": request.form.get('card_name', ''),
            "bank_code": request.form.get('bank_code', ''),
            "credit_customer_info": {
                "customer_number": request.form.get('customer_number', ''),
                "customer_name": request.form.get('customer_name', '')
            } if request.form.get('payment_method') == 'PostToCredit' else None
        }

        if 0 <= index < len(payments):
            payments[index] = payment
            session['payments'] = payments
            session['saved_payments'] = payments

            # If payment status is done_payment, update order payment status
            if payment['payment_status'] == 'done_payment':
                order_data = session.get('order_data', DEFAULT_DATA.copy())
                order_data['order_payment_status'] = 'done_payment'
                session['order_data'] = order_data
                session['saved_order_data'] = order_data

            flash('Payment method updated successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid payment index!', 'danger')
            return redirect(url_for('index'))

    except Exception as e:
        flash(f'Error updating payment method: {str(e)}', 'danger')
        return redirect(url_for('index'))


@app.route('/test-single-endpoint', methods=['POST'])
def test_single_endpoint():
    try:
        data = request.get_json()
        url = data['url']
        name = data['name']

        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or (80 if parsed.scheme == 'http' else 443)

        # Test connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, port))
        sock.close()

        return jsonify({
            'status': 'Online' if result == 0 else 'Offline',
            'name': name,
            'url': url
        })

    except Exception as e:
        return jsonify({'status': 'Error', 'error': str(e)}), 500


@app.route('/test-database-connection', methods=['POST'])
def test_database_connection():
    try:
        if request.is_json:
            data = request.get_json()
            server = data.get('server', '.')
            database = data.get('database', 'RMSCashierSrv')
            username = data.get('username', 'sa')
            password = data.get('password', 'P@ssw0rd')
        else:
            server = request.form.get('server', '.')
            database = request.form.get('database', 'RMSCashierSrv')
            username = request.form.get('username', 'sa')
            password = request.form.get('password', 'P@ssw0rd')

        # Test connection
        conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'
        conn = pyodbc.connect(conn_str)
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Database connection successful!'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Database connection failed: {str(e)}'
        })


@app.route('/add-product-from-db', methods=['POST'])
def add_product_from_db():
    try:
        data = request.get_json()

        # Convert VAT percentage from 15 to 0.15 if needed
        vat_percentage = float(data['vat_percentage'])
        if vat_percentage > 1:  # If it's in percentage format (e.g., 15)
            vat_percentage = vat_percentage / 100  # Convert to decimal (0.15)

        # FIX: Use English name as item_name (was using Arabic name before)
        product = {
            "item_code": data['item_code'],
            "item_name": data['item_EN_Name'],  # Changed from item_name to item_EN_Name
            "quantity": 1.0,  # Default quantity
            "unit_price": float(data['unit_price']),
            "vat_percentage": vat_percentage,
            "row_total_discount": 0.0,
            "total_vat_amount": float(data['unit_price']) * vat_percentage,
            "row_net_total": float(data['unit_price']) + (float(data['unit_price']) * vat_percentage),
            "unit_vat_amount": float(data['unit_price']) * vat_percentage,
            "offer_code": "",
            "offer_message": ""
        }

        products = session.get('products', [])
        products.append(product)
        session['products'] = products
        session['saved_products'] = products

        return jsonify({'success': True, 'message': 'Product added successfully!'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/add-product', methods=['POST'])
def add_product():
    try:
        quantity = float(request.form.get('quantity', 0))
        unit_price = float(request.form.get('unit_price', 0))

        # Handle VAT percentage input (both 15 and 0.15 formats)
        vat_input = request.form.get('vat_percentage', '0')
        vat_percentage = float(vat_input)
        if vat_percentage > 1:  # If it's in percentage format (e.g., 15)
            vat_percentage = vat_percentage / 100  # Convert to decimal (0.15)

        discount = float(request.form.get('discount', 0))

        # Calculate values
        subtotal = quantity * unit_price
        vat_amount = round(subtotal * vat_percentage, 2)
        net_total = round(subtotal - discount + vat_amount, 2)

        product = {
            "item_code": request.form.get('item_code'),
            "item_name": request.form.get('item_name'),
            "quantity": quantity,
            "unit_price": unit_price,
            "vat_percentage": vat_percentage,
            "row_total_discount": discount,
            "total_vat_amount": vat_amount,
            "row_net_total": net_total,
            "unit_vat_amount": vat_amount / quantity if quantity > 0 else 0,
            "offer_code": request.form.get('offer_code', ''),
            "offer_message": request.form.get('offer_message', '')
        }

        products = session.get('products', [])
        products.append(product)
        session['products'] = products
        session['saved_products'] = products

        flash('Product added successfully!', 'success')
        return redirect(url_for('index'))

    except Exception as e:
        flash(f'Error adding product: {str(e)}', 'danger')
        return redirect(url_for('index'))


def save_json_file(order_data):
    try:
        # Create JSON files directory if it doesn't exist
        if not os.path.exists('JSON files'):
            os.makedirs('JSON files')

        # Generate filename
        client_name = order_data.get('client_first_name', 'unknown') + '_' + order_data.get('client_last_name', 'client')
        payment_method = order_data.get('order_payment_method', 'unknown')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{client_name}_{payment_method}_{timestamp}.json"

        # Save the file with the new JSON structure
        filepath = os.path.join('JSON files', filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(order_data, f, indent=2, ensure_ascii=False)

        return True
    except Exception as e:
        print(f"Error saving JSON file: {str(e)}")
        return False


def prepare_order_data():
    order_data = session.get('order_data', DEFAULT_DATA.copy())
    products = session.get('products', [])
    payments = session.get('payments', [])

    # Calculate totals with 2 decimal places
    order_product_total_value = round(sum(product.get('row_net_total', 0) for product in products), 2)
    order_total_discount = round(sum(product.get('row_total_discount', 0) for product in products), 2)
    delivery_cost = round(order_data.get('order_delivery_cost', 0), 2)
    order_final_total_value = round(order_product_total_value + delivery_cost, 2)

    # Format time values for API compatibility - ensure proper format
    delivery_from_time = order_data.get('delivery_from_time', '')
    delivery_to_time = order_data.get('delivery_to_time', '')

    # Convert time format to ensure it's in HH:MM:SS format
    if delivery_from_time:
        if len(delivery_from_time) == 5:  # HH:MM format
            delivery_from_time += ":00"
        elif '.' in delivery_from_time:  # HH:MM:SS.mmm format
            delivery_from_time = delivery_from_time.split('.')[0]  # Remove milliseconds

    if delivery_to_time:
        if len(delivery_to_time) == 5:  # HH:MM format
            delivery_to_time += ":00"
        elif '.' in delivery_to_time:  # HH:MM:SS.mmm format
            delivery_to_time = delivery_to_time.split('.')[0]  # Remove milliseconds

    # Prepare final order data with the new structure
    final_order_data = {
        "branch_code": order_data.get('branch_code', ''),
        "order_code": order_data.get('order_code', ''),
        "parent_order_code": order_data.get('parent_order_code', ''),
        "order_creation_date": datetime.now().isoformat() + 'Z',
        "order_notes": order_data.get('order_notes', "Don't Ring the bell"),
        "order_product_total_value": order_product_total_value,
        "is_delivery": order_data.get('is_delivery', 1),
        "order_delivery_cost": delivery_cost,
        "order_total_discount": order_total_discount,
        "order_final_total_value": order_final_total_value,
        "order_payment_method": ",".join([payment.get('payment_method', '') for payment in payments]),
        "order_status": order_data.get('order_status', 'new'),
        "client_country_code": order_data.get('client_country_code', '966'),
        "client_phone": order_data.get('client_phone', ''),
        "client_first_name": order_data.get('client_first_name', ''),
        "client_middle_name": order_data.get('client_middle_name', ''),
        "client_last_name": order_data.get('client_last_name', ''),
        "client_email": order_data.get('client_email', ''),
        "client_birthdate": order_data.get('client_birthdate', ''),
        "client_gender": order_data.get('client_gender', 'Male'),
        "order_address": order_data.get('order_address', ''),
        "address_code": order_data.get('address_code', ''),
        "order_country_code": order_data.get('order_country_code', ''),
        "order_phone": order_data.get('order_phone', ''),
        "order_payment_status": order_data.get('order_payment_status', 'not_payment'),
        "order_gps": order_data.get('order_gps', [21.779006345949554, 39.08578576461103]),
        "order_products": products,
        "payment_methods_with_options": payments,
        "delivery_date": order_data.get('delivery_date', ''),
        "delivery_from_time": delivery_from_time,
        "delivery_to_time": delivery_to_time,
        "shipping_address_2": order_data.get('shipping_address_2', ''),
        "fullfilment_plant": order_data.get('fullfilment_plant', '')
    }

    # Ensure all numeric values in products have 2 decimal places
    for product in final_order_data['order_products']:
        for key, value in product.items():
            if isinstance(value, float):
                product[key] = round(value, 2)

    # Ensure all numeric values in payments have 2 decimal places
    for payment in final_order_data['payment_methods_with_options']:
        for key, value in payment.items():
            if isinstance(value, float):
                payment[key] = round(value, 2)
            elif key == 'credit_customer_info' and value:
                # Handle nested customer info if needed
                pass

    final_order_data = {k: v for k, v in final_order_data.items() if v is not None}

    return final_order_data


def validate_order_data(order_data):
    """Validate order data before sending to API"""
    errors = []

    # Required fields validation
    required_fields = ['branch_code', 'order_code', 'client_phone', 'client_first_name',
                       'client_last_name', 'order_address']

    for field in required_fields:
        if not order_data.get(field):
            errors.append(f"Missing required field: {field}")

    # Products validation
    if not order_data.get('order_products'):
        errors.append("No products in the order")

    # Payment validation - only required if order has value and not cash on delivery
    order_total = order_data.get('order_final_total_value', 0)
    order_payment_status = order_data.get('order_payment_status', '')

    if order_total > 0 and order_payment_status != 'not_payment' and not order_data.get('payment_methods_with_options'):
        errors.append("Order has value but no payment methods")

    # For PostToCredit with not_payment status, we still need payment info
    has_post_to_credit = any(
        payment.get('payment_method') == 'PostToCredit'
        for payment in order_data.get('payment_methods_with_options', [])
    )

    if order_total > 0 and order_payment_status == 'not_payment' and not has_post_to_credit:
        errors.append("For 'not_payment' status with order value, PostToCredit payment method is required")

    return errors


@app.context_processor
def inject_global_variables():
    return dict(
        api_urls=API_URLS,
        payment_methods=PAYMENT_METHODS,
        payment_statuses=PAYMENT_STATUSES,
        payment_options=PAYMENT_OPTIONS
    )


@app.context_processor
def inject_session_data():
    return dict(
        data=session.get('order_data', DEFAULT_DATA),
        products=session.get('products', []),
        payments=session.get('payments', [])
    )


if __name__ == '__main__':
    app.run(debug=True, port=5002)
