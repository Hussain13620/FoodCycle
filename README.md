# FoodCycle 🌿

> **"Predict Better. Waste Less. Feed More."**  
> A Circular Food Redistribution & Demand Forecasting Platform supporting **UN Sustainable Development Goal 12: Responsible Consumption and Production** and fighting hunger.

---

## 📌 Executive Summary

Nearly 30% of commercial kitchen food waste happens before a customer is ever served—primarily due to unpredictable rush patterns and precautionary overpreparation. 

**FoodCycle** addresses the crisis with a two-pillar circular economy model:
1. **AI Demand Prediction Engine**: Uses Scikit-Learn (`RandomForestRegressor`) with chronological validation, calendar awareness, and Indian festival tracking (Diwali, Eid, Holi, Christmas, etc.) to calculate accurate prep quantities with safety buffers.
2. **Surplus Food Redistribution Marketplace**: Inevitable daily surplus meals are published with preparation timestamps, holding temperatures (Chilled `<5°C` or Hot-Held `>63°C`), allergen declarations, and strict pickup deadlines. Verified NGOs claim partial or full batches with atomic reservation safety to feed local community shelters.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.10+ with [FastAPI](https://fastapi.tiangolo.com/)
- **Database**: [MongoDB](https://www.mongodb.com/) via PyMongo (local connection at `mongodb://localhost:27017/`)
- **Machine Learning**: `scikit-learn` (Random Forest Regression with chronological train/validation splits), `pandas`, and `numpy`
- **Frontend & Templating**: Jinja2 with semantic HTML5, Vanilla CSS3 design system, and Vanilla JavaScript
- **Visuals & Charts**: [Chart.js](https://www.chartjs.org/) and [Lucide Icons](https://lucide.dev/)
- **Authentication**: `pwdlib` (Argon2 / Bcrypt) and Starlette signed session cookies with Role-Based Access Control (RBAC)

---

## 🎨 Color Palette & Visual Identity

FoodCycle features a custom sustainability-focused color scheme:

| Color Name | Hex Code | Purpose |
| :--- | :--- | :--- |
| **Forest Green** | `#355E3B` | Primary actions, branding, navigation highlights |
| **Leaf Green** | `#6B8F5E` | Sustainability indicators, positive metrics, verified badges |
| **Warm Beige** | `#E8DCC8` | Borders, subtle card accents, secondary elements |
| **Off-White** | `#FAF8F2` | Main page background |
| **Earthy Brown**| `#795548` | Informational cards, supporting tags |
| **Dark Text** | `#2D332C` | High-contrast body typography |
| **Muted Text** | `#77766E` | Metadata, timestamps, captions |
| **White** | `#FFFFFF` | Card surfaces and input backgrounds |

---

## 🚀 Quickstart & Setup Guide

### 1. Prerequisites: MongoDB Setup

Before starting the application, ensure MongoDB is installed and running locally on port `27017`.

- **Windows**:
  Run PowerShell or Command Prompt as Administrator:
  ```powershell
  net start MongoDB
  ```
  *(Or execute `mongod` directly from your MongoDB `bin` folder)*

- **macOS**:
  ```bash
  brew services start mongodb/brew/mongodb-community
  ```

- **Linux (Ubuntu / Debian)**:
  ```bash
  sudo systemctl start mongod
  ```

> **Note**: If MongoDB is offline, FoodCycle displays a friendly error interface with instructions to launch the service rather than failing silently.

---

### 2. Install Python Dependencies

In your terminal or virtual environment:

```bash
pip install -r requirements.txt
```

---

### 3. Seed Database with Realistic Demo Data

Populate MongoDB with 2 restaurants, 2 NGOs, menu catalogs, 90 days of historical sales (showing weekend and festival surges), active surplus meals, and completed donation impact records:

```bash
python seed_data.py
```

---

### 4. Start the Application

Launch the FastAPI development server:

```bash
uvicorn main:app --reload
```

Open your browser at:  
👉 **`http://localhost:8000`**

---

## 🔑 Demo Credentials

FoodCycle includes 1-click credential auto-fill buttons on the login screen (`/login`), or you can log in manually:

### 1. Restaurant Account: The Spice Pavilion
- **Email**: `restaurant@foodcycle.org`
- **Password**: `demo123`
- **Features**: Menu catalog, 90-day sales history, AI demand forecasting for Diwali and weekend surges, surplus publishing, NGO request approvals.

### 2. Restaurant Account: Green Leaf Bistro
- **Email**: `bistro@foodcycle.org`
- **Password**: `demo123`
- **Features**: Mediterranean healthy bowls catalog, active surplus listings.

### 3. NGO Partner Account: Annapurna Food Relief
- **Email**: `ngo@foodcycle.org`
- **Password**: `demo123`
- **Features**: Surplus food marketplace, 1-click partial portion requests, pickup coordination, feeding drive completion logging.

### 4. NGO Partner Account: Hope Meal Foundation
- **Email**: `hope@foodcycle.org`
- **Password**: `demo123`
- **Features**: Pure vegetarian distribution preferences, community shelter logistics.

---

## 🧠 Machine Learning Demand Engine

Located in `prediction.py`:
- **Features Extracted**: Day of week (0–6), weekend flag (Fri–Sun rush), calendar month, Indian festivals (Diwali, Eid, Holi, Christmas, Dussehra, etc.), restaurant special events, 7-day rolling sales average, and 1-day lag demand.
- **Model**: `RandomForestRegressor` with chronological 80/20 train/validation splits (no future data leakage).
- **Explainable Predictions**: Each item forecast explains driving factors (e.g., *"+22% weekend surge for Biryani orders; upcoming Diwali festival period increases dining"*).
- **Graceful Fallback**: When fewer than 14 records exist for a dish, an explainable weighted heuristic baseline is applied, clearly labeled as fallback data.
- **Buffer Separation**: Predicted customer demand is cleanly decoupled from final kitchen batch recommendations using the restaurant's configurable safety margin (e.g., `+10%`).

---

## 🛡️ Atomic Concurrency & Overbooking Protection

To prevent multiple NGOs from overbooking the same surplus meal listing:
- Approvals use MongoDB conditional atomic updates:
  ```python
  listings_col.find_one_and_update(
      {"_id": listing_id, "available_quantity": {"$gte": requested_quantity}},
      {"$inc": {"available_quantity": -requested_quantity}},
      return_document=ReturnDocument.AFTER
  )
  ```
- If portions are already claimed, the system prevents overbooking and returns a clear alert.
- If an approved request is canceled or declined, reserved portions are automatically restored to the available pool.

---

## 🧪 Running the Automated Test Suite

To run the automated test suite testing RBAC, menu CRUD, demand forecasting, surplus marketplace, and atomic reservations:

```bash
python -m unittest test_app.py
```

---

## 📂 Project Architecture

```
FoodCycle/
├── main.py                 # FastAPI application, route controllers, session handling
├── database.py             # MongoDB connection, index creation, collection helpers
├── models.py               # Pydantic schemas for data validation
├── auth.py                 # pwdlib password hashing, session RBAC guards
├── prediction.py           # Scikit-learn Random Forest regression demand predictor
├── seed_data.py            # Comprehensive 90-day demo data generator
├── test_app.py             # Automated end-to-end unit and integration test suite
├── requirements.txt        # Python package dependencies
├── README.md               # Documentation and execution guide
├── static/
│   ├── css/
│   │   └── style.css       # Custom design system with FoodCycle color tokens
│   └── js/
│       └── app.js          # Modals, toasts, real-time filters, countdown timers
└── templates/
    ├── base.html           # Master layout with responsive nav & footer
    ├── index.html          # Public landing page with live database statistics
    ├── about.html          # UN SDG 12 mission & circular economy context
    ├── how_it_works.html   # 4-step workflow visualizer
    ├── impact.html         # Verified sustainability metrics & Chart.js breakdown
    ├── login.html          # Login screen with 1-click demo credential fillers
    ├── register.html       # Role selection tabs (Restaurant vs NGO)
    ├── restaurant_dashboard.html # Kitchen hub with KPI cards & demand charts
    ├── menu.html           # Dish catalog management (CRUD, veg/non-veg, allergens)
    ├── sales_history.html  # Daily sales logging & 90-day training records
    ├── forecast.html       # Scikit-Learn demand predictor with explainability
    ├── surplus_listings.html # Surplus food publishing with temperature standards
    ├── restaurant_requests.html # NGO request queue with atomic approve/reject
    ├── restaurant_profile.html # Kitchen operating details & safety buffer
    ├── ngo_dashboard.html  # NGO hub with pickup alerts & feeding stats
    ├── surplus_marketplace.html # Live marketplace with category & dietary filters
    ├── ngo_requests.html   # Request tracker & feeding drive completion modal
    ├── ngo_drives.html     # Historical feeding drive logbook
    ├── ngo_profile.html    # Beneficiary capacity & dietary preferences
    └── error_db.html       # Graceful MongoDB connection offline guide
```

---

## 🌍 UN SDG 12 Alignment

FoodCycle directly supports:
- **Target 12.3**: By 2030, halve per capita global food waste at the retail and consumer levels and reduce food losses along production and supply chains.
- **Target 2.1 (Zero Hunger)**: Ensuring safe, nutritious food surplus reaches vulnerable populations through verified community food rescue organizations.
