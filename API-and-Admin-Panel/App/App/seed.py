"""
Seed data module for the Transportation Management System.

Populates the SQLite database with sample data for demonstration purposes.
Includes admins, drivers, vehicles, customers, locations, jobs, shipments,
routes, and receipts.

Flow name: SeedDataFlow
Entrypoint: seed_database(db)
Contract:
  - Input: SQLiteDB instance (from extensions.py)
  - Output: None (side-effect: database populated)
  - Errors: sqlite3.Error on database issues
  - Side effects: Inserts rows into all tables if they are empty
"""

import logging
import datetime
import uuid

logger = logging.getLogger(__name__)


def _generate_tracking_number():
    """Generate a unique tracking number with prefix TMS."""
    now = datetime.datetime.now()
    return f"TMS{now.strftime('%m%y')}{uuid.uuid4().hex[:6].upper()}"


# PUBLIC_INTERFACE
def seed_database(db):
    """
    Populate the database with sample data if tables are empty.

    This function is idempotent - it only inserts data when
    the respective tables are empty.

    Args:
        db: SQLiteDB instance from extensions module.

    Side effects:
        Inserts sample rows into Admins, Drivers, Vehicles,
        Customers, Locations, Jobs, Shipments, Routes, RouteStops,
        and Receipts tables.
    """
    conn = db.connection
    cursor = conn.cursor()

    logger.info("SeedDataFlow: starting seed data check")

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    two_days_ago = (datetime.datetime.now() - datetime.timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
    tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    next_week = (datetime.datetime.now() + datetime.timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")

    try:
        # Seed Admins
        cursor.execute("SELECT COUNT(*) FROM Admins")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO Admins (Username, Password, LastConnected) VALUES (?, ?, ?)",
                [
                    ("admin", "admin123", now),
                    ("manager", "manager123", yesterday),
                ]
            )
            logger.info("SeedDataFlow: seeded Admins table")

        # Seed Vehicles
        cursor.execute("SELECT COUNT(*) FROM Vehicles")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO Vehicles (Make, Model, Year, Registration, MOTDate, InsuranceDate, Mileage, FuelType, Status, DateCreated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    ("Ford", "Transit", "2022", "AB12 CDE", "2025-06-15", "2025-08-20", "45000", "Diesel", "Available", two_days_ago),
                    ("Mercedes", "Sprinter", "2021", "FG34 HIJ", "2025-04-10", "2025-07-15", "62000", "Diesel", "Available", two_days_ago),
                    ("Volkswagen", "Crafter", "2023", "KL56 MNO", "2025-09-01", "2025-11-30", "28000", "Diesel", "Available", two_days_ago),
                    ("Peugeot", "Boxer", "2020", "PQ78 RST", "2025-03-20", "2025-05-10", "78000", "Diesel", "In Maintenance", two_days_ago),
                ]
            )
            logger.info("SeedDataFlow: seeded Vehicles table")

        # Seed Drivers
        cursor.execute("SELECT COUNT(*) FROM Drivers")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO Drivers (VehicleID, Username, Password, LastName, FirstName, DOB, NINo, DrivingLicenseNo, Address1, City, PostCode, Country, Location, DateCreated, LastConnected) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (1, "stevenjones", "driver123", "Jones", "Steven", "1990-05-15", "AB123456C", "JONES905150AB1CD", "10 High Street", "London", "EC1A 1BB", "UK", "51.5074,-0.1278", two_days_ago, now),
                    (2, "duncansmith", "driver123", "Smith", "Duncan", "1985-08-22", "CD789012E", "SMITH858220CD2EF", "25 Park Lane", "Manchester", "M1 1AA", "UK", "53.4808,-2.2426", two_days_ago, yesterday),
                    (3, "georgewilson", "driver123", "Wilson", "George", "1992-11-03", "EF345678G", "WILSO921103EF3GH", "42 Queen Road", "Birmingham", "B1 1AA", "UK", "52.4862,-1.8904", two_days_ago, yesterday),
                ]
            )
            logger.info("SeedDataFlow: seeded Drivers table")

        # Seed Customers
        cursor.execute("SELECT COUNT(*) FROM Customers")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO Customers (FirstName, LastName, Email, Phone, Company, Address1, City, PostCode, Country, DateCreated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    ("John", "Doe", "john.doe@example.com", "07700900001", "Doe Industries", "1 Business Park", "London", "SW1A 1AA", "UK", two_days_ago),
                    ("Jane", "Smith", "jane.smith@example.com", "07700900002", "Smith & Co", "15 Commerce Street", "Manchester", "M2 2BB", "UK", two_days_ago),
                    ("Robert", "Brown", "robert.brown@example.com", "07700900003", "Brown Logistics", "8 Warehouse Lane", "Birmingham", "B2 2CC", "UK", two_days_ago),
                    ("Emily", "Davis", "emily.davis@example.com", "07700900004", "Davis Express", "22 Delivery Road", "Leeds", "LS1 1DD", "UK", two_days_ago),
                    ("Michael", "Taylor", "michael.taylor@example.com", "07700900005", "Taylor Shipping", "5 Dock Street", "Liverpool", "L1 1EE", "UK", two_days_ago),
                ]
            )
            logger.info("SeedDataFlow: seeded Customers table")

        # Seed Locations
        cursor.execute("SELECT COUNT(*) FROM Locations")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO Locations (Name, Address1, City, PostCode, Country, Latitude, Longitude, DateCreated) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    ("London Warehouse", "100 Warehouse Rd", "London", "E1 6AN", "UK", "51.5155", "-0.0722", two_days_ago),
                    ("Manchester Depot", "50 Depot Lane", "Manchester", "M1 3BB", "UK", "53.4808", "-2.2426", two_days_ago),
                    ("Birmingham Hub", "75 Hub Street", "Birmingham", "B4 7ET", "UK", "52.4862", "-1.8904", two_days_ago),
                    ("Leeds Distribution", "30 Distribution Ave", "Leeds", "LS2 7HY", "UK", "53.8008", "-1.5491", two_days_ago),
                    ("Liverpool Port", "12 Port Road", "Liverpool", "L3 4FP", "UK", "53.4084", "-2.9916", two_days_ago),
                    ("Edinburgh Centre", "88 Royal Mile", "Edinburgh", "EH1 1RE", "UK", "55.9533", "-3.1883", two_days_ago),
                ]
            )
            logger.info("SeedDataFlow: seeded Locations table")

        # Seed Jobs
        cursor.execute("SELECT COUNT(*) FROM Jobs")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO Jobs (TrackingID, CustomerID, DriverID, PickupID, DropOffID, Status, ParcelType, ParcelSize, ParcelWeight, PricePaid, DateCreated, DateDue, DateDelivered, EstimatedDistance, Comments) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    ("AQ0325001", 1, 1, 1, 2, "Delivered", "Package", "Medium", "5.2", 45.00, two_days_ago, yesterday, yesterday, "200 miles", "Delivered on time"),
                    ("AQ0325002", 2, 1, 1, 3, "Delivered", "Document", "Small", "0.5", 15.00, two_days_ago, yesterday, yesterday, "120 miles", "Signed for"),
                    ("AQ0325003", 3, 2, 2, 4, "In Transit", "Package", "Large", "12.0", 75.00, yesterday, tomorrow, None, "95 miles", "Fragile - handle with care"),
                    ("AQ0325004", 4, 2, 3, 5, "Pending", "Pallet", "Extra Large", "50.0", 150.00, yesterday, next_week, None, "180 miles", "Industrial equipment"),
                    ("AQ0325005", 5, 3, 1, 6, "Pending", "Package", "Medium", "8.0", 55.00, now, next_week, None, "400 miles", "Express delivery requested"),
                    ("AQ0325006", 1, None, 2, 1, "Pending", "Document", "Small", "0.3", 12.00, now, tomorrow, None, "200 miles", "Return shipment"),
                    ("AQ0325007", 3, 3, 4, 2, "In Transit", "Package", "Medium", "3.5", 35.00, yesterday, tomorrow, None, "95 miles", "Standard delivery"),
                ]
            )
            logger.info("SeedDataFlow: seeded Jobs table")

        # Seed Shipments
        cursor.execute("SELECT COUNT(*) FROM Shipments")
        if cursor.fetchone()[0] == 0:
            shipments = [
                (_generate_tracking_number(), "John Doe", "1 Business Park", "London", "SW1A 1AA",
                 "Jane Smith", "15 Commerce Street", "Manchester", "M2 2BB",
                 5.2, "Electronics package", "Delivered", 1, 1, yesterday, yesterday, two_days_ago, yesterday),
                (_generate_tracking_number(), "Robert Brown", "8 Warehouse Lane", "Birmingham", "B2 2CC",
                 "Emily Davis", "22 Delivery Road", "Leeds", "LS1 1DD",
                 12.0, "Furniture parts", "In Transit", 2, 2, tomorrow, None, yesterday, now),
                (_generate_tracking_number(), "Michael Taylor", "5 Dock Street", "Liverpool", "L1 1EE",
                 "John Doe", "1 Business Park", "London", "SW1A 1AA",
                 3.5, "Documents bundle", "Pending", None, None, next_week, None, now, now),
                (_generate_tracking_number(), "Jane Smith", "15 Commerce Street", "Manchester", "M2 2BB",
                 "Robert Brown", "8 Warehouse Lane", "Birmingham", "B2 2CC",
                 8.0, "Machine parts", "Pending", None, None, next_week, None, now, now),
                (_generate_tracking_number(), "Emily Davis", "22 Delivery Road", "Leeds", "LS1 1DD",
                 "Michael Taylor", "5 Dock Street", "Liverpool", "L1 1EE",
                 1.5, "Medical supplies", "In Transit", 3, 3, tomorrow, None, yesterday, now),
            ]
            cursor.executemany(
                "INSERT INTO Shipments (TrackingNumber, SenderName, SenderAddress, SenderCity, SenderPostCode, ReceiverName, ReceiverAddress, ReceiverCity, ReceiverPostCode, Weight, Description, Status, DriverID, VehicleID, EstimatedDelivery, ActualDelivery, CreatedAt, UpdatedAt) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                shipments
            )
            logger.info("SeedDataFlow: seeded Shipments table")

        # Seed Routes
        cursor.execute("SELECT COUNT(*) FROM Routes")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO Routes (DriverID, VehicleID, RouteName, StartLocation, EndLocation, EstimatedDistance, EstimatedDuration, Status, PlannedDate, CreatedAt) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (1, 1, "London to Manchester Express", "London", "Manchester", 200.0, "3h 30m", "Completed", yesterday, two_days_ago),
                    (2, 2, "Manchester to Leeds Run", "Manchester", "Leeds", 45.0, "1h 15m", "Active", now, yesterday),
                    (3, 3, "Leeds to Liverpool Circuit", "Leeds", "Liverpool", 75.0, "1h 45m", "Active", now, yesterday),
                    (1, 1, "London to Edinburgh Long Haul", "London", "Edinburgh", 400.0, "7h 00m", "Planned", next_week, now),
                ]
            )
            logger.info("SeedDataFlow: seeded Routes table")

        # Seed RouteStops
        cursor.execute("SELECT COUNT(*) FROM RouteStops")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO RouteStops (RouteID, ShipmentID, StopOrder, Address, City, PostCode, StopType, Status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (1, 1, 1, "15 Commerce Street", "Manchester", "M2 2BB", "Delivery", "Completed"),
                    (2, 2, 1, "22 Delivery Road", "Leeds", "LS1 1DD", "Delivery", "Pending"),
                    (3, 5, 1, "5 Dock Street", "Liverpool", "L1 1EE", "Delivery", "Pending"),
                ]
            )
            logger.info("SeedDataFlow: seeded RouteStops table")

        # Seed Receipts
        cursor.execute("SELECT COUNT(*) FROM Receipts")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO Receipts (DriverID, JobID, Amount, Description, DateCreated) VALUES (?, ?, ?, ?, ?)",
                [
                    (1, 1, 25.50, "Fuel - London to Manchester", yesterday),
                    (1, 2, 8.00, "Lunch", yesterday),
                    (2, 3, 18.75, "Fuel - Manchester to Leeds", now),
                    (3, 7, 30.00, "Fuel - Leeds to Liverpool", now),
                ]
            )
            logger.info("SeedDataFlow: seeded Receipts table")

        conn.commit()
        logger.info("SeedDataFlow: seed data check complete")

    except Exception as e:
        conn.rollback()
        logger.error("SeedDataFlow: failed to seed database: %s", str(e))
        raise
    finally:
        conn.close()
