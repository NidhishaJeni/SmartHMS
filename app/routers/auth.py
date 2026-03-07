"""
Authentication routes for SmartHMS.
Handles registration, login, and logout.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.utils.auth import get_password_hash, verify_password, create_access_token
from datetime import timedelta

router = APIRouter(prefix="", tags=["Authentication"])
templates = Jinja2Templates(directory="templates")

# Allowed roles for registration
ALLOWED_ROLES = ["admin", "hospital_admin", "doctor", "nurse", "lab_tech", "patient"]


@router.get("/register")
async def register_page(request: Request):
    """Render registration page."""
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle user registration."""
    # Validate inputs
    username = username.strip()
    password = password.strip()
    role = role.strip()
    
    if not username or not password:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Please provide username and password"
        })
    
    if role not in ALLOWED_ROLES:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Invalid role selected"
        })
    
    # Check if user exists
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Username already exists"
        })
    
    try:
        # Create new user
        user = User(
            username=username,
            password_hash=get_password_hash(password),
            role=role
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Redirect to login with success message
        return RedirectResponse(url=f"/login?registered=true", status_code=status.HTTP_302_FOUND)
    except Exception as e:
        db.rollback()
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": f"Registration failed: {str(e)}"
        })


@router.get("/login")
async def login_page(request: Request, registered: bool = False):
    """Render login page."""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "registered": registered
    })


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle user login."""
    username = username.strip()
    password = password.strip()
    
    # Find user
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid username or password"
        })
    
    if not user.is_active:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Your account has been deactivated"
        })
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=60)
    )
    
    # Determine redirect URL based on user role
    role_dashboard_map = {
        "patient": "/patient/dashboard",
        "doctor": "/doctor/dashboard",
        "nurse": "/nurse/dashboard",
        "lab_tech": "/lab/dashboard",
        "admin": "/admin/dashboard",
        "hospital_admin": "/admin/dashboard"
    }
    redirect_url = role_dashboard_map.get(user.role, "/")
    
    # Set cookie and redirect based on role
    response = RedirectResponse(url=f"{redirect_url}?token={access_token}", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=3600
    )
    response.set_cookie(key="user_role", value=user.role, httponly=False)
    response.set_cookie(key="username", value=user.username, httponly=False)
    
    return response


@router.get("/logout")
async def logout():
    """Handle user logout."""
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("access_token")
    response.delete_cookie("user_role")
    response.delete_cookie("username")
    return response

