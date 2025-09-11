markdown

# Online Order Tool

A comprehensive Flask web application for creating, managing, and submitting pharmacy orders to multiple backend systems. The tool features fast
product lookup from SQL Server databases, flexible multi-payment handling, and JSON export for traceability.

## Features

- **Order Management**: Create and manage pharmacy orders with detailed product information
- **Database Integration**: Direct connection to SQL Server for real-time product lookup
- **Multi-payment Support**: Handle various payment methods including Visa, Points, Tamara, Tabby, and more
- **API Integration**: Send orders to multiple pharmacy backend systems
- **Order Cancellation**: Cancel orders with proper reason tracking
- **Theme Customization**: Light/dark mode with multiple color themes
- **JSON Export**: Export order data for documentation and traceability

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Online_Order_Tool

2. **Create a virtual environment**
    ```bash
    python -m venv venv
    source venv/bin/activate # On Windows: venv\Scripts\activate
   
3. **Install dependencies**
    ```bash
    pip install -r requirements.txt
    Configure database connection

# Notes:
#### 1- Update the database connection settings in config.py if needed
#### 2- The default uses Windows Authentication with SQL Server
#### 3- Run the application
#### 4- Open your browser and navigate to http://localhost:5002