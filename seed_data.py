"""
Sample Data Seeding Script for FoodCycle
Seeds 2 Restaurants, 2 NGOs, Menu Items, 90 Days of Historical Sales Data,
Surplus Listings, Donation Requests, and Completed Donation Impact Records.
All sample records are transparently marked as illustrative demonstration data.
"""

import sys
from datetime import datetime, date, timedelta
from bson import ObjectId
import random

from database import (
    get_db,
    check_mongo_connection,
    init_indexes,
    get_users_collection,
    get_menu_collection,
    get_sales_collection,
    get_listings_collection,
    get_requests_collection,
    get_records_collection,
    get_forecasts_collection,
)
from auth import hash_password
from prediction import KNOWN_FESTIVALS


def seed_database():
    is_connected, msg = check_mongo_connection()
    if not is_connected:
        print("ERROR: MongoDB is not running or unreachable!")
        print(msg)
        sys.exit(1)

    print("Initializing indexes...")
    init_indexes()

    users_col = get_users_collection()
    menu_col = get_menu_collection()
    sales_col = get_sales_collection()
    listings_col = get_listings_collection()
    requests_col = get_requests_collection()
    records_col = get_records_collection()
    forecasts_col = get_forecasts_collection()

    print("Clearing previous sample data...")
    users_col.delete_many({})
    menu_col.delete_many({})
    sales_col.delete_many({})
    listings_col.delete_many({})
    requests_col.delete_many({})
    records_col.delete_many({})
    forecasts_col.delete_many({})

    # 1. Create Demo Users
    hashed_pwd = hash_password("demo123")
    now_iso = datetime.now().isoformat()

    restaurant_1 = {
        "_id": ObjectId("660000000000000000000001"),
        "email": "restaurant@foodcycle.org",
        "password_hash": hashed_pwd,
        "org_name": "The Spice Pavilion",
        "account_type": "restaurant",
        "contact_phone": "+91 98450 12345",
        "address": "42, Indiranagar 100ft Road, HAL 2nd Stage",
        "city": "Bengaluru",
        "pincode": "560038",
        "cuisine_type": "North & South Indian Traditional",
        "operating_hours": "11:30 AM - 11:00 PM",
        "safety_margin_pct": 10.0,
        "created_at": now_iso,
        "is_sample_data": True,
    }

    restaurant_2 = {
        "_id": ObjectId("660000000000000000000002"),
        "email": "bistro@foodcycle.org",
        "password_hash": hashed_pwd,
        "org_name": "Green Leaf Bistro",
        "account_type": "restaurant",
        "contact_phone": "+91 98765 43210",
        "address": "15, 80ft Road, 4th Block, Koramangala",
        "city": "Bengaluru",
        "pincode": "560034",
        "cuisine_type": "Healthy Bowls, Mediterranean & Fusion",
        "operating_hours": "10:00 AM - 10:30 PM",
        "safety_margin_pct": 8.0,
        "created_at": now_iso,
        "is_sample_data": True,
    }

    ngo_1 = {
        "_id": ObjectId("660000000000000000000003"),
        "email": "ngo@foodcycle.org",
        "password_hash": hashed_pwd,
        "org_name": "Annapurna Food Relief",
        "account_type": "ngo",
        "contact_phone": "+91 98111 22334",
        "address": "108, 1st Cross, Domlur Layout",
        "city": "Bengaluru",
        "pincode": "560071",
        "beneficiaries_served_daily": 120,
        "dietary_preferences": "Both Vegetarian and Non-Vegetarian",
        "feeding_drive_details": "Night shelters, construction worker camps, and eldercare homes",
        "created_at": now_iso,
        "is_sample_data": True,
    }

    ngo_2 = {
        "_id": ObjectId("660000000000000000000004"),
        "email": "hope@foodcycle.org",
        "password_hash": hashed_pwd,
        "org_name": "Hope Meal Foundation",
        "account_type": "ngo",
        "contact_phone": "+91 97222 33445",
        "address": "88, Bannerghatta Main Road, Jayanagar 9th Block",
        "city": "Bengaluru",
        "pincode": "560069",
        "beneficiaries_served_daily": 80,
        "dietary_preferences": "Pure Vegetarian preferred",
        "feeding_drive_details": "Underprivileged children education centers and daily wage worker colonies",
        "created_at": now_iso,
        "is_sample_data": True,
    }

    users_col.insert_many([restaurant_1, restaurant_2, ngo_1, ngo_2])
    print("Demo accounts created:")
    print("  Restaurant 1: restaurant@foodcycle.org / demo123 (The Spice Pavilion)")
    print("  Restaurant 2: bistro@foodcycle.org / demo123 (Green Leaf Bistro)")
    print("  NGO 1:        ngo@foodcycle.org / demo123 (Annapurna Food Relief)")
    print("  NGO 2:        hope@foodcycle.org / demo123 (Hope Meal Foundation)")

    # 2. Menu Items for Restaurant 1 (The Spice Pavilion)
    menu_items_r1 = [
        {
            "_id": ObjectId("661000000000000000000001"),
            "restaurant_id": str(restaurant_1["_id"]),
            "dish_name": "Dum Biryani (Vegetable / Paneer)",
            "category": "Rice & Biryani",
            "price": 280.0,
            "serving_size": "1 portion (~450g)",
            "is_vegetarian": True,
            "allergens": ["Dairy", "Nuts"],
            "is_active": True,
            "created_at": now_iso,
            "base_demand": 45,
            "weekend_boost": 1.45,
            "festive_boost": 1.60,
        },
        {
            "_id": ObjectId("661000000000000000000002"),
            "restaurant_id": str(restaurant_1["_id"]),
            "dish_name": "Hyderabadi Chicken Biryani",
            "category": "Rice & Biryani",
            "price": 340.0,
            "serving_size": "1 portion (~500g)",
            "is_vegetarian": False,
            "allergens": ["Dairy"],
            "is_active": True,
            "created_at": now_iso,
            "base_demand": 60,
            "weekend_boost": 1.50,
            "festive_boost": 1.55,
        },
        {
            "_id": ObjectId("661000000000000000000003"),
            "restaurant_id": str(restaurant_1["_id"]),
            "dish_name": "Dal Makhani & Jeera Rice Meal",
            "category": "Main Course",
            "price": 240.0,
            "serving_size": "1 meal box (~400g)",
            "is_vegetarian": True,
            "allergens": ["Dairy"],
            "is_active": True,
            "created_at": now_iso,
            "base_demand": 38,
            "weekend_boost": 1.25,
            "festive_boost": 1.35,
        },
        {
            "_id": ObjectId("661000000000000000000004"),
            "restaurant_id": str(restaurant_1["_id"]),
            "dish_name": "Paneer Butter Masala",
            "category": "Main Course",
            "price": 290.0,
            "serving_size": "1 bowl (~350g)",
            "is_vegetarian": True,
            "allergens": ["Dairy", "Nuts"],
            "is_active": True,
            "created_at": now_iso,
            "base_demand": 42,
            "weekend_boost": 1.40,
            "festive_boost": 1.50,
        },
        {
            "_id": ObjectId("661000000000000000000005"),
            "restaurant_id": str(restaurant_1["_id"]),
            "dish_name": "Tandoori Roti & Naan Basket",
            "category": "Breads",
            "price": 120.0,
            "serving_size": "Basket of 4 pieces",
            "is_vegetarian": True,
            "allergens": ["Gluten"],
            "is_active": True,
            "created_at": now_iso,
            "base_demand": 75,
            "weekend_boost": 1.40,
            "festive_boost": 1.50,
        },
        {
            "_id": ObjectId("661000000000000000000006"),
            "restaurant_id": str(restaurant_1["_id"]),
            "dish_name": "Gulab Jamun (Pack of 4)",
            "category": "Dessert",
            "price": 110.0,
            "serving_size": "4 pieces",
            "is_vegetarian": True,
            "allergens": ["Dairy", "Gluten"],
            "is_active": True,
            "created_at": now_iso,
            "base_demand": 30,
            "weekend_boost": 1.35,
            "festive_boost": 2.20,  # Sweets soar on festivals
        },
    ]

    # Menu Items for Restaurant 2 (Green Leaf Bistro)
    menu_items_r2 = [
        {
            "_id": ObjectId("661000000000000000000007"),
            "restaurant_id": str(restaurant_2["_id"]),
            "dish_name": "Mediterranean Quinoa Falafel Bowl",
            "category": "Healthy Bowls",
            "price": 320.0,
            "serving_size": "1 bowl (~380g)",
            "is_vegetarian": True,
            "allergens": ["Sesame"],
            "is_active": True,
            "created_at": now_iso,
            "base_demand": 28,
            "weekend_boost": 1.30,
            "festive_boost": 1.15,
        },
        {
            "_id": ObjectId("661000000000000000000008"),
            "restaurant_id": str(restaurant_2["_id"]),
            "dish_name": "Tuscan Grilled Vegetable Penne",
            "category": "Pasta & Mains",
            "price": 310.0,
            "serving_size": "1 portion (~350g)",
            "is_vegetarian": True,
            "allergens": ["Gluten", "Dairy"],
            "is_active": True,
            "created_at": now_iso,
            "base_demand": 25,
            "weekend_boost": 1.35,
            "festive_boost": 1.20,
        },
    ]

    all_menu_items = menu_items_r1 + menu_items_r2
    for item in all_menu_items:
        # copy dict without helper simulation keys
        doc = {k: v for k, v in item.items() if k not in ("base_demand", "weekend_boost", "festive_boost")}
        menu_col.insert_one(doc)
    print(f"Created {len(all_menu_items)} menu items.")

    # 3. 90 Days of Historical Daily Sales for Restaurant 1
    # Reflects real-world trends: higher on weekends (Fri-Sun), festival boosts (Diwali/Dussehra/Eid),
    # and realistic production leftovers (5-15% surplus before FoodCycle)
    print("Generating 90 days of illustrative daily sales history...")
    today = date.today()
    sales_docs = []
    random.seed(42)

    for days_back in range(90, 0, -1):
        curr_date = today - timedelta(days=days_back)
        curr_str = curr_date.strftime("%Y-%m-%d")
        dow = curr_date.weekday()
        is_weekend = dow in (4, 5, 6)
        festival = KNOWN_FESTIVALS.get(curr_str)

        for item in menu_items_r1:
            base = item["base_demand"]
            mult = 1.0

            if is_weekend:
                mult *= item["weekend_boost"]

            if festival:
                mult *= item["festive_boost"]

            # Add random realistic daily variance (+/- 10%)
            daily_noise = random.uniform(0.92, 1.08)
            qty_sold = int(round(base * mult * daily_noise))

            # Restaurant prep was typically 10-20% higher than sold
            overprep_rate = random.uniform(1.08, 1.22)
            qty_produced = int(round(qty_sold * overprep_rate))
            leftover = max(0, qty_produced - qty_sold)

            special_event = None
            if festival:
                special_event = festival
            elif dow == 5 and random.random() < 0.2:
                special_event = "Live Music Weekend"

            sales_docs.append({
                "restaurant_id": str(restaurant_1["_id"]),
                "dish_id": str(item["_id"]),
                "dish_name": item["dish_name"],
                "date": curr_str,
                "day_of_week": dow,
                "is_weekend": 1 if is_weekend else 0,
                "quantity_sold": qty_sold,
                "quantity_produced": qty_produced,
                "leftover_quantity": leftover,
                "special_event": special_event,
                "is_sample_data": True,
            })

    sales_col.insert_many(sales_docs)
    print(f"Seeded {len(sales_docs)} sales history records for machine learning model training.")

    # 4. Active Surplus Listings
    # Prepared today, expiring this evening/night, available for claiming
    expiry_1 = (datetime.now() + timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M")
    prep_1 = (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")

    expiry_2 = (datetime.now() + timedelta(hours=7)).strftime("%Y-%m-%dT%H:%M")
    prep_2 = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")

    expiry_3 = (datetime.now() + timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M")
    prep_3 = (datetime.now() - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M")

    listing_1 = {
        "_id": ObjectId("662000000000000000000001"),
        "restaurant_id": str(restaurant_1["_id"]),
        "restaurant_name": restaurant_1["org_name"],
        "restaurant_address": restaurant_1["address"],
        "restaurant_phone": restaurant_1["contact_phone"],
        "dish_name": "Dum Biryani (Vegetable / Paneer)",
        "food_category": "Prepared Rice & Meals",
        "initial_quantity": 40,
        "available_quantity": 15,  # 25 servings already requested/approved by NGO
        "unit": "servings",
        "preparation_time": prep_1,
        "expiry_deadline": expiry_1,
        "storage_conditions": "Hot Held (above 63°C)",
        "is_vegetarian": True,
        "allergens": ["Dairy", "Nuts"],
        "pickup_address": restaurant_1["address"],
        "min_pickup_quantity": 5,
        "is_free": True,
        "price_per_unit": 0.0,
        "notes": "Packed in food-grade thermocol catering containers. Temperature checked at 68°C upon packing.",
        "status": "Available",
        "created_at": now_iso,
        "is_sample_data": True,
    }

    listing_2 = {
        "_id": ObjectId("662000000000000000000002"),
        "restaurant_id": str(restaurant_1["_id"]),
        "restaurant_name": restaurant_1["org_name"],
        "restaurant_address": restaurant_1["address"],
        "restaurant_phone": restaurant_1["contact_phone"],
        "dish_name": "Dal Makhani & Jeera Rice Meal",
        "food_category": "Main Course",
        "initial_quantity": 30,
        "available_quantity": 30,
        "unit": "servings",
        "preparation_time": prep_2,
        "expiry_deadline": expiry_2,
        "storage_conditions": "Hot Held (above 63°C)",
        "is_vegetarian": True,
        "allergens": ["Dairy"],
        "pickup_address": restaurant_1["address"],
        "min_pickup_quantity": 5,
        "is_free": True,
        "price_per_unit": 0.0,
        "notes": "Freshly cooked lunch surplus. Sealed in individual microwaveable foil trays.",
        "status": "Available",
        "created_at": now_iso,
        "is_sample_data": True,
    }

    listing_3 = {
        "_id": ObjectId("662000000000000000000003"),
        "restaurant_id": str(restaurant_2["_id"]),
        "restaurant_name": restaurant_2["org_name"],
        "restaurant_address": restaurant_2["address"],
        "restaurant_phone": restaurant_2["contact_phone"],
        "dish_name": "Mediterranean Quinoa Falafel Bowls",
        "food_category": "Healthy Bowls",
        "initial_quantity": 20,
        "available_quantity": 20,
        "unit": "portions",
        "preparation_time": prep_3,
        "expiry_deadline": expiry_3,
        "storage_conditions": "Refrigerated (under 5°C)",
        "is_vegetarian": True,
        "allergens": ["Sesame"],
        "pickup_address": restaurant_2["address"],
        "min_pickup_quantity": 5,
        "is_free": True,
        "price_per_unit": 0.0,
        "notes": "Dressing packed separately in sanitized squeeze packets. Chilled at 3.5°C.",
        "status": "Available",
        "created_at": now_iso,
        "is_sample_data": True,
    }

    listings_col.insert_many([listing_1, listing_2, listing_3])
    print(f"Created 3 surplus food listings.")

    # 5. Example Donation Requests
    # Request 1: NGO 1 requested 25 servings of Listing 1 (Approved, waiting for pickup)
    request_1 = {
        "_id": ObjectId("663000000000000000000001"),
        "listing_id": str(listing_1["_id"]),
        "restaurant_id": str(restaurant_1["_id"]),
        "restaurant_name": restaurant_1["org_name"],
        "ngo_id": str(ngo_1["_id"]),
        "ngo_name": ngo_1["org_name"],
        "dish_name": listing_1["dish_name"],
        "requested_quantity": 25,
        "pickup_time": (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"),
        "status": "Approved",
        "notes": "Our insulated transport van is en route. Will distribute to Domlur night shelter.",
        "created_at": (datetime.now() - timedelta(minutes=45)).isoformat(),
        "updated_at": (datetime.now() - timedelta(minutes=30)).isoformat(),
        "is_sample_data": True,
    }

    # Request 2: NGO 2 requested 15 servings of Listing 2 (Requested - Pending Restaurant approval)
    request_2 = {
        "_id": ObjectId("663000000000000000000002"),
        "listing_id": str(listing_2["_id"]),
        "restaurant_id": str(restaurant_1["_id"]),
        "restaurant_name": restaurant_1["org_name"],
        "ngo_id": str(ngo_2["_id"]),
        "ngo_name": ngo_2["org_name"],
        "dish_name": listing_2["dish_name"],
        "requested_quantity": 15,
        "pickup_time": (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M"),
        "status": "Requested",
        "notes": "Requesting 15 meals for evening study center students in Jayanagar.",
        "created_at": (datetime.now() - timedelta(minutes=15)).isoformat(),
        "updated_at": (datetime.now() - timedelta(minutes=15)).isoformat(),
        "is_sample_data": True,
    }

    requests_col.insert_many([request_1, request_2])
    print("Created 2 active donation requests (1 Approved, 1 Pending).")

    # 6. Completed Donation Records (Historical Impact)
    # Records from past 3 weeks demonstrating verified circular impact
    completed_records = [
        {
            "_id": ObjectId("664000000000000000000001"),
            "request_id": "req-past-01",
            "listing_id": "listing-past-01",
            "restaurant_id": str(restaurant_1["_id"]),
            "restaurant_name": restaurant_1["org_name"],
            "ngo_id": str(ngo_1["_id"]),
            "ngo_name": ngo_1["org_name"],
            "dish_name": "Dum Biryani (Vegetable / Paneer)",
            "quantity_collected": 35,
            "unit": "servings",
            "beneficiaries_served": 35,
            "completion_date": (datetime.now() - timedelta(days=2)).isoformat(),
            "notes": "Distributed at Domlur community shelter. Zero food wasted.",
            "is_sample_data": True,
        },
        {
            "_id": ObjectId("664000000000000000000002"),
            "request_id": "req-past-02",
            "listing_id": "listing-past-02",
            "restaurant_id": str(restaurant_1["_id"]),
            "restaurant_name": restaurant_1["org_name"],
            "ngo_id": str(ngo_2["_id"]),
            "ngo_name": ngo_2["org_name"],
            "dish_name": "Paneer Butter Masala & Roti Basket",
            "quantity_collected": 40,
            "unit": "servings",
            "beneficiaries_served": 40,
            "completion_date": (datetime.now() - timedelta(days=5)).isoformat(),
            "notes": "Served to children and caregivers at Jayanagar center.",
            "is_sample_data": True,
        },
        {
            "_id": ObjectId("664000000000000000000003"),
            "request_id": "req-past-03",
            "listing_id": "listing-past-03",
            "restaurant_id": str(restaurant_2["_id"]),
            "restaurant_name": restaurant_2["org_name"],
            "ngo_id": str(ngo_1["_id"]),
            "ngo_name": ngo_1["org_name"],
            "dish_name": "Mediterranean Bowls & Penne",
            "quantity_collected": 28,
            "unit": "portions",
            "beneficiaries_served": 28,
            "completion_date": (datetime.now() - timedelta(days=9)).isoformat(),
            "notes": "Distributed to construction labor families near Koramangala.",
            "is_sample_data": True,
        },
        {
            "_id": ObjectId("664000000000000000000004"),
            "request_id": "req-past-04",
            "listing_id": "listing-past-04",
            "restaurant_id": str(restaurant_1["_id"]),
            "restaurant_name": restaurant_1["org_name"],
            "ngo_id": str(ngo_1["_id"]),
            "ngo_name": ngo_1["org_name"],
            "dish_name": "Hyderabadi Chicken Biryani",
            "quantity_collected": 45,
            "unit": "servings",
            "beneficiaries_served": 45,
            "completion_date": (datetime.now() - timedelta(days=14)).isoformat(),
            "notes": "Distributed with insulated thermal bags to flood relief temporary camp.",
            "is_sample_data": True,
        },
    ]

    records_col.insert_many(completed_records)
    print(f"Created {len(completed_records)} completed donation records.")

    print("\n========================================================")
    print("Database seeding completed successfully!")
    print("Demo Credentials for Testing:")
    print("  Restaurant Account:")
    print("    Email:    restaurant@foodcycle.org")
    print("    Password: demo123")
    print("  NGO Account:")
    print("    Email:    ngo@foodcycle.org")
    print("    Password: demo123")
    print("========================================================\n")


if __name__ == "__main__":
    seed_database()
