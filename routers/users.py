from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import os
import requests
import models, schemas, auth
from database import get_db

router = APIRouter(
    prefix="/users",
    tags=["users"],
)

@router.post("/request-otp")
def request_otp(req: schemas.OTPRequest, db: Session = Depends(get_db)):
    # Clean phone number (optional: remove spaces/dashes)
    phone = req.phone_number.strip()
    
    # Generate OTP
    otp = auth.generate_otp()
    expiry = datetime.utcnow() + timedelta(minutes=auth.OTP_EXPIRE_MINUTES)
    
    # Find existing user or create a new one
    user = db.query(models.User).filter(models.User.phone_number == phone).first()
    
    if not user:
        user = models.User(phone_number=phone, full_name=req.full_name)
        db.add(user)
    else:
        # Update full name if provided during request
        if req.full_name:
            user.full_name = req.full_name
            
    user.otp_code = otp
    user.otp_expires_at = expiry
    db.commit()
    
    # Send the SMS OTP via MSG91
    msg91_auth_key = os.getenv("MSG91_AUTH_KEY")
    msg91_template_id = os.getenv("MSG91_TEMPLATE_ID")

    if msg91_auth_key and msg91_template_id:
        try:
            # MSG91 Send OTP API endpoint
            # Note: mobile number should include the country code without the '+' sign for MSG91 (e.g., 919876543210)
            # Remove '+' if it exists to be safe
            clean_phone = phone.lstrip('+')
            url = f"https://control.msg91.com/api/v5/otp?template_id={msg91_template_id}&mobile={clean_phone}&otp={otp}"
            headers = {
                "authkey": msg91_auth_key,
                "Content-Type": "application/json"
            }
            response = requests.post(url, headers=headers, json={"OTP": otp})
            print(f"MSG91 SMS sent to {phone}. Response: {response.text}")
        except Exception as e:
            print(f"Failed to send MSG91 SMS to {phone}: {e}")
            raise HTTPException(status_code=500, detail="Failed to send OTP SMS.")
    else:
        # Fallback if MSG91 credentials are not configured
        print("-----------------------------------------")
        print("WARNING: MSG91 credentials not found in environment.")
        print(f"MOCK SMS SENT TO: {user.phone_number}")
        print(f"YOUR OTP CODE IS: 🚀 {otp} 🚀")
        print("-----------------------------------------")
    
    return {"msg": f"OTP sent successfully to {phone}"}

@router.post("/verify-otp", response_model=schemas.Token)
def verify_otp(req: schemas.OTPVerify, db: Session = Depends(get_db)):
    phone = req.phone_number.strip()
    
    user = db.query(models.User).filter(models.User.phone_number == phone).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="User not found")
        
    if not user.otp_code or user.otp_code != req.otp_code:
        raise HTTPException(status_code=400, detail="Invalid OTP code")
        
    # Check expiry but be timezone naive since we used utcnow
    if not user.otp_expires_at or user.otp_expires_at.replace(tzinfo=None) < datetime.utcnow():
         raise HTTPException(status_code=400, detail="OTP has expired")
         
    # Clear OTP
    user.otp_code = None
    user.otp_expires_at = None
    db.commit()
    
    # Issue JWT Token
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.phone_number}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=schemas.UserOut)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user
