# Transportation Management System

A full-suite transportation management system for delivery companies, including a Flask-based web server (API + Admin Panel + Customer website) backed by SQLite (for local development) and an Android driver app.

## Quick Start (Local Development)

### Prerequisites
- Python 3.8+

### Setup & Run

```bash
cd API-and-Admin-Panel/App/App

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python App.py
```

The application will:
1. Create a SQLite database (`tms.db`) automatically
2. Seed it with demo data (admins, drivers, vehicles, customers, jobs, shipments, routes)
3. Start the server on http://localhost:3001

### Access Points
| URL | Description |
|-----|-------------|
| http://localhost:3001/ | Customer Website (redirects to /home) |
| http://localhost:3001/home | Customer Landing Page with Tracking |
| http://localhost:3001/admin | Admin Panel Login |
| http://localhost:3001/api/ | REST API Root |
| http://localhost:3001/api-docs | API Documentation |
| http://localhost:3001/healthz | Health Check |

### Demo Credentials
- **Admin Panel:** `admin` / `admin123`
- **Driver Login (API):** `stevenjones` / `driver123`

---

## Architecture

### Components
1. **Customer Website** (`/home`) - Public landing page with parcel tracking
2. **Admin Panel** (`/admin`) - Dashboard for managing jobs, shipments, drivers, vehicles, routes
3. **REST API** (`/api`) - RESTful endpoints for all CRUD operations
4. **Android App** - Driver mobile app (separate project)

### Database (SQLite)
Tables: `Admins`, `Drivers`, `Vehicles`, `Customers`, `Locations`, `Jobs`, `Shipments`, `Routes`, `RouteStops`, `Receipts`

### Key Features
- **Shipment Creation & Tracking**: Create shipments with auto-generated tracking numbers, track via tracking ID
- **Status Transitions**: Validated flow: `Pending → In Transit → Delivered`
- **Driver/Vehicle Assignment**: Assign drivers and vehicles to shipments
- **Route Planning**: Create routes with multiple stops linked to shipments
- **Dashboard**: Real-time statistics on jobs, shipments, drivers, and routes

---

## API Documentation

### Endpoints Summary

#### Health & Docs
- `GET /healthz` - Health check
- `GET /api-docs` - Full API documentation

#### Jobs (Legacy)
- `GET /api/jobs` - List all jobs
- `POST /api/jobs` - Create a new job
- `GET /api/jobs/<id>` - Get job details
- `PUT /api/jobs/<id>` - Update job
- `DELETE /api/jobs/<id>` - Delete job
- `PUT /api/jobs/<id>/status` - Update job status (validated transitions)
- `GET /api/jobs/pending` - List pending jobs
- `GET /api/jobs/in-transit` - List in-transit jobs
- `GET /api/jobs/delivered` - List delivered jobs
- `GET /api/jobs/<trackingId>/location` - Track parcel location
- `GET /api/jobs/full/<id>` - Full job with customer and locations

#### Shipments
- `GET /api/shipments` - List all shipments
- `POST /api/shipments` - Create a new shipment
- `GET /api/shipments/<id>` - Get shipment details
- `PUT /api/shipments/<id>/status` - Update shipment status
- `PUT /api/shipments/<id>/assign` - Assign driver/vehicle
- `GET /api/shipments/track/<tracking_number>` - Track by tracking number

#### Routes
- `GET /api/routes` - List all routes
- `POST /api/routes` - Create route with stops
- `GET /api/routes/<id>` - Get route with stops
- `PUT /api/routes/<id>/status` - Update route status

#### Drivers, Vehicles, Customers, Locations, Receipts
Standard CRUD: `GET /api/<resource>`, `POST`, `GET /<id>`, `PUT /<id>`, `DELETE /<id>`

---

## Demo Flow (Step-by-Step Video Recording)

### 1. Health Check
Navigate to `http://localhost:3001/healthz` → Shows system is running.

### 2. API Documentation
Navigate to `http://localhost:3001/api-docs` → Shows all available endpoints.

### 3. Customer Website
Navigate to `http://localhost:3001/home`:
- Browse the landing page
- Track a parcel using `AQ0325003` (In Transit) or `AQ0325001` (Delivered)
- Try shipment tracking with any TMS-prefixed tracking number from the seed data

### 4. Admin Panel
Navigate to `http://localhost:3001/admin`:
- Login with `admin` / `admin123`
- View the dashboard with real-time statistics
- Click **Shipments** → View all shipments with status badges
- Click **Jobs** → Filter by Pending/In Transit/Delivered
- Click **Routes** → View planned delivery routes
- Click **Drivers** → View driver details and assignments
- Click **Vehicles** → View fleet status
- Create a new record in any table
- Update a record's status

### 5. Status Transition Demo
Using the API (e.g., with curl):
```bash
# Move job from Pending to In Transit
curl -X PUT "http://localhost:3001/api/jobs/4/status?Status=In%20Transit"

# Move job from In Transit to Delivered
curl -X PUT "http://localhost:3001/api/jobs/3/status?Status=Delivered"

# Assign driver to shipment
curl -X PUT "http://localhost:3001/api/shipments/3/assign?DriverID=1&VehicleID=1"

# Create a new shipment
curl -X POST "http://localhost:3001/api/shipments" \
  -H "Content-Type: application/json" \
  -d '{"SenderName":"Test","SenderCity":"London","ReceiverName":"Demo","ReceiverCity":"Manchester","Weight":5.0,"Description":"Demo package"}'
```

---

## Production Readiness Suggestions
1. **Authentication**: Replace plaintext passwords with hashed passwords (bcrypt)
2. **Database**: Migrate from SQLite to PostgreSQL or MySQL for concurrent access
3. **HTTPS**: Enable TLS/SSL for all endpoints
4. **Rate Limiting**: Add API rate limiting to prevent abuse
5. **Input Validation**: Add comprehensive input validation and sanitization
6. **Logging**: Add structured logging with log aggregation
7. **Monitoring**: Add Prometheus metrics and health check probes
8. **CORS**: Configure CORS properly for production domains
9. **Session Management**: Use Redis or database-backed sessions
10. **Testing**: Add comprehensive unit and integration tests
