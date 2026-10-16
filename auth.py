"""
Authentication and Role-Based Access Control (RBAC) Module for FoodCycle
Uses pwdlib with Argon2/Bcrypt for secure hashing, and Starlette signed session cookies.
"""

from typing import Optional, Dict, Any
from bson import ObjectId
from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from pwdlib import PasswordHash
from database import get_users_collection

# Recommended hashing algorithm configuration via pwdlib
_pwd_context = PasswordHash.recommended()

SESSION_SECRET_KEY = "foodcycle-super-secret-key-sustainable-dev-sdg12-2026"


def hash_password(password: str) -> str:
    """Hash plaintext password using argon2/bcrypt."""
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plaintext password against hash."""
    try:
        return _pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Retrieve logged-in user from session, or None if unauthenticated.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    try:
        users_col = get_users_collection()
        user = users_col.find_one({"_id": ObjectId(user_id)})
        return user
    except Exception:
        return None


def login_user(request: Request, user: Dict[str, Any]):
    """Set user data in session cookie."""
    request.session["user_id"] = str(user["_id"])
    request.session["org_name"] = user.get("org_name", "")
    request.session["account_type"] = user.get("account_type", "")
    request.session["email"] = user.get("email", "")


def logout_user(request: Request):
    """Clear session data."""
    request.session.clear()


def require_auth(request: Request) -> Dict[str, Any]:
    """Dependency / guard: requires logged-in user, otherwise redirects or raises 401."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in."
        )
    return user


def require_restaurant(request: Request) -> Dict[str, Any]:
    """Dependency: ensures user is authenticated and is a restaurant."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please log in as a restaurant to access this page."
        )
    if user.get("account_type") != "restaurant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Restaurant account required."
        )
    return user


def require_ngo(request: Request) -> Dict[str, Any]:
    """Dependency: ensures user is authenticated and is an NGO."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please log in as an NGO to access this page."
        )
    if user.get("account_type") != "ngo":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: NGO account required."
        )
    return user
