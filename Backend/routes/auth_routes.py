from fastapi import APIRouter, HTTPException, status, Depends, Form, Request, Header
from passlib.context import CryptContext
from models import User, UserCreate, UserLogin, TokenResponse, Cache
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from fastapi.responses import JSONResponse
from auth import create_access_token, create_refresh_token, decode_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from services.redis_client import redis_client
from services.session_store import store_session
from db import get_current_user
import json

router = APIRouter(tags=["Authentication"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/register", response_model=TokenResponse)
async def register(user: UserCreate):
    # Dict-based query to avoid descriptor issues in tests
    existing = await User.find_one({"username": user.username})
    if existing:
        raise HTTPException(400, detail="Email already registered")

    hashed_password = pwd_context.hash(user.password)
    # Give new users an initial credit balance
    new_user = User(username=user.username, password_hash=hashed_password, credits=Decimal("1000"))
    await new_user.insert()

    # ✅ Generate tokens
    access_token = create_access_token(data={"sub": str(new_user.id)})
    refresh_token = create_refresh_token(data={"sub": str(new_user.id)})

    # ✅ Store session
    await store_session(
        user_id=str(new_user.id),
        data={"user_id": str(new_user.id), "username": new_user.username},
        expiry_minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    username: str = Form(None),
    password: str = Form(None)
):
    
    if username and password:
        pass 
    else:
        
        data = await request.json()
        username = data.get("username")
        password = data.get("password")

    if not username or not password:
        return JSONResponse(status_code=422, content={"detail": "Username and password required"})

    # Dict-based query to avoid descriptor issues in tests
    user = await User.find_one({"username": username})
    if not user or not pwd_context.verify(password, user.password_hash):
        return JSONResponse(status_code=401, content={"detail": "Invalid credentials"})

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    await store_session(
        user_id=str(user.id),
        data={"user_id": str(user.id), "username": user.username},
        expiry_minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str):
    payload = decode_access_token(refresh_token)
    if not payload:
        raise HTTPException(401, detail="Invalid refresh token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(401, detail="Invalid refresh token")
    
    new_access = create_access_token(data={"sub": user_id})
    new_refresh = create_refresh_token(data={"sub": user_id})
    return TokenResponse(access_token=new_access, refresh_token=new_refresh)

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    redis_key = f"user_session:{current_user.id}"

    # Remove Redis session
    redis_client.delete(redis_key)

    # Remove cached DB session if present (support both async and mocked sync)
    cache_entry = Cache.find_one({"key": redis_key})
    if hasattr(cache_entry, "__await__"):
        cache_entry = await cache_entry
    if cache_entry:
        await cache_entry.delete()

    return {"message": "Logged out successfully"}
