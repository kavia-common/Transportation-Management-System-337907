"""
Database extension module for the Transportation Management System.

Provides a SQLite-based database adapter that replaces the previous MySQL
dependency, enabling fully local development without external services.

Contract:
  - Inputs: Flask app instance via init_app()
  - Outputs: Database connection via `connection` property
  - Side effects: Creates SQLite database file on disk, initializes schema
  - Errors: sqlite3.Error for DB issues, wrapped with context

Flow name: DatabaseAdapterFlow
Entrypoint: db.init_app(app)
"""

import sqlite3
import os
import logging

logger = logging.getLogger(__name__)


class SQLiteDB:
    """
    SQLite database adapter providing a MySQL-compatible cursor interface.

    This adapter wraps Python's built-in sqlite3 module and provides
    a connection property that returns cursor objects compatible with
    the existing codebase's MySQL cursor usage patterns.
    """

    def __init__(self):
        self._app = None
        self._db_path = None

    # PUBLIC_INTERFACE
    def init_app(self, app):
        """
        Initialize the database adapter with the Flask application.

        Args:
            app: Flask application instance with config containing
                 optional 'SQLITE_DB_PATH' key.

        Side effects:
            - Sets the database path
            - Creates the schema if tables don't exist
            - Registers teardown handler
        """
        self._app = app
        self._db_path = app.config.get(
            'SQLITE_DB_PATH',
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tms.db')
        )
        logger.info("DatabaseAdapterFlow: initialized with db_path=%s", self._db_path)

        # Create schema on startup
        with app.app_context():
            self._create_schema()

    @property
    def connection(self):
        """
        Get a database connection with row_factory set for dict-like access.

        Returns:
            sqlite3.Connection: A connection to the SQLite database.

        Invariant: Connection has row_factory=sqlite3.Row for cursor.description compatibility.
        """
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _create_schema(self):
        """
        Create database tables if they don't already exist.

        This method is idempotent - safe to call multiple times.
        """
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        logger.info("DatabaseAdapterFlow: creating schema if not exists")

        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS Admins (
                AdminID INTEGER PRIMARY KEY AUTOINCREMENT,
                Username TEXT NOT NULL UNIQUE,
                Password TEXT NOT NULL,
                LastConnected TEXT
            );

            CREATE TABLE IF NOT EXISTS Drivers (
                DriverID INTEGER PRIMARY KEY AUTOINCREMENT,
                VehicleID INTEGER,
                Username TEXT UNIQUE,
                Password TEXT DEFAULT 'driver123',
                LastName TEXT,
                FirstName TEXT,
                DOB TEXT,
                NINo TEXT,
                DrivingLicenseNo TEXT,
                DrivingLicensePic TEXT,
                Address1 TEXT,
                Address2 TEXT,
                City TEXT,
                PostCode TEXT,
                Country TEXT,
                Location TEXT,
                DateCreated TEXT,
                LastConnected TEXT
            );

            CREATE TABLE IF NOT EXISTS Vehicles (
                VehicleID INTEGER PRIMARY KEY AUTOINCREMENT,
                Make TEXT,
                Model TEXT,
                Year TEXT,
                Registration TEXT,
                MOTDate TEXT,
                InsuranceDate TEXT,
                Mileage TEXT,
                FuelType TEXT,
                Status TEXT DEFAULT 'Available',
                DateCreated TEXT
            );

            CREATE TABLE IF NOT EXISTS Customers (
                CustomerID INTEGER PRIMARY KEY AUTOINCREMENT,
                FirstName TEXT,
                LastName TEXT,
                Email TEXT,
                Phone TEXT,
                Company TEXT,
                Address1 TEXT,
                Address2 TEXT,
                City TEXT,
                PostCode TEXT,
                Country TEXT,
                DateCreated TEXT
            );

            CREATE TABLE IF NOT EXISTS Locations (
                LocationID INTEGER PRIMARY KEY AUTOINCREMENT,
                Name TEXT,
                Address1 TEXT,
                Address2 TEXT,
                City TEXT,
                PostCode TEXT,
                Country TEXT,
                Latitude TEXT,
                Longitude TEXT,
                DateCreated TEXT
            );

            CREATE TABLE IF NOT EXISTS Jobs (
                JobID INTEGER PRIMARY KEY AUTOINCREMENT,
                TrackingID TEXT,
                CustomerID INTEGER,
                DriverID INTEGER,
                PickupID INTEGER,
                DropOffID INTEGER,
                Status TEXT DEFAULT 'Pending',
                ParcelType TEXT,
                ParcelSize TEXT,
                ParcelWeight TEXT,
                PricePaid REAL,
                DateCreated TEXT,
                DateDue TEXT,
                DateDelivered TEXT,
                DistanceTravelled TEXT,
                EstimatedDistance TEXT,
                Picture1 TEXT,
                Picture2 TEXT,
                Comments TEXT,
                FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID),
                FOREIGN KEY (DriverID) REFERENCES Drivers(DriverID),
                FOREIGN KEY (PickupID) REFERENCES Locations(LocationID),
                FOREIGN KEY (DropOffID) REFERENCES Locations(LocationID)
            );

            CREATE TABLE IF NOT EXISTS Receipts (
                ReceiptID INTEGER PRIMARY KEY AUTOINCREMENT,
                DriverID INTEGER,
                JobID INTEGER,
                Amount REAL,
                Description TEXT,
                Picture TEXT,
                DateCreated TEXT,
                FOREIGN KEY (DriverID) REFERENCES Drivers(DriverID),
                FOREIGN KEY (JobID) REFERENCES Jobs(JobID)
            );

            CREATE TABLE IF NOT EXISTS Shipments (
                ShipmentID INTEGER PRIMARY KEY AUTOINCREMENT,
                TrackingNumber TEXT UNIQUE,
                SenderName TEXT,
                SenderAddress TEXT,
                SenderCity TEXT,
                SenderPostCode TEXT,
                ReceiverName TEXT,
                ReceiverAddress TEXT,
                ReceiverCity TEXT,
                ReceiverPostCode TEXT,
                Weight REAL,
                Description TEXT,
                Status TEXT DEFAULT 'Pending',
                DriverID INTEGER,
                VehicleID INTEGER,
                EstimatedDelivery TEXT,
                ActualDelivery TEXT,
                CreatedAt TEXT,
                UpdatedAt TEXT,
                FOREIGN KEY (DriverID) REFERENCES Drivers(DriverID),
                FOREIGN KEY (VehicleID) REFERENCES Vehicles(VehicleID)
            );

            CREATE TABLE IF NOT EXISTS Routes (
                RouteID INTEGER PRIMARY KEY AUTOINCREMENT,
                DriverID INTEGER,
                VehicleID INTEGER,
                RouteName TEXT,
                StartLocation TEXT,
                EndLocation TEXT,
                EstimatedDistance REAL,
                EstimatedDuration TEXT,
                Status TEXT DEFAULT 'Planned',
                PlannedDate TEXT,
                CreatedAt TEXT,
                FOREIGN KEY (DriverID) REFERENCES Drivers(DriverID),
                FOREIGN KEY (VehicleID) REFERENCES Vehicles(VehicleID)
            );

            CREATE TABLE IF NOT EXISTS RouteStops (
                StopID INTEGER PRIMARY KEY AUTOINCREMENT,
                RouteID INTEGER,
                ShipmentID INTEGER,
                StopOrder INTEGER,
                Address TEXT,
                City TEXT,
                PostCode TEXT,
                StopType TEXT DEFAULT 'Delivery',
                Status TEXT DEFAULT 'Pending',
                FOREIGN KEY (RouteID) REFERENCES Routes(RouteID),
                FOREIGN KEY (ShipmentID) REFERENCES Shipments(ShipmentID)
            );
        """)

        conn.commit()
        conn.close()
        logger.info("DatabaseAdapterFlow: schema creation complete")


# Singleton instance used across the application
db = SQLiteDB()
