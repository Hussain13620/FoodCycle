"""
Database Configuration and MongoDB Client Setup for FoodCycle
Uses PyMongo with direct local connection to mongodb://localhost:27017/
"""

import sys
from typing import Optional
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# Direct configuration without .env or external config frameworks
# Uses localhost:27017 with directConnection=true for fast local development
MONGO_URI = "mongodb://localhost:27017/?directConnection=true"
DATABASE_NAME = "foodcycle"

_client: Optional[MongoClient] = None
_db: Optional[Database] = None


def get_mongo_client() -> MongoClient:
    """Return a singleton MongoClient instance with fast local directConnection."""
    global _client
    if _client is None:
        try:
            _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
            _client.admin.command("ping")
        except Exception:
            # Fallback to direct IPv4 if localhost DNS lookup delays on Windows
            _client = MongoClient("mongodb://127.0.0.1:27017/?directConnection=true", serverSelectionTimeoutMS=2000)
    return _client


def get_db() -> Database:
    """Get the FoodCycle database instance."""
    global _db
    if _db is None:
        client = get_mongo_client()
        _db = client[DATABASE_NAME]
    return _db


def check_mongo_connection() -> tuple[bool, str]:
    """
    Check if MongoDB is running and reachable.
    Returns (is_connected, message).
    """
    try:
        client = get_mongo_client()
        # Force a network call to verify server is active
        client.admin.command("ping")
        return True, "Connected to MongoDB successfully."
    except (ConnectionFailure, ServerSelectionTimeoutError) as err:
        error_msg = (
            "Cannot connect to MongoDB at mongodb://localhost:27017/.\n"
            "HOW TO START MONGODB:\n"
            "  - Windows: Open PowerShell/Command Prompt as Administrator and run:\n"
            "      net start MongoDB\n"
            "      (or launch 'mongod' from your MongoDB bin directory)\n"
            "  - macOS: brew services start mongodb/brew/mongodb-community\n"
            "  - Linux: sudo systemctl start mongod\n"
            f"Technical error: {err}"
        )
        return False, error_msg


def init_indexes():
    """Create necessary indexes for efficient querying and data integrity."""
    try:
        db = get_db()
        # Users
        db.users.create_index([("email", ASCENDING)], unique=True)
        db.users.create_index([("account_type", ASCENDING)])

        # Menu Items
        db.menu_items.create_index([("restaurant_id", ASCENDING), ("is_active", ASCENDING)])

        # Sales History
        db.sales_history.create_index([("restaurant_id", ASCENDING), ("date", DESCENDING)])
        db.sales_history.create_index([("restaurant_id", ASCENDING), ("dish_id", ASCENDING), ("date", ASCENDING)])

        # Forecasts
        db.demand_forecasts.create_index([("restaurant_id", ASCENDING), ("target_date", DESCENDING)])

        # Surplus Listings
        db.surplus_listings.create_index([("status", ASCENDING), ("expiry_deadline", ASCENDING)])
        db.surplus_listings.create_index([("restaurant_id", ASCENDING)])

        # Donation Requests
        db.donation_requests.create_index([("listing_id", ASCENDING)])
        db.donation_requests.create_index([("ngo_id", ASCENDING), ("status", ASCENDING)])
        db.donation_requests.create_index([("restaurant_id", ASCENDING), ("status", ASCENDING)])

        # Donation Records
        db.donation_records.create_index([("restaurant_id", ASCENDING)])
        db.donation_records.create_index([("ngo_id", ASCENDING)])
        db.donation_records.create_index([("completion_date", DESCENDING)])
    except Exception as e:
        print(f"Warning: Could not initialize MongoDB indexes: {e}")


# Convenient collection accessors
def get_users_collection() -> Collection:
    return get_db().users


def get_menu_collection() -> Collection:
    return get_db().menu_items


def get_sales_collection() -> Collection:
    return get_db().sales_history


def get_forecasts_collection() -> Collection:
    return get_db().demand_forecasts


def get_listings_collection() -> Collection:
    return get_db().surplus_listings


def get_requests_collection() -> Collection:
    return get_db().donation_requests


def get_records_collection() -> Collection:
    return get_db().donation_records
