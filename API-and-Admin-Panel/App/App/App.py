"""
Transportation Management System - Main Application Entry Point.

A Flask-based web server that manages delivery jobs, drivers, vehicles,
customers, receipts, shipments, and routes. Registers Blueprints for:
  - Customer website (/home)
  - REST API (/api)
  - Admin panel (/admin)

Flow name: ApplicationBootstrapFlow
Entrypoint: app (Flask instance)
Contract:
  - Inputs: Environment variables (HOST, PORT) or defaults
  - Outputs: Running Flask web server
  - Side effects: Initializes SQLite database, seeds demo data
"""

import os
import sys
import logging

# Configure logging early
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

from flask import Flask, redirect, jsonify

# Ensure the App directory is on the path for imports
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from extensions import db
from Website.LandingPage import landing
from API.RestAPI import rest_api
from AdminPanel.AdminPanel import admin_panel

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'tms-dev-secret-key-change-in-prod')

# Database configuration
app.config['SQLITE_DB_PATH'] = os.path.join(APP_DIR, 'tms.db')

# Upload folder configuration
UPLOAD_FOLDER = os.path.join(APP_DIR, 'AdminPanel', 'static', 'images', 'receipts')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize database
db.init_app(app)

# Seed demo data on startup
from seed import seed_database
with app.app_context():
    seed_database(db)

# Register blueprints
app.register_blueprint(landing, url_prefix='/home')
app.register_blueprint(rest_api, url_prefix='/api')
app.register_blueprint(admin_panel, url_prefix='/admin')

logger.info("ApplicationBootstrapFlow: all blueprints registered")


@app.route('/')
def hello():
    """Redirect root URL to the customer website landing page."""
    return redirect("/home", code=301)


# PUBLIC_INTERFACE
@app.route('/healthz')
def health_check():
    """
    Health check endpoint for monitoring and load balancers.

    Returns:
        JSON response with status 'ok' and HTTP 200.

    This endpoint verifies the application is running and can
    respond to requests. Used by deployment infrastructure.
    """
    return jsonify({"status": "ok", "service": "Transportation Management System"}), 200


# PUBLIC_INTERFACE
@app.route('/api-docs')
def api_docs():
    """
    API documentation endpoint listing all available REST API routes.

    Returns:
        JSON response with categorized API endpoint documentation.
    """
    docs = {
        "service": "Transportation Management System API",
        "version": "2.0",
        "base_url": "/api",
        "endpoints": {
            "health": {
                "GET /healthz": "Health check endpoint"
            },
            "jobs": {
                "GET /api/jobs": "List all jobs (optional: ?limit1=N&limit2=M for pagination)",
                "POST /api/jobs": "Create a new job (params via query string or JSON body)",
                "GET /api/jobs/<id>": "Get job by ID",
                "PUT /api/jobs/<id>": "Update job by ID",
                "DELETE /api/jobs/<id>": "Delete job by ID",
                "GET /api/jobs/pending": "List pending jobs",
                "GET /api/jobs/delivered": "List delivered jobs",
                "GET /api/jobs/in-transit": "List in-transit jobs",
                "GET /api/jobs/<trackingId>/location": "Track parcel by tracking ID",
                "GET /api/jobs/full/<id>": "Get full job details with customer and locations",
                "PUT /api/jobs/<id>/status": "Update job status (Pending -> In Transit -> Delivered)"
            },
            "shipments": {
                "GET /api/shipments": "List all shipments",
                "POST /api/shipments": "Create a new shipment",
                "GET /api/shipments/<id>": "Get shipment by ID",
                "PUT /api/shipments/<id>": "Update shipment",
                "PUT /api/shipments/<id>/status": "Update shipment status",
                "PUT /api/shipments/<id>/assign": "Assign driver and vehicle to shipment",
                "GET /api/shipments/track/<tracking_number>": "Track shipment by tracking number"
            },
            "routes": {
                "GET /api/routes": "List all routes",
                "POST /api/routes": "Create a new route with stops",
                "GET /api/routes/<id>": "Get route details with stops",
                "PUT /api/routes/<id>/status": "Update route status"
            },
            "drivers": {
                "GET /api/drivers": "List all drivers",
                "POST /api/drivers": "Create a new driver",
                "GET /api/drivers/<id>": "Get driver by ID",
                "PUT /api/drivers/<id>": "Update driver",
                "DELETE /api/drivers/<id>": "Delete driver",
                "GET /api/drivers/<id>/location": "Get driver location",
                "POST /api/drivers/login": "Driver login (Android app)",
                "GET /api/drivers/assigned/<id>": "Get assigned jobs for driver"
            },
            "vehicles": {
                "GET /api/vehicles": "List all vehicles",
                "POST /api/vehicles": "Create a new vehicle",
                "GET /api/vehicles/<id>": "Get vehicle by ID",
                "PUT /api/vehicles/<id>": "Update vehicle",
                "DELETE /api/vehicles/<id>": "Delete vehicle"
            },
            "customers": {
                "GET /api/customers": "List all customers",
                "POST /api/customers": "Create a new customer",
                "GET /api/customers/<id>": "Get customer by ID",
                "PUT /api/customers/<id>": "Update customer",
                "DELETE /api/customers/<id>": "Delete customer"
            },
            "locations": {
                "GET /api/locations": "List all locations",
                "POST /api/locations": "Create a new location",
                "GET /api/locations/<id>": "Get location by ID",
                "PUT /api/locations/<id>": "Update location",
                "DELETE /api/locations/<id>": "Delete location"
            },
            "receipts": {
                "GET /api/receipts": "List all receipts",
                "POST /api/receipts": "Create a new receipt",
                "GET /api/receipts/<id>": "Get receipt by ID",
                "PUT /api/receipts/<id>": "Update receipt",
                "DELETE /api/receipts/<id>": "Delete receipt",
                "GET /api/receipts/driver/<id>": "Get today's receipts for driver",
                "POST /api/receipts/uploads": "Upload receipt image file"
            },
            "dashboard": {
                "GET /api/money": "Monthly revenue and receipts summary",
                "GET /api/dashboard/stats": "Dashboard statistics summary"
            }
        }
    }
    return jsonify(docs), 200


if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '3001'))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    logger.info("ApplicationBootstrapFlow: starting server on %s:%d (debug=%s)", host, port, debug)
    app.run(host=host, port=port, debug=debug)
