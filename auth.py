import os
import random
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from database import get_db
import models
import schemas

SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-for-jwt-generation-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days
OTP_EXPIRE_MINUTES = 5 # 5 mins

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/verify-otp")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def generate_otp():
    # Generate a random 6 digit OTP
    return str(random.randint(100000, 999999))

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        phone_number: str = payload.get("sub")
        if phone_number is None:
            raise credentials_exception
        token_data = schemas.TokenData(phone_number=phone_number)
    except JWTError:
        raise credentials_exception
        
    user = db.query(models.User).filter(models.User.phone_number == token_data.phone_number).first()
    if user is None:
        raise credentials_exception
    return user
