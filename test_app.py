"""
Automated Test Suite for FoodCycle Web Application
Tests authentication, RBAC, menu CRUD, sales entry, demand forecasting,
surplus marketplace, donation request workflow, and atomic overbooking protection.
"""

import unittest
from bson import ObjectId
from starlette.testclient import TestClient

from main import app
from database import (
    get_users_collection,
    get_menu_collection,
    get_sales_collection,
    get_listings_collection,
    get_requests_collection,
    get_records_collection,
)
from seed_data import seed_database


class FoodCycleTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n--- [SETUP] Seeding database for clean test run ---")
        seed_database()
        cls.client = TestClient(app, follow_redirects=False)

    def test_01_public_pages(self):
        """Test public pages are served properly."""
        for path in ["/", "/about", "/how-it-works", "/marketplace", "/impact", "/login", "/register"]:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200, f"Failed on path {path}")
            self.assertIn("FoodCycle", res.text)
        print("[PASS] Public pages OK")

    def test_02_rbac_unauthenticated(self):
        """Unauthenticated access to protected pages should redirect to login."""
        res_rest = self.client.get("/restaurant/dashboard")
        self.assertEqual(res_rest.status_code, 303)
        self.assertIn("/login", res_rest.headers["location"])

        res_ngo = self.client.get("/ngo/dashboard")
        self.assertEqual(res_ngo.status_code, 303)
        self.assertIn("/login", res_ngo.headers["location"])
        print("[PASS] RBAC unauthenticated redirection OK")

    def test_03_login_and_role_access(self):
        """Test login with demo credentials and verify role restrictions."""
        # Login as restaurant
        rest_client = TestClient(app, follow_redirects=False)
        login_res = rest_client.post("/login", data={
            "email": "restaurant@foodcycle.org",
            "password": "demo123"
        })
        self.assertEqual(login_res.status_code, 303)
        self.assertEqual(login_res.headers["location"], "/restaurant/dashboard")

        # Restaurant accessing restaurant dashboard -> 200
        dash_res = rest_client.get("/restaurant/dashboard")
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn("The Spice Pavilion", dash_res.text)

        # Restaurant trying to access NGO dashboard -> 403 Forbidden
        ngo_res = rest_client.get("/ngo/dashboard")
        self.assertEqual(ngo_res.status_code, 200)  # Exception handler returns 200 with danger flash alert on home
        self.assertIn("Access forbidden", ngo_res.text)

        # Login as NGO
        ngo_client = TestClient(app, follow_redirects=False)
        login_ngo = ngo_client.post("/login", data={
            "email": "ngo@foodcycle.org",
            "password": "demo123"
        })
        self.assertEqual(login_ngo.status_code, 303)
        self.assertEqual(login_ngo.headers["location"], "/ngo/dashboard")

        # NGO accessing NGO dashboard -> 200
        dash_ngo = ngo_client.get("/ngo/dashboard")
        self.assertEqual(dash_ngo.status_code, 200)
        self.assertIn("Annapurna Food Relief", dash_ngo.text)

        # NGO trying to access Restaurant dashboard -> 403 Forbidden
        rest_attempt = ngo_client.get("/restaurant/dashboard")
        self.assertIn("Access forbidden", rest_attempt.text)
        print("[PASS] Login and RBAC isolation OK")

    def test_04_menu_crud(self):
        """Test adding, listing, toggling, and deleting menu items."""
        rest_client = TestClient(app, follow_redirects=False)
        rest_client.post("/login", data={"email": "restaurant@foodcycle.org", "password": "demo123"})

        # Add new item
        add_res = rest_client.post("/restaurant/menu", data={
            "dish_name": "Test Paneer Tikka Masala",
            "category": "Main Course",
            "price": 310.0,
            "serving_size": "1 bowl (~350g)",
            "is_vegetarian": "true",
            "allergens_raw": "Dairy, Nuts",
        })
        self.assertEqual(add_res.status_code, 303)

        menu_col = get_menu_collection()
        item = menu_col.find_one({"dish_name": "Test Paneer Tikka Masala"})
        self.assertIsNotNone(item)
        self.assertTrue(item["is_active"])

        # Toggle item
        toggle_res = rest_client.post(f"/restaurant/menu/{item['_id']}/toggle")
        self.assertEqual(toggle_res.status_code, 303)
        item_updated = menu_col.find_one({"_id": item["_id"]})
        self.assertFalse(item_updated["is_active"])

        # Delete item
        del_res = rest_client.post(f"/restaurant/menu/{item['_id']}/delete")
        self.assertEqual(del_res.status_code, 303)
        self.assertIsNone(menu_col.find_one({"_id": item["_id"]}))
        print("[PASS] Menu CRUD operations OK")

    def test_05_forecast_generation(self):
        """Test forecasting engine runs RandomForestRegressor with calendar features."""
        rest_client = TestClient(app, follow_redirects=False)
        rest_client.post("/login", data={"email": "restaurant@foodcycle.org", "password": "demo123"})

        # Test forecasting for Diwali festival date in 2026
        res = rest_client.get("/restaurant/forecast?target_date=2026-11-08&safety_margin=10")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Machine Learning Demand Forecasting", res.text)
        self.assertIn("Diwali", res.text)
        self.assertIn("RandomForestRegressor", res.text)
        print("[PASS] Demand Forecast Engine OK")

    def test_06_surplus_and_request_workflow(self):
        """Test full surplus listing -> request -> approve -> pickup -> complete workflow."""
        rest_client = TestClient(app, follow_redirects=False)
        rest_client.post("/login", data={"email": "restaurant@foodcycle.org", "password": "demo123"})

        ngo_client = TestClient(app, follow_redirects=False)
        ngo_client.post("/login", data={"email": "ngo@foodcycle.org", "password": "demo123"})

        # 1. Restaurant creates new surplus listing with 20 portions
        create_res = rest_client.post("/restaurant/surplus", data={
            "dish_name": "Workflow Test Biryani",
            "food_category": "Prepared Rice & Meals",
            "initial_quantity": 20,
            "unit": "servings",
            "preparation_time": "2026-10-10T14:00",
            "expiry_deadline": "2026-10-10T22:00",
            "storage_conditions": "Hot Held (above 63°C)",
            "is_vegetarian": "true",
            "allergens_raw": "Dairy",
            "pickup_address": "42 Indiranagar, Bengaluru",
            "notes": "Packed in food grade thermocol",
        })
        self.assertEqual(create_res.status_code, 303)

        listings_col = get_listings_collection()
        listing = listings_col.find_one({"dish_name": "Workflow Test Biryani"})
        self.assertIsNotNone(listing)
        listing_id = str(listing["_id"])
        self.assertEqual(listing["available_quantity"], 20)

        # 2. NGO requests 12 servings
        req_res = ngo_client.post("/ngo/requests", data={
            "listing_id": listing_id,
            "requested_quantity": 12,
            "pickup_time": "2026-10-10 18:30",
            "notes": "Night shelter distribution",
        })
        self.assertEqual(req_res.status_code, 303)

        requests_col = get_requests_collection()
        req_doc = requests_col.find_one({"listing_id": listing_id, "status": "Requested"})
        self.assertIsNotNone(req_doc)
        req_id = str(req_doc["_id"])
        self.assertEqual(req_doc["requested_quantity"], 12)

        # 3. Restaurant approves request (atomic reservation)
        app_res = rest_client.post(f"/restaurant/requests/{req_id}/approve")
        self.assertEqual(app_res.status_code, 303)

        # Check listing quantity decremented from 20 to 8
        listing_after = listings_col.find_one({"_id": ObjectId(listing_id)})
        self.assertEqual(listing_after["available_quantity"], 8)

        # Check request status is Approved
        req_after = requests_col.find_one({"_id": ObjectId(req_id)})
        self.assertEqual(req_after["status"], "Approved")

        # 4. NGO confirms pickup (food handed over)
        pickup_res = ngo_client.post(f"/ngo/requests/{req_id}/confirm-pickup")
        self.assertEqual(pickup_res.status_code, 303)
        req_collected = requests_col.find_one({"_id": ObjectId(req_id)})
        self.assertEqual(req_collected["status"], "Collected")

        # 5. NGO completes distribution drive and records 12 beneficiaries
        complete_res = ngo_client.post("/ngo/requests/complete", data={
            "request_id": req_id,
            "actual_quantity": 12,
            "beneficiaries_served": 12,
            "notes": "Distributed at Domlur community shelter",
        })
        self.assertEqual(complete_res.status_code, 303)

        req_final = requests_col.find_one({"_id": ObjectId(req_id)})
        self.assertEqual(req_final["status"], "Completed")

        records_col = get_records_collection()
        record = records_col.find_one({"request_id": req_id})
        self.assertIsNotNone(record)
        self.assertEqual(record["beneficiaries_served"], 12)
        print("[PASS] Surplus Redistribution & Completion Workflow OK")

    def test_07_atomic_overbooking_protection(self):
        """Test that approving more than remaining surplus fails cleanly."""
        rest_client = TestClient(app, follow_redirects=False)
        rest_client.post("/login", data={"email": "restaurant@foodcycle.org", "password": "demo123"})

        ngo_client = TestClient(app, follow_redirects=False)
        ngo_client.post("/login", data={"email": "ngo@foodcycle.org", "password": "demo123"})

        # Listing with only 5 portions
        listings_col = get_listings_collection()
        listing_doc = {
            "restaurant_id": "660000000000000000000001",
            "restaurant_name": "The Spice Pavilion",
            "dish_name": "Limited Dessert Portion",
            "food_category": "Dessert",
            "initial_quantity": 5,
            "available_quantity": 5,
            "unit": "servings",
            "preparation_time": "2026-10-10T14:00",
            "expiry_deadline": "2026-10-10T22:00",
            "storage_conditions": "Refrigerated (under 5°C)",
            "is_vegetarian": True,
            "allergens": ["Dairy"],
            "pickup_address": "42 Indiranagar",
            "min_pickup_quantity": 1,
            "is_free": True,
            "status": "Available",
            "created_at": "2026-10-10T14:00:00",
        }
        res_ins = listings_col.insert_one(listing_doc)
        limit_id = str(res_ins.inserted_id)

        # NGO 1 requests 4 portions
        ngo_client.post("/ngo/requests", data={
            "listing_id": limit_id,
            "requested_quantity": 4,
            "pickup_time": "2026-10-10 18:00",
        })

        # NGO 2 requests 4 portions as well
        requests_col = get_requests_collection()
        second_req = {
            "listing_id": limit_id,
            "restaurant_id": "660000000000000000000001",
            "restaurant_name": "The Spice Pavilion",
            "ngo_id": "660000000000000000000004",
            "ngo_name": "Hope Meal Foundation",
            "dish_name": "Limited Dessert Portion",
            "requested_quantity": 4,
            "pickup_time": "2026-10-10 19:00",
            "status": "Requested",
            "created_at": "2026-10-10T15:00:00",
        }
        ins_r2 = requests_col.insert_one(second_req)
        r2_id = str(ins_r2.inserted_id)

        req1 = requests_col.find_one({"listing_id": limit_id, "ngo_id": "660000000000000000000003"})
        r1_id = str(req1["_id"])

        # Approve Request 1 -> succeeds, 5 - 4 = 1 left
        rest_client.post(f"/restaurant/requests/{r1_id}/approve")
        listing_mid = listings_col.find_one({"_id": ObjectId(limit_id)})
        self.assertEqual(listing_mid["available_quantity"], 1)

        # Attempt to approve Request 2 (wants 4, only 1 left) -> should fail cleanly
        app2_res = rest_client.post(f"/restaurant/requests/{r2_id}/approve")
        self.assertIn("Insufficient remaining surplus quantity", app2_res.text)

        # Verify request 2 remains in "Requested" state and available quantity did not go negative
        req2_after = requests_col.find_one({"_id": ObjectId(r2_id)})
        self.assertEqual(req2_after["status"], "Requested")
        listing_final = listings_col.find_one({"_id": ObjectId(limit_id)})
        self.assertEqual(listing_final["available_quantity"], 1)
        print("[PASS] Atomic Overbooking Concurrency Protection OK")


if __name__ == "__main__":
    unittest.main()
