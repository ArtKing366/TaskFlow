import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User


bearer_scheme = HTTPBearer(auto_error=False)


SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set")

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(user_id:int) ->str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    
    payload = {
        "sub": str(user_id),
        "exp": expire,
    }
    
    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm="HS256"
    )
    
    
def decode_access_token(token: str) -> int:
    try:
        decoded = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=["HS256"]
        )

        return int(decoded["sub"])

    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")
    


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        user_id = decode_access_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user
