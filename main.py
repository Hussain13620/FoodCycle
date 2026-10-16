"""
FoodCycle - Circular Food Waste Prevention & NGO Redistribution Platform
FastAPI Application with PyMongo, Scikit-Learn Demand Forecasting, and Jinja2.
Supports UN Sustainable Development Goal 12.
"""

from datetime import datetime, date, timedelta
from typing import Optional, List
from bson import ObjectId
from pymongo import ReturnDocument

from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from database import (
    check_mongo_connection,
    init_indexes,
    get_users_collection,
    get_menu_collection,
    get_sales_collection,
    get_forecasts_collection,
    get_listings_collection,
    get_requests_collection,
    get_records_collection,
)
from auth import (
    SESSION_SECRET_KEY,
    hash_password,
    verify_password,
    get_current_user,
    login_user,
    logout_user,
    require_restaurant,
    require_ngo,
)
from prediction import (
    generate_restaurant_forecast,
    get_festival_for_date,
)

# Initialize FastAPI Application
app = FastAPI(
    title="FoodCycle",
    description="Circular Food Redistribution & Demand Forecasting Platform",
    version="1.0.0"
)

# Mount Session Middleware for secure signed cookie sessions
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY, max_age=86400 * 7)

# Mount Static Files and Jinja2 Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# Startup event: initialize indexes
@app.on_event("startup")
def on_startup():
    is_connected, msg = check_mongo_connection()
    if is_connected:
        init_indexes()
    else:
        print("STARTUP WARNING: MongoDB is not reachable.")
        print(msg)


def render_with_user(template_name: str, request: Request, context: dict, status_code: int = 200) -> HTMLResponse:
    """Helper to inject current_user and common state into templates."""
    user = get_current_user(request)
    context["request"] = request
    context["current_user"] = user
    return templates.TemplateResponse(request=request, name=template_name, context=context, status_code=status_code)


def check_db_or_error(request: Request):
    """Verify MongoDB connectivity; returns error template response if offline."""
    is_connected, msg = check_mongo_connection()
    if not is_connected:
        return templates.TemplateResponse(
            request=request,
            name="error_db.html",
            context={"request": request, "current_user": None, "error_details": msg},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    return None


# ============================================================================
# PUBLIC ROUTES
# ============================================================================

@app.get("/", response_class=HTMLResponse)
def page_home(request: Request):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    # Compute live metrics from database
    records_col = get_records_collection()
    users_col = get_users_collection()
    listings_col = get_listings_collection()

    completed = list(records_col.find({}))
    meals_distributed = sum(r.get("quantity_collected", 0) for r in completed)
    beneficiaries_served = sum(r.get("beneficiaries_served", 0) for r in completed)
    # Estimate kg diverted (approx 0.4kg per meal serving)
    kg_diverted = round(meals_distributed * 0.4, 1)
    co2_avoided = round(kg_diverted * 2.5, 1)

    restaurants_count = users_col.count_documents({"account_type": "restaurant"})
    ngos_count = users_col.count_documents({"account_type": "ngo"})

    # Active listings
    active_listings = list(listings_col.find({"status": "Available", "available_quantity": {"$gt": 0}}).sort("created_at", -1))

    stats = {
        "meals_distributed": meals_distributed,
        "beneficiaries_served": beneficiaries_served,
        "kg_diverted": kg_diverted,
        "co2_avoided": co2_avoided,
        "restaurants_count": restaurants_count,
        "ngos_count": ngos_count,
    }

    return render_with_user("index.html", request, {
        "active_page": "home",
        "stats": stats,
        "active_listings": active_listings,
    })


@app.get("/about", response_class=HTMLResponse)
def page_about(request: Request):
    return render_with_user("about.html", request, {"active_page": "about"})


@app.get("/how-it-works", response_class=HTMLResponse)
def page_how_it_works(request: Request):
    return render_with_user("how_it_works.html", request, {"active_page": "how_it_works"})


@app.get("/impact", response_class=HTMLResponse)
def page_impact(request: Request):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    records_col = get_records_collection()
    users_col = get_users_collection()

    completed = list(records_col.find({}).sort("completion_date", -1))
    meals_distributed = sum(r.get("quantity_collected", 0) for r in completed)
    beneficiaries_served = sum(r.get("beneficiaries_served", 0) for r in completed)
    kg_diverted = round(meals_distributed * 0.4, 1)
    co2_avoided = round(kg_diverted * 2.5, 1)

    stats = {
        "meals_distributed": meals_distributed,
        "beneficiaries_served": beneficiaries_served,
        "kg_diverted": kg_diverted,
        "co2_avoided": co2_avoided,
        "completed_donations_count": len(completed),
        "restaurants_count": users_col.count_documents({"account_type": "restaurant"}),
        "ngos_count": users_col.count_documents({"account_type": "ngo"}),
    }

    return render_with_user("impact.html", request, {
        "active_page": "impact",
        "stats": stats,
        "recent_records": completed[:10],
    })


@app.get("/marketplace", response_class=HTMLResponse)
def page_marketplace(request: Request):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    listings_col = get_listings_collection()
    listings = list(listings_col.find({
        "status": "Available",
        "available_quantity": {"$gt": 0}
    }).sort("created_at", -1))

    return render_with_user("surplus_marketplace.html", request, {
        "active_page": "marketplace",
        "listings": listings,
    })


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.get("/login", response_class=HTMLResponse)
def get_login(request: Request, msg: Optional[str] = None):
    user = get_current_user(request)
    if user:
        if user.get("account_type") == "restaurant":
            return RedirectResponse("/restaurant/dashboard", status_code=303)
        return RedirectResponse("/ngo/dashboard", status_code=303)
    return render_with_user("login.html", request, {"alert_message": msg, "alert_type": "info"})


@app.post("/login")
def post_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    users_col = get_users_collection()
    user = users_col.find_one({"email": email.strip().lower()})

    if not user or not verify_password(password, user.get("password_hash", "")):
        return render_with_user("login.html", request, {
            "alert_message": "Invalid email or password. Please try again or use the demo buttons.",
            "alert_type": "danger"
        })

    login_user(request, user)

    if user.get("account_type") == "restaurant":
        return RedirectResponse("/restaurant/dashboard", status_code=303)
    else:
        return RedirectResponse("/ngo/dashboard", status_code=303)


@app.get("/register", response_class=HTMLResponse)
def get_register(request: Request, role: Optional[str] = "restaurant"):
    return render_with_user("register.html", request, {"selected_role": role})


@app.post("/register")
def post_register(
    request: Request,
    account_type: str = Form(...),
    org_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    contact_phone: str = Form(...),
    address: str = Form(...),
    city: str = Form(default="Bengaluru"),
    pincode: Optional[str] = Form(default=""),
    cuisine_type: Optional[str] = Form(default=""),
    operating_hours: Optional[str] = Form(default=""),
    beneficiaries_served_daily: Optional[int] = Form(default=50),
    dietary_preferences: Optional[str] = Form(default="Both Vegetarian and Non-Vegetarian"),
    feeding_drive_details: Optional[str] = Form(default=""),
):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    users_col = get_users_collection()
    clean_email = email.strip().lower()

    if users_col.find_one({"email": clean_email}):
        return render_with_user("register.html", request, {
            "alert_message": "An account with this email already exists. Please log in.",
            "alert_type": "warning",
            "selected_role": account_type,
        })

    user_doc = {
        "org_name": org_name.strip(),
        "email": clean_email,
        "password_hash": hash_password(password),
        "account_type": account_type,
        "contact_phone": contact_phone.strip(),
        "address": address.strip(),
        "city": city.strip(),
        "pincode": pincode.strip() if pincode else "",
        "created_at": datetime.now().isoformat(),
    }

    if account_type == "restaurant":
        user_doc["cuisine_type"] = cuisine_type or "Multi-cuisine"
        user_doc["operating_hours"] = operating_hours or "11:00 AM - 11:00 PM"
        user_doc["safety_margin_pct"] = 10.0
    else:
        user_doc["beneficiaries_served_daily"] = beneficiaries_served_daily or 50
        user_doc["dietary_preferences"] = dietary_preferences or "Both Vegetarian and Non-Vegetarian"
        user_doc["feeding_drive_details"] = feeding_drive_details or "Community food rescue"

    inserted = users_col.insert_one(user_doc)
    user_doc["_id"] = inserted.inserted_id
    login_user(request, user_doc)

    if account_type == "restaurant":
        return RedirectResponse("/restaurant/dashboard", status_code=303)
    else:
        return RedirectResponse("/ngo/dashboard", status_code=303)


@app.get("/logout")
def get_logout(request: Request):
    logout_user(request)
    return RedirectResponse("/login?msg=You+have+been+logged+out+successfully.", status_code=303)


# ============================================================================
# RESTAURANT PORTAL ROUTES
# ============================================================================

@app.get("/restaurant/dashboard", response_class=HTMLResponse)
def get_restaurant_dashboard(request: Request, user=Depends(require_restaurant)):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    rest_id = str(user["_id"])
    today_str = date.today().strftime("%Y-%m-%d")

    # Generate or fetch today's forecast
    sales_col = get_sales_collection()
    menu_col = get_menu_collection()
    requests_col = get_requests_collection()
    listings_col = get_listings_collection()
    records_col = get_records_collection()

    margin = float(user.get("safety_margin_pct", 10.0))
    predictions = generate_restaurant_forecast(rest_id, today_str, margin, sales_col, menu_col)

    today_forecast_sum = sum(p["predicted_demand"] for p in predictions)
    expected_surplus_sum = sum(p["expected_surplus"] for p in predictions)

    pending_requests = list(requests_col.find({"restaurant_id": rest_id, "status": "Requested"}).sort("created_at", -1))
    active_listings = list(listings_col.find({"restaurant_id": rest_id, "status": "Available"}).sort("created_at", -1))
    completed_donations_count = records_col.count_documents({"restaurant_id": rest_id})

    return render_with_user("restaurant_dashboard.html", request, {
        "today_forecast_sum": today_forecast_sum,
        "expected_surplus_sum": expected_surplus_sum,
        "pending_requests_count": len(pending_requests),
        "pending_requests": pending_requests,
        "active_listings": active_listings,
        "completed_donations_count": completed_donations_count,
    })


@app.get("/restaurant/forecast", response_class=HTMLResponse)
def get_restaurant_forecast(
    request: Request,
    target_date: Optional[str] = None,
    safety_margin: Optional[float] = None,
    special_event: Optional[str] = None,
    user=Depends(require_restaurant)
):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    rest_id = str(user["_id"])
    if not target_date:
        # Default target date: tomorrow
        target_date = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")

    if safety_margin is None:
        safety_margin = float(user.get("safety_margin_pct", 10.0))

    sales_col = get_sales_collection()
    menu_col = get_menu_collection()

    events_map = {target_date: special_event} if special_event else {}
    predictions = generate_restaurant_forecast(
        restaurant_id=rest_id,
        target_date_str=target_date,
        safety_margin_pct=safety_margin,
        sales_col=sales_col,
        menu_col=menu_col,
        special_events_map=events_map
    )

    total_pred = sum(p["predicted_demand"] for p in predictions)
    total_rec = sum(p["recommended_production"] for p in predictions)
    total_surplus = sum(p["expected_surplus"] for p in predictions)
    festival_match = get_festival_for_date(target_date)

    return render_with_user("forecast.html", request, {
        "target_date": target_date,
        "safety_margin": int(safety_margin),
        "special_event": special_event,
        "predictions": predictions,
        "total_predicted_demand": total_pred,
        "total_recommended_production": total_rec,
        "total_expected_surplus": total_surplus,
        "festival_detected": festival_match,
    })


@app.post("/restaurant/forecast/save")
def post_save_forecast(
    request: Request,
    target_date: str = Form(...),
    safety_margin: float = Form(default=10.0),
    user=Depends(require_restaurant)
):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    rest_id = str(user["_id"])
    sales_col = get_sales_collection()
    menu_col = get_menu_collection()
    forecasts_col = get_forecasts_collection()

    predictions = generate_restaurant_forecast(rest_id, target_date, safety_margin, sales_col, menu_col)

    # Save to demand_forecasts collection
    forecast_doc = {
        "restaurant_id": rest_id,
        "target_date": target_date,
        "safety_margin_pct": safety_margin,
        "dishes": predictions,
        "created_at": datetime.now().isoformat(),
    }
    forecasts_col.update_one(
        {"restaurant_id": rest_id, "target_date": target_date},
        {"$set": forecast_doc},
        upsert=True
    )

    return RedirectResponse(
        f"/restaurant/forecast?target_date={target_date}&safety_margin={safety_margin}",
        status_code=303
    )


@app.get("/restaurant/menu", response_class=HTMLResponse)
def get_restaurant_menu(request: Request, user=Depends(require_restaurant)):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    rest_id = str(user["_id"])
    menu_col = get_menu_collection()
    items = list(menu_col.find({"restaurant_id": rest_id}).sort("dish_name", 1))

    return render_with_user("menu.html", request, {"menu_items": items})


@app.post("/restaurant/menu")
def post_restaurant_menu(
    request: Request,
    dish_name: str = Form(...),
    category: str = Form(default="Main Course"),
    price: float = Form(default=0.0),
    serving_size: str = Form(default="1 portion (~400g)"),
    is_vegetarian: str = Form(default="true"),
    allergens_raw: Optional[str] = Form(default=""),
    user=Depends(require_restaurant)
):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    rest_id = str(user["_id"])
    menu_col = get_menu_collection()

    allergens = [a.strip() for a in allergens_raw.split(",") if a.strip()] if allergens_raw else []

    item_doc = {
        "restaurant_id": rest_id,
        "dish_name": dish_name.strip(),
        "category": category,
        "price": float(price),
        "serving_size": serving_size.strip(),
        "is_vegetarian": (is_vegetarian.lower() == "true"),
        "allergens": allergens,
        "is_active": True,
        "created_at": datetime.now().isoformat(),
    }
    menu_col.insert_one(item_doc)
    return RedirectResponse("/restaurant/menu", status_code=303)


@app.post("/restaurant/menu/{item_id}/toggle")
def post_toggle_menu_item(item_id: str, request: Request, user=Depends(require_restaurant)):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    menu_col = get_menu_collection()
    item = menu_col.find_one({"_id": ObjectId(item_id), "restaurant_id": str(user["_id"])})
    if item:
        new_status = not item.get("is_active", True)
        menu_col.update_one({"_id": ObjectId(item_id)}, {"$set": {"is_active": new_status}})
    return RedirectResponse("/restaurant/menu", status_code=303)


@app.post("/restaurant/menu/{item_id}/delete")
def post_delete_menu_item(item_id: str, request: Request, user=Depends(require_restaurant)):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    menu_col = get_menu_collection()
    menu_col.delete_one({"_id": ObjectId(item_id), "restaurant_id": str(user["_id"])})
    return RedirectResponse("/restaurant/menu", status_code=303)


@app.get("/restaurant/sales", response_class=HTMLResponse)
def get_restaurant_sales(request: Request, user=Depends(require_restaurant)):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    rest_id = str(user["_id"])
    sales_col = get_sales_collection()
    menu_col = get_menu_collection()

    sales = list(sales_col.find({"restaurant_id": rest_id}).sort("date", -1).limit(60))
    menu_items = list(menu_col.find({"restaurant_id": rest_id, "is_active": True}))

    today_str = date.today().strftime("%Y-%m-%d")

    return render_with_user("sales_history.html", request, {
        "sales_records": sales,
        "total_count": len(sales),
        "menu_items": menu_items,
        "today_str": today_str,
    })


@app.post("/restaurant/sales")
def post_restaurant_sales(
    request: Request,
    dish_id: str = Form(...),
    date: str = Form(...),
    quantity_sold: int = Form(...),
    quantity_produced: int = Form(...),
    leftover_quantity: int = Form(...),
    special_event: Optional[str] = Form(default=None),
    user=Depends(require_restaurant)
):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    rest_id = str(user["_id"])
    menu_col = get_menu_collection()
    sales_col = get_sales_collection()

    dish = menu_col.find_one({"_id": ObjectId(dish_id)})
    dish_name = dish.get("dish_name", "Dish") if dish else "Dish"

    date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    dow = date_obj.weekday()
    is_weekend = 1 if dow in (4, 5, 6) else 0

    sales_doc = {
        "restaurant_id": rest_id,
        "dish_id": dish_id,
        "dish_name": dish_name,
        "date": date,
        "day_of_week": dow,
        "is_weekend": is_weekend,
        "quantity_sold": int(quantity_sold),
        "quantity_produced": int(quantity_produced),
        "leftover_quantity": int(leftover_quantity),
        "special_event": special_event.strip() if (special_event and special_event.strip()) else None,
        "created_at": datetime.now().isoformat(),
    }
    sales_col.insert_one(sales_doc)
    return RedirectResponse("/restaurant/sales", status_code=303)


@app.get("/restaurant/surplus", response_class=HTMLResponse)
def get_restaurant_surplus(request: Request, user=Depends(require_restaurant)):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    rest_id = str(user["_id"])
    listings_col = get_listings_collection()

    active = list(listings_col.find({"restaurant_id": rest_id, "status": "Available"}).sort("created_at", -1))
    past = list(listings_col.find({"restaurant_id": rest_id, "status": {"$ne": "Available"}}).sort("created_at", -1))

    now = datetime.now()
    default_prep = now.strftime("%Y-%m-%dT%H:%M")
    default_expiry = (now + timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M")

    return render_with_user("surplus_listings.html", request, {
        "active_listings": active,
        "past_listings": past,
        "default_prep_time": default_prep,
        "default_expiry_time": default_expiry,
    })


@app.post("/restaurant/surplus")
def post_restaurant_surplus(
    request: Request,
    dish_name: str = Form(...),
    food_category: str = Form(default="Prepared Rice & Meals"),
    initial_quantity: int = Form(...),
    unit: str = Form(default="servings"),
    preparation_time: str = Form(...),
    expiry_deadline: str = Form(...),
    storage_conditions: str = Form(...),
    is_vegetarian: str = Form(default="true"),
    allergens_raw: Optional[str] = Form(default=""),
    pickup_address: str = Form(...),
    notes: Optional[str] = Form(default=""),
    user=Depends(require_restaurant)
):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    rest_id = str(user["_id"])
    listings_col = get_listings_collection()

    allergens = [a.strip() for a in allergens_raw.split(",") if a.strip()] if allergens_raw else []

    doc = {
        "restaurant_id": rest_id,
        "restaurant_name": user.get("org_name", "Restaurant"),
        "restaurant_address": user.get("address", ""),
        "restaurant_phone": user.get("contact_phone", ""),
        "dish_name": dish_name.strip(),
        "food_category": food_category,
        "initial_quantity": int(initial_quantity),
        "available_quantity": int(initial_quantity),
        "unit": unit,
        "preparation_time": preparation_time,
        "expiry_deadline": expiry_deadline,
        "storage_conditions": storage_conditions,
        "is_vegetarian": (is_vegetarian.lower() == "true"),
        "allergens": allergens,
        "pickup_address": pickup_address.strip(),
        "min_pickup_quantity": 1,
        "is_free": True,
        "price_per_unit": 0.0,
        "notes": notes.strip() if notes else "",
        "status": "Available",
        "created_at": datetime.now().isoformat(),
    }
    listings_col.insert_one(doc)
    return RedirectResponse("/restaurant/surplus", status_code=303)


@app.post("/restaurant/surplus/{listing_id}/cancel")
def post_cancel_surplus_listing(listing_id: str, request: Request, user=Depends(require_restaurant)):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    listings_col = get_listings_collection()
    listings_col.update_one(
        {"_id": ObjectId(listing_id), "restaurant_id": str(user["_id"])},
        {"$set": {"status": "Cancelled"}}
    )
    return RedirectResponse("/restaurant/surplus", status_code=303)


@app.get("/restaurant/requests", response_class=HTMLResponse)
def get_restaurant_requests(request: Request, user=Depends(require_restaurant)):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    rest_id = str(user["_id"])
    requests_col = get_requests_collection()
    reqs = list(requests_col.find({"restaurant_id": rest_id}).sort("created_at", -1))

    return render_with_user("restaurant_requests.html", request, {"requests_list": reqs})


@app.post("/restaurant/requests/{req_id}/approve")
def post_approve_request(req_id: str, request: Request, user=Depends(require_restaurant)):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    rest_id = str(user["_id"])
    requests_col = get_requests_collection()
    listings_col = get_listings_collection()

    req = requests_col.find_one({"_id": ObjectId(req_id), "restaurant_id": rest_id})
    if not req or req.get("status") != "Requested":
        return RedirectResponse("/restaurant/requests", status_code=303)

    requested_qty = req.get("requested_quantity", 0)
    listing_id = ObjectId(req.get("listing_id"))

    # ATOMIC RESERVATION: check available_quantity >= requested_qty and decrement
    updated_listing = listings_col.find_one_and_update(
        {"_id": listing_id, "available_quantity": {"$gte": requested_qty}},
        {"$inc": {"available_quantity": -requested_qty}},
        return_document=ReturnDocument.AFTER
    )

    if not updated_listing:
        # Not enough quantity available (overbooking prevented!)
        return render_with_user("restaurant_requests.html", request, {
            "requests_list": list(requests_col.find({"restaurant_id": rest_id}).sort("created_at", -1)),
            "alert_message": "Could not approve: Insufficient remaining surplus quantity (overbooking prevented).",
            "alert_type": "danger",
        })

    # If remaining quantity reached 0, mark listing status
    if updated_listing.get("available_quantity", 0) <= 0:
        listings_col.update_one({"_id": listing_id}, {"$set": {"status": "Fully Claimed"}})

    # Mark request Approved
    requests_col.update_one(
        {"_id": ObjectId(req_id)},
        {"$set": {"status": "Approved", "updated_at": datetime.now().isoformat()}}
    )

    return RedirectResponse("/restaurant/requests", status_code=303)


@app.post("/restaurant/requests/{req_id}/reject")
def post_reject_request(req_id: str, request: Request, user=Depends(require_restaurant)):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    rest_id = str(user["_id"])
    requests_col = get_requests_collection()
    listings_col = get_listings_collection()

    req = requests_col.find_one({"_id": ObjectId(req_id), "restaurant_id": rest_id})
    if req:
        # If it was already approved, release the reserved quantity
        if req.get("status") == "Approved":
            listings_col.update_one(
                {"_id": ObjectId(req["listing_id"])},
                {
                    "$inc": {"available_quantity": req.get("requested_quantity", 0)},
                    "$set": {"status": "Available"}
                }
            )

        requests_col.update_one(
            {"_id": ObjectId(req_id)},
            {"$set": {"status": "Rejected", "updated_at": datetime.now().isoformat()}}
        )

    return RedirectResponse("/restaurant/requests", status_code=303)


@app.post("/restaurant/requests/{req_id}/mark-collected")
def post_restaurant_mark_collected(req_id: str, request: Request, user=Depends(require_restaurant)):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    rest_id = str(user["_id"])
    requests_col = get_requests_collection()
    requests_col.update_one(
        {"_id": ObjectId(req_id), "restaurant_id": rest_id},
        {"$set": {"status": "Collected", "updated_at": datetime.now().isoformat()}}
    )
    return RedirectResponse("/restaurant/requests", status_code=303)


@app.get("/restaurant/profile", response_class=HTMLResponse)
def get_restaurant_profile(request: Request, user=Depends(require_restaurant)):
    return render_with_user("restaurant_profile.html", request, {})


@app.post("/restaurant/profile")
def post_restaurant_profile(
    request: Request,
    org_name: str = Form(...),
    contact_phone: str = Form(...),
    address: str = Form(...),
    cuisine_type: Optional[str] = Form(default=""),
    operating_hours: Optional[str] = Form(default=""),
    safety_margin_pct: float = Form(default=10.0),
    user=Depends(require_restaurant)
):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    users_col = get_users_collection()
    users_col.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "org_name": org_name.strip(),
            "contact_phone": contact_phone.strip(),
            "address": address.strip(),
            "cuisine_type": cuisine_type.strip() if cuisine_type else "",
            "operating_hours": operating_hours.strip() if operating_hours else "",
            "safety_margin_pct": float(safety_margin_pct),
        }}
    )
    request.session["org_name"] = org_name.strip()
    return RedirectResponse("/restaurant/profile", status_code=303)


# ============================================================================
# NGO PORTAL ROUTES
# ============================================================================

@app.get("/ngo/dashboard", response_class=HTMLResponse)
def get_ngo_dashboard(request: Request, user=Depends(require_ngo)):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    ngo_id = str(user["_id"])
    requests_col = get_requests_collection()
    listings_col = get_listings_collection()
    records_col = get_records_collection()

    available_listings = list(listings_col.find({"status": "Available", "available_quantity": {"$gt": 0}}).sort("created_at", -1))
    my_requests = list(requests_col.find({"ngo_id": ngo_id}).sort("created_at", -1))
    approved_requests = [r for r in my_requests if r.get("status") == "Approved"]

    # Historical impact records
    drives = list(records_col.find({"ngo_id": ngo_id}))
    total_food_collected = sum(d.get("quantity_collected", 0) for d in drives)
    total_beneficiaries = sum(d.get("beneficiaries_served", 0) for d in drives)

    return render_with_user("ngo_dashboard.html", request, {
        "available_listings": available_listings,
        "my_requests": my_requests,
        "approved_requests": approved_requests,
        "approved_pickups_count": len(approved_requests),
        "total_food_collected": total_food_collected,
        "total_beneficiaries": total_beneficiaries,
        "completed_drives_count": len(drives),
    })


@app.post("/ngo/requests")
def post_ngo_create_request(
    request: Request,
    listing_id: str = Form(...),
    requested_quantity: int = Form(...),
    pickup_time: str = Form(...),
    notes: Optional[str] = Form(default=""),
    user=Depends(require_ngo)
):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    ngo_id = str(user["_id"])
    listings_col = get_listings_collection()
    requests_col = get_requests_collection()

    listing = listings_col.find_one({"_id": ObjectId(listing_id)})
    if not listing or listing.get("status") != "Available":
        return RedirectResponse("/marketplace", status_code=303)

    req_qty = int(requested_quantity)
    avail_qty = int(listing.get("available_quantity", 0))

    if req_qty > avail_qty or req_qty <= 0:
        return RedirectResponse("/marketplace", status_code=303)

    req_doc = {
        "listing_id": listing_id,
        "restaurant_id": str(listing.get("restaurant_id")),
        "restaurant_name": listing.get("restaurant_name"),
        "ngo_id": ngo_id,
        "ngo_name": user.get("org_name", "NGO"),
        "dish_name": listing.get("dish_name"),
        "requested_quantity": req_qty,
        "pickup_time": pickup_time.replace("T", " "),
        "status": "Requested",
        "notes": notes.strip() if notes else "",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    requests_col.insert_one(req_doc)

    return RedirectResponse("/ngo/requests", status_code=303)


@app.get("/ngo/requests", response_class=HTMLResponse)
def get_ngo_requests(request: Request, user=Depends(require_ngo)):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    ngo_id = str(user["_id"])
    requests_col = get_requests_collection()
    reqs = list(requests_col.find({"ngo_id": ngo_id}).sort("created_at", -1))

    return render_with_user("ngo_requests.html", request, {"requests_list": reqs})


@app.post("/ngo/requests/{req_id}/cancel")
def post_ngo_cancel_request(req_id: str, request: Request, user=Depends(require_ngo)):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    ngo_id = str(user["_id"])
    requests_col = get_requests_collection()
    listings_col = get_listings_collection()

    req = requests_col.find_one({"_id": ObjectId(req_id), "ngo_id": ngo_id})
    if req and req.get("status") in ["Requested", "Approved"]:
        # If it was approved, restore quantity to listing
        if req.get("status") == "Approved":
            listings_col.update_one(
                {"_id": ObjectId(req["listing_id"])},
                {
                    "$inc": {"available_quantity": req.get("requested_quantity", 0)},
                    "$set": {"status": "Available"}
                }
            )

        requests_col.update_one(
            {"_id": ObjectId(req_id)},
            {"$set": {"status": "Cancelled", "updated_at": datetime.now().isoformat()}}
        )

    return RedirectResponse("/ngo/requests", status_code=303)


@app.post("/ngo/requests/{req_id}/confirm-pickup")
def post_ngo_confirm_pickup(req_id: str, request: Request, user=Depends(require_ngo)):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    ngo_id = str(user["_id"])
    requests_col = get_requests_collection()
    requests_col.update_one(
        {"_id": ObjectId(req_id), "ngo_id": ngo_id},
        {"$set": {"status": "Collected", "updated_at": datetime.now().isoformat()}}
    )
    return RedirectResponse("/ngo/requests", status_code=303)


@app.post("/ngo/requests/complete")
def post_ngo_complete_drive(
    request: Request,
    request_id: str = Form(...),
    actual_quantity: int = Form(...),
    beneficiaries_served: int = Form(...),
    notes: Optional[str] = Form(default=""),
    user=Depends(require_ngo)
):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    ngo_id = str(user["_id"])
    requests_col = get_requests_collection()
    records_col = get_records_collection()

    req = requests_col.find_one({"_id": ObjectId(request_id), "ngo_id": ngo_id})
    if not req:
        return RedirectResponse("/ngo/requests", status_code=303)

    # Update request state to Completed
    requests_col.update_one(
        {"_id": ObjectId(request_id)},
        {"$set": {"status": "Completed", "updated_at": datetime.now().isoformat()}}
    )

    # Insert verified donation record
    record_doc = {
        "request_id": request_id,
        "listing_id": req.get("listing_id"),
        "restaurant_id": req.get("restaurant_id"),
        "restaurant_name": req.get("restaurant_name"),
        "ngo_id": ngo_id,
        "ngo_name": user.get("org_name", "NGO"),
        "dish_name": req.get("dish_name"),
        "quantity_collected": int(actual_quantity),
        "unit": "servings",
        "beneficiaries_served": int(beneficiaries_served),
        "completion_date": datetime.now().isoformat(),
        "notes": notes.strip() if notes else "Food distributed safely to community beneficiaries.",
    }
    records_col.insert_one(record_doc)

    return RedirectResponse("/ngo/drives", status_code=303)


@app.get("/ngo/drives", response_class=HTMLResponse)
def get_ngo_drives(request: Request, user=Depends(require_ngo)):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    ngo_id = str(user["_id"])
    records_col = get_records_collection()

    drives = list(records_col.find({"ngo_id": ngo_id}).sort("completion_date", -1))
    total_rescued = sum(d.get("quantity_collected", 0) for d in drives)
    total_served = sum(d.get("beneficiaries_served", 0) for d in drives)

    return render_with_user("ngo_drives.html", request, {
        "drives_list": drives,
        "total_rescued": total_rescued,
        "total_served": total_served,
    })


@app.get("/ngo/profile", response_class=HTMLResponse)
def get_ngo_profile(request: Request, user=Depends(require_ngo)):
    return render_with_user("ngo_profile.html", request, {})


@app.post("/ngo/profile")
def post_ngo_profile(
    request: Request,
    org_name: str = Form(...),
    contact_phone: str = Form(...),
    address: str = Form(...),
    city: str = Form(default="Bengaluru"),
    beneficiaries_served_daily: int = Form(default=50),
    dietary_preferences: str = Form(default="Both Vegetarian and Non-Vegetarian"),
    feeding_drive_details: Optional[str] = Form(default=""),
    user=Depends(require_ngo)
):
    db_err = check_db_or_error(request)
    if db_err: return db_err

    users_col = get_users_collection()
    users_col.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "org_name": org_name.strip(),
            "contact_phone": contact_phone.strip(),
            "address": address.strip(),
            "city": city.strip(),
            "beneficiaries_served_daily": int(beneficiaries_served_daily),
            "dietary_preferences": dietary_preferences,
            "feeding_drive_details": feeding_drive_details.strip() if feeding_drive_details else "",
        }}
    )
    request.session["org_name"] = org_name.strip()
    return RedirectResponse("/ngo/profile", status_code=303)


# Global Exception Handler for 401 / 403 HTTPExceptions
@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        return RedirectResponse(f"/login?msg={exc.detail}", status_code=303)
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        return render_with_user("index.html", request, {
            "alert_message": exc.detail,
            "alert_type": "danger",
            "stats": {"meals_distributed": 0, "beneficiaries_served": 0, "kg_diverted": 0, "co2_avoided": 0, "restaurants_count": 0, "ngos_count": 0},
            "active_listings": [],
        })
    return HTMLResponse(content=f"Error {exc.status_code}: {exc.detail}", status_code=exc.status_code)
