import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.models.user import User, UserCreate, UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["authentication"]
)

# Custom Input Schemas for Login and Refresh
class LoginRequest(BaseModel):
    email: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


# ==========================================
# 1. User Registration Route
# ==========================================
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_user(request: UserCreate, db: Session = Depends(get_db)):
    """
    Registers a new user in the database and returns access + refresh tokens.
    """
    # 1. Check if the user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email is already registered."
        )
        
    # 2. Hash the raw password
    hashed_pw = get_password_hash(request.password)
    
    # 3. Create and save the new user
    new_user = User(
        email=request.email,
        hashed_password=hashed_pw
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    logger.info(f"Successfully registered new user: {new_user.email}")
    
    # 4. Generate JWT tokens for the session
    access_token = create_access_token(subject=new_user.id)
    refresh_token = create_refresh_token(subject=new_user.id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=new_user
    )


# ==========================================
# 2. User Login Route
# ==========================================
@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login_user(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticates user credentials and returns access + refresh tokens.
    """
    # 1. Look up user by email
    user = db.query(User).filter(User.email == request.email.strip().lower()).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )
        
    # 2. Verify hashed password
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is deactivated."
        )
        
    logger.info(f"User logged in successfully: {user.email}")
    
    # 3. Generate tokens
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user
    )


# ==========================================
# 3. Access Token Refresh Route
# ==========================================
@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def refresh_access_token(request: RefreshRequest, db: Session = Depends(get_db)):
    """
    Validates a refresh token and generates a new access token.
    """
    # 1. Decode refresh token
    payload = decode_token(request.refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token."
        )
        
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is missing subject payload."
        )
        
    # 2. Confirm user is still valid
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive or no longer exists."
        )
        
    # 3. Issue new tokens
    new_access_token = create_access_token(subject=user.id)
    # Re-issue a new refresh token (refresh token rotation)
    new_refresh_token = create_refresh_token(subject=user.id)
    
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        user=user
    )
