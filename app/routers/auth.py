from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models import User
from app.schemas import Token, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse)
def register(user_data : UserCreate, db:Session = Depends(get_db)):
    existing_user = (
        db.query(User)
        .filter(User.email ==user_data.email )
        .first
    )
    
    if existing_user is not None:
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    heashed_password = hash_password(user_data.password)
    
    user = User(
        email = user_data.email,
        heashed_password = heashed_password
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user







