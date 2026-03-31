"""
Transportation Management System - REST API Blueprint.

Provides all RESTful endpoints for managing jobs, drivers, vehicles,
customers, locations, receipts, shipments, and routes.

Flow name: RestAPIFlow
Entrypoint: rest_api Blueprint registered at /api
Contract:
  - Inputs: HTTP requests (GET/POST/PUT/DELETE) with JSON body or query params
  - Outputs: JSON responses with appropriate HTTP status codes
  - Errors: 404 for not found, 400 for bad requests, 500 for server errors
  - Side effects: Database reads/writes
"""

import sys
import os
import json
import datetime
import uuid
import logging

from flask import Blueprint, jsonify, make_response, request
from flask import current_app as app
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Ensure imports work
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from extensions import db

logger = logging.getLogger(__name__)

rest_api = Blueprint('rest_api', __name__)
CORS(rest_api)


# ---------------------------------------------------------------------------
# Helper: convert sqlite3.Row results to list of dicts
# ---------------------------------------------------------------------------
def _rows_to_dicts(cursor):
    """Convert cursor results to a list of dictionaries."""
    if cursor.description is None:
        return []
    row_headers = [x[0] for x in cursor.description]
    rv = cursor.fetchall()
    return [dict(zip(row_headers, row)) for row in rv]


def _json_response(data, status=200):
    """Create a JSON response with proper content type."""
    resp = make_response(json.dumps(data, default=str))
    resp.headers['Content-Type'] = 'application/json'
    resp.status_code = status
    return resp


def _get_request_data():
    """
    Extract request data from either JSON body or query parameters.

    Returns:
        dict: Merged data from JSON body and query parameters.
    """
    data = {}
    if request.args:
        data.update(request.args.to_dict())
    if request.is_json:
        data.update(request.get_json(silent=True) or {})
    return data


# ---------------------------------------------------------------------------
# API Root
# ---------------------------------------------------------------------------

# PUBLIC_INTERFACE
@rest_api.route("/")
def api_default():
    """
    API root endpoint returning service metadata.

    Returns:
        JSON with API name, version, and timestamps.
    """
    return make_response(jsonify([{
        "Name": "Transportation Management System REST API",
        "Version": "2.0",
        "Description": "Complete TMS API with shipment tracking, route planning, and status management",
        "Docs": "/api-docs"
    }]))


# ===========================================================================
# JOBS ENDPOINTS
# ===========================================================================

# PUBLIC_INTERFACE
@rest_api.route('/jobs/', methods=['GET'])
@rest_api.route('/jobs', methods=['GET', 'POST'])
def return_jobs():
    """
    List all jobs or create a new job.

    GET: Returns all jobs, optionally paginated with ?limit1=N&limit2=M
    POST: Creates a new job from query params or JSON body.

    Returns:
        JSON array of job objects (GET) or success message (POST).
    """
    if request.method == 'GET':
        if "limit1" in request.args and "limit2" in request.args:
            return _get_table("Jobs", request.args["limit1"], request.args["limit2"])
        else:
            return _get_all_table("Jobs")
    elif request.method == 'POST':
        return _create_job(request)


# PUBLIC_INTERFACE
@rest_api.route('/jobs/<int:id>/', methods=['GET'])
@rest_api.route('/jobs/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def get_job(id):
    """
    Get, update, or delete a specific job by ID.

    Args:
        id: Job ID (integer).

    Returns:
        JSON job object (GET), success message (PUT/DELETE), or 404 error.
    """
    if request.method == 'GET':
        return _get_record("Jobs", "JobID", id)
    elif request.method == 'PUT':
        return _update_table(request, 'Jobs', 'JobID', id)
    elif request.method == 'DELETE':
        return _delete_record("Jobs", "JobID", id)


# PUBLIC_INTERFACE
@rest_api.route('/jobs/<int:id>/status', methods=['PUT'])
def update_job_status(id):
    """
    Update job status with validation of allowed transitions.

    Allowed transitions: Pending -> In Transit -> Delivered

    Args:
        id: Job ID (integer).

    Request body/params:
        Status: New status string.

    Returns:
        JSON success message or error for invalid transitions.
    """
    data = _get_request_data()
    new_status = data.get('Status', '')

    valid_statuses = ['Pending', 'In Transit', 'Delivered']
    if new_status not in valid_statuses:
        return _json_response(
            {"Error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"},
            400
        )

    # Valid transitions
    valid_transitions = {
        'Pending': ['In Transit'],
        'In Transit': ['Delivered'],
        'Delivered': []
    }

    try:
        conn = db.connection
        cur = conn.cursor()
        cur.execute("SELECT Status FROM Jobs WHERE JobID = ?", (id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return _json_response({"Error": "Job not found"}, 404)

        current_status = row[0]
        if new_status not in valid_transitions.get(current_status, []):
            conn.close()
            return _json_response(
                {"Error": f"Cannot transition from '{current_status}' to '{new_status}'. "
                          f"Allowed: {valid_transitions.get(current_status, [])}"},
                400
            )

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if new_status == 'Delivered':
            cur.execute(
                "UPDATE Jobs SET Status = ?, DateDelivered = ? WHERE JobID = ?",
                (new_status, now, id)
            )
        else:
            cur.execute("UPDATE Jobs SET Status = ? WHERE JobID = ?", (new_status, id))
        conn.commit()
        conn.close()

        logger.info("RestAPIFlow: Job %d status changed: %s -> %s", id, current_status, new_status)
        return _json_response({"Success": f"Job status updated to '{new_status}'"})

    except Exception as e:
        logger.error("RestAPIFlow: failed to update job status: %s", str(e))
        return _json_response({"Error": str(e)}, 500)


# PUBLIC_INTERFACE
@rest_api.route('/jobs/pending', methods=['GET'])
def return_pending_jobs():
    """
    List all jobs with 'Pending' status.

    Returns:
        JSON array of pending job objects.
    """
    return _get_jobs_by_status('Pending')


# PUBLIC_INTERFACE
@rest_api.route('/jobs/delivered', methods=['GET'])
def return_done_jobs():
    """
    List all jobs with 'Delivered' status.

    Returns:
        JSON array of delivered job objects.
    """
    return _get_jobs_by_status('Delivered')


# PUBLIC_INTERFACE
@rest_api.route('/jobs/in-transit', methods=['GET'])
def return_in_transit_jobs():
    """
    List all jobs with 'In Transit' status.

    Returns:
        JSON array of in-transit job objects.
    """
    return _get_jobs_by_status('In Transit')


def _get_jobs_by_status(status):
    """Retrieve jobs filtered by status with optional pagination."""
    try:
        conn = db.connection
        cur = conn.cursor()
        if "limit1" in request.args and "limit2" in request.args:
            cur.execute(
                "SELECT * FROM Jobs WHERE Status=? LIMIT ? OFFSET ?",
                (status, int(request.args['limit1']), int(request.args['limit2']))
            )
        else:
            cur.execute("SELECT * FROM Jobs WHERE Status=?", (status,))
        json_data = _rows_to_dicts(cur)
        conn.close()
        return _json_response(json_data)
    except Exception as e:
        logger.error("RestAPIFlow: failed to get jobs by status: %s", str(e))
        return _json_response({"Error": str(e)}, 500)


# PUBLIC_INTERFACE
@rest_api.route('/jobs/<string:id>/location', methods=['GET'])
def get_parcel_location(id):
    """
    Get driver location for a parcel by tracking ID.

    Args:
        id: Tracking ID string.

    Returns:
        JSON with driver ID, name, and location coordinates.
    """
    try:
        conn = db.connection
        cur = conn.cursor()
        cur.execute("SELECT DriverID FROM Jobs WHERE TrackingID=?", (id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return make_response(jsonify([{"Error": "No matching tracking ID found."}]), 404)

        driver_id = row[0]
        if driver_id is None:
            conn.close()
            return make_response(jsonify([{"Error": "No driver assigned to this job."}]), 404)

        cur.execute(
            "SELECT DriverID, FirstName, Location FROM Drivers WHERE DriverID=?",
            (driver_id,)
        )
        json_data = _rows_to_dicts(cur)
        conn.close()
        if not json_data:
            return make_response(jsonify([{"Error": "Driver not found."}]), 404)
        return _json_response(json_data)
    except Exception as e:
        logger.error("RestAPIFlow: failed to get parcel location: %s", str(e))
        return _json_response({"Error": str(e)}, 500)


# PUBLIC_INTERFACE
@rest_api.route('/jobs/full/<int:id>/', methods=['GET'])
@rest_api.route('/jobs/full/<int:id>', methods=['GET'])
def get_full_job(id):
    """
    Get comprehensive job details including customer, pickup, and dropoff info.

    Args:
        id: Job ID (integer).

    Returns:
        JSON object with Job, Customer, Pickup, and Dropoff data.
    """
    try:
        conn = db.connection
        cur = conn.cursor()

        # Get job data
        cur.execute(
            "SELECT JobID, TrackingID, Status, ParcelType, ParcelSize, ParcelWeight, "
            "DateCreated, DateDue, DateDelivered, DistanceTravelled, Picture1, Picture2, "
            "Comments, DriverID, CustomerID, PickupID, DropOffID FROM Jobs WHERE JobID = ?",
            (id,)
        )
        job_row = cur.fetchone()
        if not job_row:
            conn.close()
            return _json_response({"Error": "No matching ID found."}, 404)

        job_headers = [x[0] for x in cur.description]
        job_data = dict(zip(job_headers, job_row))

        # Get customer data
        customer_data = {}
        if job_data.get('CustomerID'):
            cur.execute("SELECT * FROM Customers WHERE CustomerID = ?", (job_data['CustomerID'],))
            rows = _rows_to_dicts(cur)
            customer_data = rows[0] if rows else {}

        # Get pickup location
        pickup_data = {}
        if job_data.get('PickupID'):
            cur.execute("SELECT * FROM Locations WHERE LocationID = ?", (job_data['PickupID'],))
            rows = _rows_to_dicts(cur)
            pickup_data = rows[0] if rows else {}

        # Get dropoff location
        dropoff_data = {}
        if job_data.get('DropOffID'):
            cur.execute("SELECT * FROM Locations WHERE LocationID = ?", (job_data['DropOffID'],))
            rows = _rows_to_dicts(cur)
            dropoff_data = rows[0] if rows else {}

        # Get driver data
        driver_data = {}
        if job_data.get('DriverID'):
            cur.execute(
                "SELECT DriverID, FirstName, LastName, Location FROM Drivers WHERE DriverID = ?",
                (job_data['DriverID'],)
            )
            rows = _rows_to_dicts(cur)
            driver_data = rows[0] if rows else {}

        conn.close()

        result = {
            "Job": job_data,
            "Customer": customer_data,
            "Pickup": pickup_data,
            "Dropoff": dropoff_data,
            "Driver": driver_data
        }
        return _json_response(result)

    except Exception as e:
        logger.error("RestAPIFlow: failed to get full job: %s", str(e))
        return _json_response({"Error": str(e)}, 500)


# ===========================================================================
# SHIPMENTS ENDPOINTS
# ===========================================================================

# PUBLIC_INTERFACE
@rest_api.route('/shipments', methods=['GET', 'POST'])
@rest_api.route('/shipments/', methods=['GET'])
def handle_shipments():
    """
    List all shipments or create a new shipment.

    GET: Returns all shipments with optional pagination.
    POST: Creates a new shipment with auto-generated tracking number.

    Request body for POST:
        SenderName, SenderAddress, SenderCity, SenderPostCode,
        ReceiverName, ReceiverAddress, ReceiverCity, ReceiverPostCode,
        Weight, Description, EstimatedDelivery (optional)

    Returns:
        JSON array of shipments (GET) or creation confirmation with tracking number (POST).
    """
    if request.method == 'GET':
        return _get_all_table("Shipments")
    elif request.method == 'POST':
        return _create_shipment()


# PUBLIC_INTERFACE
@rest_api.route('/shipments/<int:id>', methods=['GET', 'PUT'])
@rest_api.route('/shipments/<int:id>/', methods=['GET'])
def handle_shipment(id):
    """
    Get or update a specific shipment.

    Args:
        id: Shipment ID (integer).

    Returns:
        JSON shipment object or success message.
    """
    if request.method == 'GET':
        return _get_record("Shipments", "ShipmentID", id)
    elif request.method == 'PUT':
        return _update_table(request, "Shipments", "ShipmentID", id)


# PUBLIC_INTERFACE
@rest_api.route('/shipments/<int:id>/status', methods=['PUT'])
def update_shipment_status(id):
    """
    Update shipment status with validated transitions.

    Allowed transitions: Pending -> In Transit -> Delivered

    Args:
        id: Shipment ID (integer).

    Request body:
        Status: New status string.

    Returns:
        JSON success/error message.
    """
    data = _get_request_data()
    new_status = data.get('Status', '')

    valid_statuses = ['Pending', 'In Transit', 'Delivered']
    if new_status not in valid_statuses:
        return _json_response(
            {"Error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"},
            400
        )

    valid_transitions = {
        'Pending': ['In Transit'],
        'In Transit': ['Delivered'],
        'Delivered': []
    }

    try:
        conn = db.connection
        cur = conn.cursor()
        cur.execute("SELECT Status FROM Shipments WHERE ShipmentID = ?", (id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return _json_response({"Error": "Shipment not found"}, 404)

        current_status = row[0]
        if new_status not in valid_transitions.get(current_status, []):
            conn.close()
            return _json_response(
                {"Error": f"Cannot transition from '{current_status}' to '{new_status}'"},
                400
            )

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if new_status == 'Delivered':
            cur.execute(
                "UPDATE Shipments SET Status = ?, ActualDelivery = ?, UpdatedAt = ? WHERE ShipmentID = ?",
                (new_status, now, now, id)
            )
        else:
            cur.execute(
                "UPDATE Shipments SET Status = ?, UpdatedAt = ? WHERE ShipmentID = ?",
                (new_status, now, id)
            )
        conn.commit()
        conn.close()

        logger.info("RestAPIFlow: Shipment %d status changed: %s -> %s", id, current_status, new_status)
        return _json_response({"Success": f"Shipment status updated to '{new_status}'"})

    except Exception as e:
        logger.error("RestAPIFlow: failed to update shipment status: %s", str(e))
        return _json_response({"Error": str(e)}, 500)


# PUBLIC_INTERFACE
@rest_api.route('/shipments/<int:id>/assign', methods=['PUT'])
def assign_shipment(id):
    """
    Assign a driver and vehicle to a shipment.

    Args:
        id: Shipment ID (integer).

    Request body:
        DriverID: Driver ID to assign.
        VehicleID: Vehicle ID to assign.

    Returns:
        JSON success/error message.
    """
    data = _get_request_data()
    driver_id = data.get('DriverID')
    vehicle_id = data.get('VehicleID')

    if not driver_id:
        return _json_response({"Error": "DriverID is required"}, 400)

    try:
        conn = db.connection
        cur = conn.cursor()

        # Verify shipment exists
        cur.execute("SELECT ShipmentID FROM Shipments WHERE ShipmentID = ?", (id,))
        if not cur.fetchone():
            conn.close()
            return _json_response({"Error": "Shipment not found"}, 404)

        # Verify driver exists
        cur.execute("SELECT DriverID FROM Drivers WHERE DriverID = ?", (driver_id,))
        if not cur.fetchone():
            conn.close()
            return _json_response({"Error": "Driver not found"}, 404)

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if vehicle_id:
            cur.execute(
                "UPDATE Shipments SET DriverID = ?, VehicleID = ?, UpdatedAt = ? WHERE ShipmentID = ?",
                (driver_id, vehicle_id, now, id)
            )
        else:
            cur.execute(
                "UPDATE Shipments SET DriverID = ?, UpdatedAt = ? WHERE ShipmentID = ?",
                (driver_id, now, id)
            )
        conn.commit()
        conn.close()

        logger.info("RestAPIFlow: Shipment %d assigned to Driver %s", id, driver_id)
        return _json_response({"Success": f"Shipment assigned to driver {driver_id}"})

    except Exception as e:
        logger.error("RestAPIFlow: failed to assign shipment: %s", str(e))
        return _json_response({"Error": str(e)}, 500)


# PUBLIC_INTERFACE
@rest_api.route('/shipments/track/<string:tracking_number>', methods=['GET'])
def track_shipment(tracking_number):
    """
    Track a shipment by its tracking number.

    Args:
        tracking_number: Unique tracking number string.

    Returns:
        JSON with shipment details and assigned driver info.
    """
    try:
        conn = db.connection
        cur = conn.cursor()
        cur.execute("SELECT * FROM Shipments WHERE TrackingNumber = ?", (tracking_number,))
        rows = _rows_to_dicts(cur)

        if not rows:
            conn.close()
            return _json_response({"Error": "Tracking number not found"}, 404)

        shipment = rows[0]

        # Get driver info if assigned
        driver_info = None
        if shipment.get('DriverID'):
            cur.execute(
                "SELECT DriverID, FirstName, LastName, Location FROM Drivers WHERE DriverID = ?",
                (shipment['DriverID'],)
            )
            driver_rows = _rows_to_dicts(cur)
            driver_info = driver_rows[0] if driver_rows else None

        conn.close()
        return _json_response({
            "Shipment": shipment,
            "Driver": driver_info
        })

    except Exception as e:
        logger.error("RestAPIFlow: failed to track shipment: %s", str(e))
        return _json_response({"Error": str(e)}, 500)


def _create_shipment():
    """Create a new shipment with auto-generated tracking number."""
    data = _get_request_data()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tracking = f"TMS{datetime.datetime.now().strftime('%m%y')}{uuid.uuid4().hex[:6].upper()}"

    try:
        conn = db.connection
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Shipments (TrackingNumber, SenderName, SenderAddress, SenderCity, "
            "SenderPostCode, ReceiverName, ReceiverAddress, ReceiverCity, ReceiverPostCode, "
            "Weight, Description, Status, EstimatedDelivery, CreatedAt, UpdatedAt) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?, ?, ?)",
            (
                tracking,
                data.get('SenderName', ''),
                data.get('SenderAddress', ''),
                data.get('SenderCity', ''),
                data.get('SenderPostCode', ''),
                data.get('ReceiverName', ''),
                data.get('ReceiverAddress', ''),
                data.get('ReceiverCity', ''),
                data.get('ReceiverPostCode', ''),
                data.get('Weight', 0),
                data.get('Description', ''),
                data.get('EstimatedDelivery', ''),
                now, now
            )
        )
        conn.commit()
        shipment_id = cur.lastrowid
        conn.close()

        logger.info("RestAPIFlow: created shipment %d with tracking %s", shipment_id, tracking)
        return _json_response({
            "Success": "Shipment created successfully",
            "ShipmentID": shipment_id,
            "TrackingNumber": tracking
        }, 201)

    except Exception as e:
        logger.error("RestAPIFlow: failed to create shipment: %s", str(e))
        return _json_response({"Error": str(e)}, 500)


# ===========================================================================
# ROUTES / ROUTE PLANNING ENDPOINTS
# ===========================================================================

# PUBLIC_INTERFACE
@rest_api.route('/routes', methods=['GET', 'POST'])
@rest_api.route('/routes/', methods=['GET'])
def handle_routes():
    """
    List all routes or create a new route with stops.

    GET: Returns all routes.
    POST: Creates a new route with optional stop definitions.

    Request body for POST:
        DriverID, VehicleID, RouteName, StartLocation, EndLocation,
        EstimatedDistance, EstimatedDuration, PlannedDate,
        Stops (optional array of {ShipmentID, StopOrder, Address, City, PostCode, StopType})

    Returns:
        JSON array of routes (GET) or creation confirmation (POST).
    """
    if request.method == 'GET':
        return _get_all_table("Routes")
    elif request.method == 'POST':
        return _create_route()


# PUBLIC_INTERFACE
@rest_api.route('/routes/<int:id>', methods=['GET'])
@rest_api.route('/routes/<int:id>/', methods=['GET'])
def get_route(id):
    """
    Get route details including all stops.

    Args:
        id: Route ID (integer).

    Returns:
        JSON object with route details and array of stops.
    """
    try:
        conn = db.connection
        cur = conn.cursor()

        cur.execute("SELECT * FROM Routes WHERE RouteID = ?", (id,))
        route_rows = _rows_to_dicts(cur)
        if not route_rows:
            conn.close()
            return _json_response({"Error": "Route not found"}, 404)

        cur.execute(
            "SELECT rs.*, s.TrackingNumber, s.ReceiverName, s.Status as ShipmentStatus "
            "FROM RouteStops rs LEFT JOIN Shipments s ON rs.ShipmentID = s.ShipmentID "
            "WHERE rs.RouteID = ? ORDER BY rs.StopOrder",
            (id,)
        )
        stops = _rows_to_dicts(cur)

        # Get driver info
        driver_info = None
        if route_rows[0].get('DriverID'):
            cur.execute(
                "SELECT DriverID, FirstName, LastName FROM Drivers WHERE DriverID = ?",
                (route_rows[0]['DriverID'],)
            )
            d_rows = _rows_to_dicts(cur)
            driver_info = d_rows[0] if d_rows else None

        conn.close()
        return _json_response({
            "Route": route_rows[0],
            "Stops": stops,
            "Driver": driver_info
        })

    except Exception as e:
        logger.error("RestAPIFlow: failed to get route: %s", str(e))
        return _json_response({"Error": str(e)}, 500)


# PUBLIC_INTERFACE
@rest_api.route('/routes/<int:id>/status', methods=['PUT'])
def update_route_status(id):
    """
    Update route status.

    Allowed statuses: Planned, Active, Completed, Cancelled

    Args:
        id: Route ID (integer).

    Request body:
        Status: New status string.

    Returns:
        JSON success/error message.
    """
    data = _get_request_data()
    new_status = data.get('Status', '')

    valid_statuses = ['Planned', 'Active', 'Completed', 'Cancelled']
    if new_status not in valid_statuses:
        return _json_response(
            {"Error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"},
            400
        )

    try:
        conn = db.connection
        cur = conn.cursor()
        cur.execute("SELECT RouteID FROM Routes WHERE RouteID = ?", (id,))
        if not cur.fetchone():
            conn.close()
            return _json_response({"Error": "Route not found"}, 404)

        cur.execute("UPDATE Routes SET Status = ? WHERE RouteID = ?", (new_status, id))
        conn.commit()
        conn.close()

        logger.info("RestAPIFlow: Route %d status changed to %s", id, new_status)
        return _json_response({"Success": f"Route status updated to '{new_status}'"})

    except Exception as e:
        logger.error("RestAPIFlow: failed to update route status: %s", str(e))
        return _json_response({"Error": str(e)}, 500)


def _create_route():
    """Create a new route with optional stops."""
    data = _get_request_data()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        conn = db.connection
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Routes (DriverID, VehicleID, RouteName, StartLocation, EndLocation, "
            "EstimatedDistance, EstimatedDuration, Status, PlannedDate, CreatedAt) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'Planned', ?, ?)",
            (
                data.get('DriverID'),
                data.get('VehicleID'),
                data.get('RouteName', ''),
                data.get('StartLocation', ''),
                data.get('EndLocation', ''),
                data.get('EstimatedDistance', 0),
                data.get('EstimatedDuration', ''),
                data.get('PlannedDate', ''),
                now
            )
        )
        route_id = cur.lastrowid

        # Add stops if provided
        stops = data.get('Stops', [])
        if isinstance(stops, str):
            try:
                stops = json.loads(stops)
            except (json.JSONDecodeError, TypeError):
                stops = []

        for stop in stops:
            cur.execute(
                "INSERT INTO RouteStops (RouteID, ShipmentID, StopOrder, Address, City, "
                "PostCode, StopType, Status) VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending')",
                (
                    route_id,
                    stop.get('ShipmentID'),
                    stop.get('StopOrder', 0),
                    stop.get('Address', ''),
                    stop.get('City', ''),
                    stop.get('PostCode', ''),
                    stop.get('StopType', 'Delivery')
                )
            )

        conn.commit()
        conn.close()

        logger.info("RestAPIFlow: created route %d with %d stops", route_id, len(stops))
        return _json_response({
            "Success": "Route created successfully",
            "RouteID": route_id
        }, 201)

    except Exception as e:
        logger.error("RestAPIFlow: failed to create route: %s", str(e))
        return _json_response({"Error": str(e)}, 500)


# ===========================================================================
# DRIVERS ENDPOINTS
# ===========================================================================

# PUBLIC_INTERFACE
@rest_api.route('/drivers/', methods=['GET'])
@rest_api.route('/drivers', methods=['GET', 'POST'])
def return_drivers():
    """
    List all drivers or create a new driver.

    GET: Returns all drivers (without passwords), optionally paginated.
    POST: Creates a new driver from query params or JSON body.

    Returns:
        JSON array of driver objects (GET) or success message (POST).
    """
    if request.method == 'GET':
        try:
            conn = db.connection
            cur = conn.cursor()
            sql = ('SELECT DriverID, VehicleID, Username, LastName, FirstName, DOB, NINo, '
                   'DrivingLicenseNo, DrivingLicensePic, Address1, Address2, City, PostCode, '
                   'Country, Location, DateCreated, LastConnected FROM Drivers')
            if "limit1" in request.args and "limit2" in request.args:
                sql += ' LIMIT ? OFFSET ?'
                cur.execute(sql, (int(request.args["limit1"]), int(request.args["limit2"])))
            else:
                cur.execute(sql)
            json_data = _rows_to_dicts(cur)
            conn.close()
            return _json_response(json_data)
        except Exception as e:
            logger.error("RestAPIFlow: failed to get drivers: %s", str(e))
            return _json_response({"Error": str(e)}, 500)
    elif request.method == 'POST':
        return _create_driver(request)


# PUBLIC_INTERFACE
@rest_api.route('/drivers/<int:id>/', methods=['GET'])
@rest_api.route('/drivers/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def get_driver(id):
    """
    Get, update, or delete a specific driver.

    Args:
        id: Driver ID (integer).

    Returns:
        JSON driver object (GET), success message (PUT/DELETE), or 404 error.
    """
    if request.method == 'GET':
        try:
            conn = db.connection
            cur = conn.cursor()
            cur.execute(
                "SELECT DriverID, VehicleID, LastName, FirstName, DOB, NINo, "
                "DrivingLicenseNo, DrivingLicensePic, Address1, Address2, City, PostCode, "
                "Country, Location, DateCreated, LastConnected FROM Drivers WHERE DriverID = ?",
                (id,)
            )
            json_data = _rows_to_dicts(cur)
            conn.close()
            if not json_data:
                return make_response(jsonify([{"Error": "No matching ID found."}]), 404)
            return _json_response(json_data)
        except Exception as e:
            return _json_response({"Error": str(e)}, 500)
    elif request.method == 'PUT':
        return _update_table(request, 'Drivers', 'DriverID', id)
    elif request.method == 'DELETE':
        return _delete_record("Drivers", "DriverID", id)


# PUBLIC_INTERFACE
@rest_api.route('/drivers/<int:id>/location', methods=['GET', 'PUT'])
def get_location(id):
    """
    Get or update a driver's location.

    Args:
        id: Driver ID (integer).

    Returns:
        JSON with driver location (GET) or success message (PUT).
    """
    if request.method == 'GET':
        try:
            conn = db.connection
            cur = conn.cursor()
            cur.execute(
                "SELECT DriverID, FirstName, Location FROM Drivers WHERE DriverID=?",
                (id,)
            )
            json_data = _rows_to_dicts(cur)
            conn.close()
            if not json_data:
                return make_response(jsonify([{"Error": "No matching ID found."}]), 404)
            return _json_response(json_data)
        except Exception as e:
            return _json_response({"Error": str(e)}, 500)
    elif request.method == 'PUT':
        return _update_table(request, 'Drivers', 'DriverID', id)


# PUBLIC_INTERFACE
@rest_api.route('/drivers/login', methods=['POST'])
def driver_login():
    """
    Authenticate a driver (used by Android app).

    Request params:
        Username: Driver username.
        Password: Driver password.

    Returns:
        JSON with login status and driver info on success.
    """
    data = _get_request_data()
    username = data.get('Username', '')
    password = data.get('Password', '')

    try:
        conn = db.connection
        cur = conn.cursor()
        cur.execute("SELECT Password FROM Drivers WHERE Username=?", (username,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return make_response(jsonify([{
                "Status": "Error",
                "Message": "Login failed: Wrong Username"
            }]), 200)

        if password == row[0]:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute(
                "UPDATE Drivers SET LastConnected = ? WHERE Username=?",
                (now, username)
            )
            conn.commit()
            cur.execute(
                "SELECT DriverID, FirstName, LastConnected, VehicleID FROM Drivers WHERE Username=?",
                (username,)
            )
            result = cur.fetchone()
            conn.close()
            return make_response(jsonify([{
                "Status": "Success",
                "Message": "Login Successful",
                "DriverID": result[0],
                "FirstName": result[1],
                "LastConnected": result[2],
                "VehicleID": result[3]
            }]), 200)
        else:
            conn.close()
            return make_response(jsonify([{
                "Status": "Error",
                "Message": "Login failed: Wrong Password"
            }]), 200)
    except Exception as e:
        logger.error("RestAPIFlow: driver login failed: %s", str(e))
        return _json_response({"Error": str(e)}, 500)


# PUBLIC_INTERFACE
@rest_api.route('/drivers/assigned/<int:id>/', methods=['GET'])
@rest_api.route('/drivers/assigned/<int:id>', methods=['GET'])
def get_assigned_jobs(id):
    """
    Get all assigned pending jobs for a driver with full details.

    Args:
        id: Driver ID (integer).

    Returns:
        JSON array of full job objects assigned to the driver.
    """
    try:
        conn = db.connection
        cur = conn.cursor()
        cur.execute(
            "SELECT JobID FROM Jobs WHERE (Status='Pending' OR Status='In Transit') AND DriverID=?",
            (id,)
        )
        rows = _rows_to_dicts(cur)

        if not rows:
            conn.close()
            return _json_response({"Error": "No jobs found."}, 404)

        # Build full job data locally (no external HTTP calls)
        full_array = []
        for row in rows:
            job_id = row['JobID']
            cur.execute(
                "SELECT * FROM Jobs WHERE JobID = ?", (job_id,)
            )
            job_data = _rows_to_dicts(cur)
            if job_data:
                job = job_data[0]
                # Get customer
                customer = {}
                if job.get('CustomerID'):
                    cur.execute("SELECT * FROM Customers WHERE CustomerID = ?", (job['CustomerID'],))
                    c_rows = _rows_to_dicts(cur)
                    customer = c_rows[0] if c_rows else {}
                # Get pickup
                pickup = {}
                if job.get('PickupID'):
                    cur.execute("SELECT * FROM Locations WHERE LocationID = ?", (job['PickupID'],))
                    p_rows = _rows_to_dicts(cur)
                    pickup = p_rows[0] if p_rows else {}
                # Get dropoff
                dropoff = {}
                if job.get('DropOffID'):
                    cur.execute("SELECT * FROM Locations WHERE LocationID = ?", (job['DropOffID'],))
                    d_rows = _rows_to_dicts(cur)
                    dropoff = d_rows[0] if d_rows else {}

                full_array.append({
                    "Job": job,
                    "Customer": customer,
                    "Pickup": pickup,
                    "Dropoff": dropoff
                })

        conn.close()
        return _json_response(full_array)

    except Exception as e:
        logger.error("RestAPIFlow: failed to get assigned jobs: %s", str(e))
        return _json_response({"Error": str(e)}, 500)


def _create_driver(request):
    """Create a new driver with auto-generated username."""
    data = _get_request_data()
    first_name = data.get('FirstName', 'Driver')
    last_name = data.get('LastName', 'New')
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        conn = db.connection
        cur = conn.cursor()

        # Generate unique username
        base_uname = (first_name + last_name).lower()
        uname = base_uname
        counter = 1
        while True:
            cur.execute("SELECT COUNT(*) FROM Drivers WHERE Username=?", (uname,))
            if cur.fetchone()[0] == 0:
                break
            uname = f"{base_uname}{counter}"
            counter += 1

        cur.execute(
            "INSERT INTO Drivers (VehicleID, Username, Password, LastName, FirstName, DOB, "
            "NINo, DrivingLicenseNo, DrivingLicensePic, Address1, Address2, City, PostCode, "
            "Country, Location, DateCreated) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                data.get('VehicleID'),
                uname,
                data.get('Password', 'driver123'),
                last_name,
                first_name,
                data.get('DOB'),
                data.get('NINo'),
                data.get('DrivingLicenseNo'),
                data.get('DrivingLicensePic'),
                data.get('Address1'),
                data.get('Address2'),
                data.get('City'),
                data.get('PostCode'),
                data.get('Country'),
                data.get('Location'),
                now
            )
        )
        conn.commit()
        conn.close()

        logger.info("RestAPIFlow: created driver with username %s", uname)
        return _json_response({"Success": f"Driver created with username '{uname}'"}, 201)

    except Exception as e:
        logger.error("RestAPIFlow: failed to create driver: %s", str(e))
        return _json_response({"Error": str(e)}, 500)


# ===========================================================================
# VEHICLES ENDPOINTS
# ===========================================================================

# PUBLIC_INTERFACE
@rest_api.route('/vehicles/', methods=['GET'])
@rest_api.route('/vehicles', methods=['GET', 'POST'])
def return_vehicles():
    """
    List all vehicles or create a new vehicle.

    Returns:
        JSON array of vehicles (GET) or success message (POST).
    """
    if request.method == 'GET':
        if "limit1" in request.args and "limit2" in request.args:
            return _get_table("Vehicles", request.args["limit1"], request.args["limit2"])
        else:
            return _get_all_table("Vehicles")
    elif request.method == 'POST':
        return _create_generic(request, "Vehicles", "VehicleID")


# PUBLIC_INTERFACE
@rest_api.route('/vehicles/<int:id>/', methods=['GET'])
@rest_api.route('/vehicles/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def get_vehicle(id):
    """
    Get, update, or delete a specific vehicle.

    Args:
        id: Vehicle ID (integer).
    """
    if request.method == 'GET':
        return _get_record("Vehicles", "VehicleID", id)
    elif request.method == 'PUT':
        return _update_table(request, 'Vehicles', 'VehicleID', id)
    elif request.method == 'DELETE':
        return _delete_record("Vehicles", "VehicleID", id)


# ===========================================================================
# CUSTOMERS ENDPOINTS
# ===========================================================================

# PUBLIC_INTERFACE
@rest_api.route('/customers/', methods=['GET'])
@rest_api.route('/customers', methods=['GET', 'POST'])
def return_customers():
    """
    List all customers or create a new customer.

    Returns:
        JSON array of customers (GET) or success message (POST).
    """
    if request.method == 'GET':
        if "limit1" in request.args and "limit2" in request.args:
            return _get_table("Customers", request.args["limit1"], request.args["limit2"])
        else:
            return _get_all_table("Customers")
    elif request.method == 'POST':
        return _create_generic(request, "Customers", "CustomerID")


# PUBLIC_INTERFACE
@rest_api.route('/customers/<int:id>/', methods=['GET'])
@rest_api.route('/customers/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def get_customer(id):
    """
    Get, update, or delete a specific customer.

    Args:
        id: Customer ID (integer).
    """
    if request.method == 'GET':
        return _get_record("Customers", "CustomerID", id)
    elif request.method == 'PUT':
        return _update_table(request, 'Customers', 'CustomerID', id)
    elif request.method == 'DELETE':
        return _delete_record("Customers", "CustomerID", id)


# ===========================================================================
# LOCATIONS ENDPOINTS
# ===========================================================================

# PUBLIC_INTERFACE
@rest_api.route('/locations/', methods=['GET'])
@rest_api.route('/locations', methods=['GET', 'POST'])
def return_locations():
    """
    List all locations or create a new location.

    Returns:
        JSON array of locations (GET) or success message (POST).
    """
    if request.method == 'GET':
        if "limit1" in request.args and "limit2" in request.args:
            return _get_table("Locations", request.args["limit1"], request.args["limit2"])
        else:
            return _get_all_table("Locations")
    elif request.method == 'POST':
        return _create_generic(request, "Locations", "LocationID")


# PUBLIC_INTERFACE
@rest_api.route('/locations/<int:id>/', methods=['GET'])
@rest_api.route('/locations/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def get_location_by_id(id):
    """
    Get, update, or delete a specific location.

    Args:
        id: Location ID (integer).
    """
    if request.method == 'GET':
        return _get_record("Locations", "LocationID", id)
    elif request.method == 'PUT':
        return _update_table(request, 'Locations', 'LocationID', id)
    elif request.method == 'DELETE':
        return _delete_record("Locations", "LocationID", id)


# ===========================================================================
# RECEIPTS ENDPOINTS
# ===========================================================================

# PUBLIC_INTERFACE
@rest_api.route('/receipts/', methods=['GET'])
@rest_api.route('/receipts', methods=['GET', 'POST'])
def return_receipts():
    """
    List all receipts or create a new receipt.

    Returns:
        JSON array of receipts (GET) or success message (POST).
    """
    if request.method == 'GET':
        if "limit1" in request.args and "limit2" in request.args:
            return _get_table("Receipts", request.args["limit1"], request.args["limit2"])
        else:
            return _get_all_table("Receipts")
    elif request.method == 'POST':
        return _create_generic(request, "Receipts", "ReceiptID")


# PUBLIC_INTERFACE
@rest_api.route('/receipts/<int:id>/', methods=['GET'])
@rest_api.route('/receipts/<int:id>', methods=['GET', 'PUT', 'DELETE'])
def get_receipt(id):
    """
    Get, update, or delete a specific receipt.

    Args:
        id: Receipt ID (integer).
    """
    if request.method == 'GET':
        return _get_record("Receipts", "ReceiptID", id)
    elif request.method == 'PUT':
        return _update_table(request, 'Receipts', 'ReceiptID', id)
    elif request.method == 'DELETE':
        return _delete_record("Receipts", "ReceiptID", id)


# PUBLIC_INTERFACE
@rest_api.route('/receipts/driver/<int:id>/', methods=['GET'])
@rest_api.route('/receipts/driver/<int:id>', methods=['GET'])
def get_receipt_by_driver(id):
    """
    Get today's receipts for a specific driver.

    Args:
        id: Driver ID (integer).

    Returns:
        JSON array of receipt objects created today.
    """
    try:
        conn = db.connection
        cur = conn.cursor()
        today = datetime.date.today().strftime("%Y-%m-%d")
        cur.execute(
            "SELECT * FROM Receipts WHERE DriverID=? AND DATE(DateCreated)=?",
            (id, today)
        )
        json_data = _rows_to_dicts(cur)
        conn.close()
        return _json_response(json_data)
    except Exception as e:
        return _json_response({"Error": str(e)}, 500)


# ===========================================================================
# ADMIN & DASHBOARD ENDPOINTS
# ===========================================================================

# PUBLIC_INTERFACE
@rest_api.route('/admin', methods=['POST'])
def admin_login():
    """
    Authenticate an admin user.

    Request params:
        Username: Admin username.
        Password: Admin password.

    Returns:
        JSON with login status.
    """
    return _login(request, "Admins")


# PUBLIC_INTERFACE
@rest_api.route('/money', methods=['GET'])
def get_money():
    """
    Get monthly revenue and receipts summary for the current year.

    Returns:
        JSON array with monthly breakdown of revenue and receipts.
    """
    import calendar as cal_mod
    current_date = datetime.date.today()
    current_month = current_date.month + 1
    result = []
    for month in range(1, current_month):
        month_data = {
            "Month": cal_mod.month_name[month],
            "Amount": _month_revenue(month),
            "Receipts": _month_receipts(month)
        }
        result.append(month_data)
    return _json_response(result)


# PUBLIC_INTERFACE
@rest_api.route('/dashboard/stats', methods=['GET'])
def dashboard_stats():
    """
    Get dashboard statistics for the admin panel.

    Returns:
        JSON with counts of jobs, shipments, drivers, and vehicles by status.
    """
    try:
        conn = db.connection
        cur = conn.cursor()

        stats = {}

        # Job stats
        cur.execute("SELECT COUNT(*) FROM Jobs")
        stats['total_jobs'] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM Jobs WHERE Status='Pending'")
        stats['pending_jobs'] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM Jobs WHERE Status='In Transit'")
        stats['in_transit_jobs'] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM Jobs WHERE Status='Delivered'")
        stats['delivered_jobs'] = cur.fetchone()[0]

        # Shipment stats
        cur.execute("SELECT COUNT(*) FROM Shipments")
        stats['total_shipments'] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM Shipments WHERE Status='Pending'")
        stats['pending_shipments'] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM Shipments WHERE Status='In Transit'")
        stats['in_transit_shipments'] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM Shipments WHERE Status='Delivered'")
        stats['delivered_shipments'] = cur.fetchone()[0]

        # Driver and vehicle counts
        cur.execute("SELECT COUNT(*) FROM Drivers")
        stats['total_drivers'] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM Vehicles")
        stats['total_vehicles'] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM Vehicles WHERE Status='Available'")
        stats['available_vehicles'] = cur.fetchone()[0]

        # Route stats
        cur.execute("SELECT COUNT(*) FROM Routes")
        stats['total_routes'] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM Routes WHERE Status='Active'")
        stats['active_routes'] = cur.fetchone()[0]

        conn.close()
        return _json_response(stats)

    except Exception as e:
        logger.error("RestAPIFlow: failed to get dashboard stats: %s", str(e))
        return _json_response({"Error": str(e)}, 500)


# PUBLIC_INTERFACE
@rest_api.route('/receipts/uploads/', methods=['POST'])
@rest_api.route('/receipts/uploads', methods=['POST'])
def upload_file():
    """
    Upload a receipt image file.

    Accepts multipart form data with a 'file' field.

    Returns:
        JSON success/error message.
    """
    if 'file' not in request.files:
        return make_response(jsonify([{"Message": "ERROR - No file present."}]), 400)
    file = request.files['file']
    if file.filename == '':
        return make_response(jsonify([{"Message": "ERROR - No filename"}]), 400)
    if file and _allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return make_response(jsonify([{"Message": "File uploaded successfully."}]), 200)
    return make_response(jsonify([{"Message": "ERROR - File type not allowed."}]), 400)


# 404 Error Handler
@rest_api.route("/<path:invalid_path>")
def missing_resource(invalid_path):
    """Handle 404 errors for unmatched API routes."""
    return make_response(jsonify([{"Error": "Not Found"}]), 404)


# ===========================================================================
# GENERIC DATABASE HELPERS
# ===========================================================================

def _get_all_table(table):
    """Get all records from a table."""
    try:
        conn = db.connection
        cur = conn.cursor()
        cur.execute(f'SELECT * FROM {table}')
        json_data = _rows_to_dicts(cur)
        conn.close()
        return _json_response(json_data)
    except Exception as e:
        logger.error("RestAPIFlow: failed to get all from %s: %s", table, str(e))
        return _json_response({"Error": str(e)}, 500)


def _get_table(table, limit1, limit2):
    """Get paginated records from a table."""
    try:
        conn = db.connection
        cur = conn.cursor()
        cur.execute(
            f'SELECT * FROM {table} LIMIT ? OFFSET ?',
            (int(limit1), int(limit2))
        )
        json_data = _rows_to_dicts(cur)
        conn.close()
        return _json_response(json_data)
    except Exception as e:
        logger.error("RestAPIFlow: failed to get paginated from %s: %s", table, str(e))
        return _json_response({"Error": str(e)}, 500)


def _get_record(table, idname, id):
    """Get a single record by ID."""
    try:
        conn = db.connection
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM {table} WHERE {idname} = ?", (id,))
        json_data = _rows_to_dicts(cur)
        conn.close()
        if not json_data:
            return make_response(jsonify([{"Error": "No matching ID found."}]), 404)
        return _json_response(json_data)
    except Exception as e:
        return _json_response({"Error": str(e)}, 500)


def _delete_record(table, idname, id):
    """Delete a record by ID."""
    try:
        conn = db.connection
        cur = conn.cursor()
        cur.execute(f"DELETE FROM {table} WHERE {idname} = ?", (id,))
        conn.commit()
        conn.close()
        return make_response(jsonify([{"Status": f"Record {id} deleted from {table}"}]))
    except Exception as e:
        return _json_response({"Error": str(e)}, 500)


def _create_job(request):
    """Create a new job with auto-generated tracking ID."""
    data = _get_request_data()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        conn = db.connection
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Jobs (CustomerID, DriverID, PickupID, DropOffID, Status, "
            "ParcelType, ParcelSize, ParcelWeight, PricePaid, DateCreated, DateDue, "
            "EstimatedDistance, Comments) "
            "VALUES (?, ?, ?, ?, 'Pending', ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                data.get('CustomerID'),
                data.get('DriverID'),
                data.get('PickupID'),
                data.get('DropOffID'),
                data.get('ParcelType', ''),
                data.get('ParcelSize', ''),
                data.get('ParcelWeight', ''),
                data.get('PricePaid', 0),
                now,
                data.get('DateDue', ''),
                data.get('EstimatedDistance', ''),
                data.get('Comments', '')
            )
        )
        job_id = cur.lastrowid
        # Generate tracking ID
        tracking_id = f"AQ{datetime.date.today().strftime('%m%y')}{job_id}"
        cur.execute("UPDATE Jobs SET TrackingID=? WHERE JobID=?", (tracking_id, job_id))
        conn.commit()
        conn.close()

        logger.info("RestAPIFlow: created job %d with tracking %s", job_id, tracking_id)
        return _json_response({
            "Success": "Job created successfully",
            "JobID": job_id,
            "TrackingID": tracking_id
        }, 201)

    except Exception as e:
        logger.error("RestAPIFlow: failed to create job: %s", str(e))
        return _json_response({"Error": str(e)}, 500)


def _create_generic(request, table, idname):
    """Create a generic record in any table from request data."""
    data = _get_request_data()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        conn = db.connection
        cur = conn.cursor()

        # Get table columns
        cur.execute(f"PRAGMA table_info({table})")
        columns_info = cur.fetchall()
        columns = [col[1] for col in columns_info if col[1] != idname]

        values = []
        used_columns = []
        for col in columns:
            if col == 'DateCreated':
                used_columns.append(col)
                values.append(now)
            elif col in data and data[col] not in ('None', '', None):
                used_columns.append(col)
                values.append(data[col])

        if not used_columns:
            conn.close()
            return _json_response({"Error": "No valid data provided"}, 400)

        placeholders = ', '.join(['?' for _ in values])
        col_str = ', '.join(used_columns)
        cur.execute(
            f"INSERT INTO {table} ({col_str}) VALUES ({placeholders})",
            values
        )
        conn.commit()
        new_id = cur.lastrowid
        conn.close()

        logger.info("RestAPIFlow: created record in %s with ID %d", table, new_id)
        return _json_response({
            "Success": f"Record added to {table} successfully!",
            f"{idname}": new_id
        }, 201)

    except Exception as e:
        logger.error("RestAPIFlow: failed to create record in %s: %s", table, str(e))
        return _json_response({"Error": str(e)}, 500)


def _update_table(request, table, idname, id):
    """Update a record in any table from request data."""
    data = _get_request_data()

    try:
        conn = db.connection
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM {table} WHERE {idname} = ?", (id,))
        if not cur.fetchone():
            conn.close()
            return make_response(jsonify([{"Error": "No matching ID found."}]), 404)

        # Build SET clause from provided data
        set_parts = []
        values = []
        for key, value in data.items():
            if key != idname:
                set_parts.append(f"{key} = ?")
                values.append(value if value != 'None' else None)

        if not set_parts:
            conn.close()
            return _json_response({"Error": "No update data provided"}, 400)

        values.append(id)
        sql = f"UPDATE {table} SET {', '.join(set_parts)} WHERE {idname} = ?"
        cur.execute(sql, values)
        conn.commit()
        conn.close()

        return make_response(jsonify([{"Success": f"Table {table} edited successfully!"}]))

    except Exception as e:
        logger.error("RestAPIFlow: failed to update %s: %s", table, str(e))
        return _json_response({"Error": str(e)}, 500)


def _login(request, table):
    """Authenticate a user against a table."""
    data = _get_request_data()
    username = data.get('Username', '')
    password = data.get('Password', '')

    try:
        conn = db.connection
        cur = conn.cursor()
        cur.execute(f"SELECT Password FROM {table} WHERE Username=?", (username,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return make_response(jsonify([{
                "Status": "Error",
                "Message": "Login failed: Wrong Username"
            }]), 200)

        if password == row[0]:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute(
                f"UPDATE {table} SET LastConnected = ? WHERE Username=?",
                (now, username)
            )
            conn.commit()
            conn.close()
            return make_response(jsonify([{
                "Status": "Success",
                "Message": "Login Successful",
                "Username": username
            }]), 200)
        else:
            conn.close()
            return make_response(jsonify([{
                "Status": "Error",
                "Message": "Login failed: Wrong Password"
            }]), 200)
    except Exception as e:
        return _json_response({"Error": str(e)}, 500)


def _month_revenue(month):
    """Calculate total revenue for a given month."""
    try:
        conn = db.connection
        cur = conn.cursor()
        cur.execute(
            "SELECT SUM(PricePaid) FROM Jobs WHERE "
            "CAST(strftime('%m', DateDelivered) AS INTEGER) = ?",
            (month,)
        )
        result = cur.fetchone()
        conn.close()
        return result[0] if result and result[0] else None
    except Exception:
        return None


def _month_receipts(month):
    """Calculate total receipts for a given month."""
    try:
        conn = db.connection
        cur = conn.cursor()
        cur.execute(
            "SELECT SUM(Amount) FROM Receipts WHERE "
            "CAST(strftime('%m', DateCreated) AS INTEGER) = ?",
            (month,)
        )
        result = cur.fetchone()
        conn.close()
        return result[0] if result and result[0] else None
    except Exception:
        return None


ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}


def _allowed_file(filename):
    """Check if a filename has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
