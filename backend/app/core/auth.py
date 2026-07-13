from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User

# Initialize HTTPBearer security parser
# This automatically extracts 'Bearer <token>' from the HTTP Authorization header
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency that extracts the JWT token from the headers,
    validates it, and retrieves the corresponding database user.
    """
    token = credentials.credentials

    # 1. Decode the token and check signature/expiration
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials: Token is invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Extract the User ID from the subject claim
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials: Token payload is missing subject.",
        )

    # 3. Retrieve user from database
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials: User no longer exists.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is deactivated.",
        )

    # 4. Return user object so it can be injected directly into routes
    return user
