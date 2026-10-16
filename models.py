"""
Pydantic Models and Data Validation Schemas for FoodCycle
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, EmailStr, Field


class UserRegisterModel(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")
    org_name: str = Field(..., min_length=2, max_length=120)
    account_type: Literal["restaurant", "ngo"]
    contact_phone: str = Field(..., min_length=7, max_length=20)
    address: str = Field(..., min_length=5, max_length=250)
    city: str = Field(default="Bengaluru", max_length=50)
    pincode: str = Field(default="", max_length=12)
    # Restaurant-specific fields
    cuisine_type: Optional[str] = "Multi-cuisine"
    operating_hours: Optional[str] = "11:00 AM - 11:00 PM"
    safety_margin_pct: Optional[float] = 10.0
    # NGO-specific fields
    beneficiaries_served_daily: Optional[int] = 50
    dietary_preferences: Optional[str] = "All accepted"
    feeding_drive_details: Optional[str] = "Community kitchen & shelter distribution"


class UserLoginModel(BaseModel):
    email: EmailStr
    password: str


class MenuItemModel(BaseModel):
    dish_name: str = Field(..., min_length=2, max_length=100)
    category: str = Field(default="Main Course", max_length=50)
    price: float = Field(default=0.0, ge=0.0)
    serving_size: str = Field(default="1 portion (~350g)", max_length=60)
    is_vegetarian: bool = True
    allergens: List[str] = Field(default_factory=list)
    is_active: bool = True


class SalesRecordModel(BaseModel):
    dish_id: str
    date: str  # YYYY-MM-DD
    quantity_sold: int = Field(..., ge=0)
    quantity_produced: int = Field(..., ge=0)
    leftover_quantity: int = Field(..., ge=0)
    special_event: Optional[str] = None


class SurplusListingModel(BaseModel):
    dish_name: str = Field(..., min_length=2, max_length=120)
    food_category: str = Field(default="Prepared Meals")
    initial_quantity: int = Field(..., gt=0)
    unit: str = Field(default="servings")
    preparation_time: str  # ISO string or YYYY-MM-DDTHH:MM
    expiry_deadline: str   # ISO string or YYYY-MM-DDTHH:MM
    storage_conditions: Literal["Refrigerated (under 5°C)", "Hot Held (above 63°C)", "Room Temperature", "Frozen (-18°C)"]
    is_vegetarian: bool = True
    allergens: List[str] = Field(default_factory=list)
    pickup_address: str = Field(..., min_length=5)
    min_pickup_quantity: int = Field(default=1, ge=1)
    is_free: bool = True
    price_per_unit: float = Field(default=0.0, ge=0.0)
    notes: Optional[str] = ""


class DonationRequestModel(BaseModel):
    listing_id: str
    requested_quantity: int = Field(..., gt=0)
    pickup_time: str  # Estimated pickup time string or datetime
    notes: Optional[str] = ""


class DonationCompletionModel(BaseModel):
    request_id: str
    actual_quantity: int = Field(..., gt=0)
    beneficiaries_served: int = Field(..., ge=1)
    notes: Optional[str] = ""


class ForecastRequestModel(BaseModel):
    target_date: str  # YYYY-MM-DD
    safety_margin_pct: float = Field(default=10.0, ge=0.0, le=50.0)
