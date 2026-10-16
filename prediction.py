"""
Demand Prediction Engine for FoodCycle
Uses scikit-learn (RandomForestRegressor) with chronological validation and calendar/festival features,
with a transparent, explainable heuristic fallback when historical records are sparse.
"""

import math
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

# Indian Festivals and Significant Food-Consumption Occasions
# Dates for 2024, 2025, 2026, 2027
KNOWN_FESTIVALS = {
    # 2024
    "2024-01-26": "Republic Day",
    "2024-03-25": "Holi",
    "2024-04-11": "Eid al-Fitr",
    "2024-08-15": "Independence Day",
    "2024-10-12": "Dussehra",
    "2024-10-31": "Diwali",
    "2024-11-01": "Diwali Festive Weekend",
    "2024-12-25": "Christmas",
    "2024-12-31": "New Year's Eve",
    # 2025
    "2025-01-26": "Republic Day",
    "2025-03-14": "Holi",
    "2025-03-31": "Eid al-Fitr",
    "2025-08-15": "Independence Day",
    "2025-10-02": "Dussehra / Gandhi Jayanti",
    "2025-10-20": "Diwali",
    "2025-10-21": "Diwali Festive Period",
    "2025-12-25": "Christmas",
    "2025-12-31": "New Year's Eve",
    # 2026
    "2026-01-26": "Republic Day",
    "2026-03-04": "Holi",
    "2026-03-20": "Eid al-Fitr",
    "2026-08-15": "Independence Day",
    "2026-10-19": "Dussehra",
    "2026-11-08": "Diwali",
    "2026-11-09": "Diwali Festive Weekend",
    "2026-12-25": "Christmas",
    "2026-12-31": "New Year's Eve",
    # 2027
    "2027-01-26": "Republic Day",
    "2027-03-23": "Holi",
    "2027-04-09": "Eid al-Fitr",
    "2027-08-15": "Independence Day",
    "2027-10-09": "Dussehra",
    "2027-10-29": "Diwali",
    "2027-12-25": "Christmas",
    "2027-12-31": "New Year's Eve",
}


def get_festival_for_date(date_str: str) -> Optional[str]:
    """Check if date matches a known Indian festival or holiday."""
    return KNOWN_FESTIVALS.get(date_str)


def build_date_features(target_date_obj: date, special_event: Optional[str] = None) -> Dict[str, Any]:
    """Extract calendar features for a given date."""
    target_str = target_date_obj.strftime("%Y-%m-%d")
    dow = target_date_obj.weekday()  # 0=Monday, 6=Sunday
    is_weekend = 1 if dow in (4, 5, 6) else 0  # Fri/Sat/Sun count towards weekend restaurant rush
    festival_name = get_festival_for_date(target_str)
    is_festival = 1 if festival_name else 0
    has_special_event = 1 if (special_event and special_event.strip()) else 0

    return {
        "date_str": target_str,
        "day_of_week": dow,
        "is_weekend": is_weekend,
        "month": target_date_obj.month,
        "day": target_date_obj.day,
        "is_festival": is_festival,
        "festival_name": festival_name,
        "has_special_event": has_special_event,
        "special_event": special_event,
    }


def predict_dish_demand(
    dish_id: str,
    dish_name: str,
    sales_records: List[Dict[str, Any]],
    target_date_str: str,
    safety_margin_pct: float = 10.0,
    special_event: Optional[str] = None
) -> Dict[str, Any]:
    """
    Predict demand for a specific dish on target_date_str.
    Uses RandomForestRegressor with chronological validation if records >= 14.
    Otherwise uses an explainable heuristic fallback.
    """
    target_date_obj = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    target_feats = build_date_features(target_date_obj, special_event)
    day_name = target_date_obj.strftime("%A")

    # If no records exist at all
    if not sales_records:
        default_servings = 20
        recommended_prod = math.ceil(default_servings * (1 + safety_margin_pct / 100.0))
        return {
            "dish_id": dish_id,
            "dish_name": dish_name,
            "target_date": target_date_str,
            "day_name": day_name,
            "historical_avg": 0.0,
            "predicted_demand": default_servings,
            "recommended_production": recommended_prod,
            "expected_surplus": recommended_prod - default_servings,
            "data_quality": "Insufficient Data (New Dish)",
            "model_used": "Baseline Fallback",
            "confidence_score": 25,
            "factors": [
                "No previous sales data recorded for this item.",
                "Defaulting to a conservative baseline of 20 servings.",
                "Record daily sales to unlock AI machine learning forecasts."
            ],
            "suggested_adjustment": "Set baseline production based on chef judgment.",
            "safety_margin_pct": safety_margin_pct,
            "is_ml": False,
        }

    # Convert records to sorted DataFrame
    df = pd.DataFrame(sales_records)
    df["date_dt"] = pd.to_datetime(df["date"])
    df = df.sort_values("date_dt").reset_index(drop=True)

    # Basic historical metrics
    historical_avg = float(df["quantity_sold"].mean())
    usual_production = float(df["quantity_produced"].mean()) if "quantity_produced" in df else historical_avg

    # Filter records for same day-of-week
    df["day_of_week"] = df["date_dt"].dt.weekday
    same_dow_sales = df[df["day_of_week"] == target_feats["day_of_week"]]["quantity_sold"]
    dow_avg = float(same_dow_sales.mean()) if not same_dow_sales.empty else historical_avg

    # Case A: Sufficient Data (>= 14 observations) -> Machine Learning with Chronological Validation
    if len(df) >= 14:
        # Build features for historical data
        df["is_weekend"] = df["day_of_week"].apply(lambda d: 1 if d in (4, 5, 6) else 0)
        df["month"] = df["date_dt"].dt.month
        df["day"] = df["date_dt"].dt.day
        df["is_festival"] = df["date"].apply(lambda d: 1 if get_festival_for_date(str(d)) else 0)
        df["has_special_event"] = df["special_event"].apply(lambda e: 1 if (pd.notna(e) and str(e).strip() != "") else 0)

        # 7-day rolling sales demand
        df["rolling_7d_avg"] = df["quantity_sold"].rolling(window=7, min_periods=1).mean()
        # Lag 1 day sales
        df["lag_1d"] = df["quantity_sold"].shift(1).bfill()

        feature_cols = [
            "day_of_week", "is_weekend", "month", "day",
            "is_festival", "has_special_event", "rolling_7d_avg", "lag_1d"
        ]

        # Chronological Split: 80% train, 20% validation
        n_samples = len(df)
        split_idx = max(int(n_samples * 0.8), n_samples - 4)
        train_df = df.iloc[:split_idx]
        val_df = df.iloc[split_idx:]

        X_train = train_df[feature_cols]
        y_train = train_df["quantity_sold"]

        model = RandomForestRegressor(
            n_estimators=60,
            max_depth=6,
            min_samples_split=2,
            random_state=42
        )
        model.fit(X_train, y_train)

        # Evaluate on validation set
        val_mae = 0.0
        if not val_df.empty:
            val_preds = model.predict(val_df[feature_cols])
            val_mae = float(mean_absolute_error(val_df["quantity_sold"], val_preds))

        # Recent trend
        recent_7d = float(df["quantity_sold"].tail(7).mean())
        last_recorded_sale = float(df["quantity_sold"].iloc[-1])

        # Prepare target feature vector
        target_X = pd.DataFrame([{
            "day_of_week": target_feats["day_of_week"],
            "is_weekend": target_feats["is_weekend"],
            "month": target_feats["month"],
            "day": target_feats["day"],
            "is_festival": target_feats["is_festival"],
            "has_special_event": target_feats["has_special_event"],
            "rolling_7d_avg": recent_7d,
            "lag_1d": last_recorded_sale,
        }])[feature_cols]

        raw_pred = float(model.predict(target_X)[0])
        predicted_demand = max(1, int(round(raw_pred)))

        # Confidence based on dataset size and validation error
        if len(df) >= 40 and val_mae < 4.0:
            quality = f"High Quality (ML Model - {len(df)} records)"
            confidence = 88
        elif len(df) >= 20:
            quality = f"Moderate Quality (ML Model - {len(df)} records)"
            confidence = 78
        else:
            quality = f"Emerging ML Model ({len(df)} records)"
            confidence = 68

        # Explainability factors
        factors = []
        if target_feats["is_weekend"]:
            diff_pct = int(((dow_avg - historical_avg) / (historical_avg or 1)) * 100)
            factors.append(f"Weekend pattern: {day_name} orders average {dow_avg:.1f} servings ({diff_pct:+d}% vs overall avg).")
        else:
            factors.append(f"Weekday baseline: Typical {day_name} demand is {dow_avg:.1f} servings.")

        if target_feats["festival_name"]:
            factors.append(f"Festival multiplier: {target_feats['festival_name']} historically boosts dining out and catering orders.")

        if target_feats["has_special_event"]:
            factors.append(f"Special event: '{special_event}' flagged for this date.")

        if recent_7d > historical_avg * 1.08:
            factors.append("Upward demand momentum: Recent 7-day average is trending higher than historical average.")
        elif recent_7d < historical_avg * 0.92:
            factors.append("Cooling trend: Recent sales have been slightly below long-term average.")

        model_used = "RandomForestRegressor (Chronological Validation)"
        is_ml = True

    # Case B: Heuristic Fallback (records < 14)
    else:
        # Transparent fallback combining weekday average and recent momentum
        weight_dow = 0.5
        weight_overall = 0.3
        recent_3 = float(df["quantity_sold"].tail(3).mean())
        weight_recent = 0.2

        raw_calc = (dow_avg * weight_dow) + (historical_avg * weight_overall) + (recent_3 * weight_recent)

        # Festival adjustment if data supports or target date is festival
        if target_feats["festival_name"]:
            raw_calc *= 1.15  # modest 15% festive lift

        if target_feats["has_special_event"]:
            raw_calc *= 1.10

        predicted_demand = max(1, int(round(raw_calc)))
        quality = f"Low Data / Fallback Heuristic ({len(df)} entries, needs ≥14 for ML)"
        confidence = 52
        model_used = "Weighted Historical Baseline (Heuristic Fallback)"
        is_ml = False

        factors = [
            f"Heuristic Fallback used: Only {len(df)} historical entries found (<14 needed for machine learning model).",
            f"Based on {day_name} average ({dow_avg:.1f} servings) and recent 3-day average ({recent_3:.1f} servings).",
        ]
        if target_feats["festival_name"]:
            factors.append(f"Festive adjustment (+15%) applied for {target_feats['festival_name']}.")

    # Production recommendation with safety margin & batch rounding
    recommended_production = math.ceil(predicted_demand * (1.0 + (safety_margin_pct / 100.0)))
    expected_surplus = max(0, recommended_production - predicted_demand)

    # Comparison with usual production
    diff_from_usual = recommended_production - int(round(usual_production))
    if diff_from_usual > 0:
        adj_text = f"+{diff_from_usual} servings above usual prep (anticipating surge)"
    elif diff_from_usual < 0:
        adj_text = f"{diff_from_usual} servings below usual prep (preventing surplus)"
    else:
        adj_text = "Matches usual preparation quantity"

    return {
        "dish_id": dish_id,
        "dish_name": dish_name,
        "target_date": target_date_str,
        "day_name": day_name,
        "historical_avg": round(historical_avg, 1),
        "predicted_demand": predicted_demand,
        "recommended_production": recommended_production,
        "expected_surplus": expected_surplus,
        "data_quality": quality,
        "model_used": model_used,
        "confidence_score": confidence,
        "factors": factors,
        "suggested_adjustment": adj_text,
        "safety_margin_pct": safety_margin_pct,
        "is_ml": is_ml,
    }


def generate_restaurant_forecast(
    restaurant_id: str,
    target_date_str: str,
    safety_margin_pct: float = 10.0,
    sales_col=None,
    menu_col=None,
    special_events_map: Optional[Dict[str, str]] = None
) -> List[Dict[str, Any]]:
    """
    Generate forecasts for all active menu items of a restaurant for target_date_str.
    """
    if special_events_map is None:
        special_events_map = {}

    active_items = list(menu_col.find({"restaurant_id": restaurant_id, "is_active": True}))
    results = []

    for item in active_items:
        dish_id = str(item["_id"])
        dish_name = item.get("dish_name", "Dish")

        # Fetch historical sales for this dish
        sales = list(sales_col.find(
            {"restaurant_id": restaurant_id, "dish_id": dish_id}
        ).sort("date", 1))

        special_event = special_events_map.get(target_date_str)

        prediction = predict_dish_demand(
            dish_id=dish_id,
            dish_name=dish_name,
            sales_records=sales,
            target_date_str=target_date_str,
            safety_margin_pct=safety_margin_pct,
            special_event=special_event,
        )
        prediction["category"] = item.get("category", "Main Course")
        prediction["price"] = item.get("price", 0.0)
        prediction["is_vegetarian"] = item.get("is_vegetarian", True)
        results.append(prediction)

    return results
