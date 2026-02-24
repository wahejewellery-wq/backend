from pydantic import BaseModel, constr
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    phone_number: str
    full_name: Optional[str] = None
    email: Optional[str] = None

class OTPRequest(BaseModel):
    phone_number: str
    full_name: Optional[str] = None # Optional for new users

class OTPVerify(BaseModel):
    phone_number: str
    otp_code: str

class EvaluationBase(BaseModel):
    title: str
    category: str
    purity: str
    gold_weight: str
    diamond_weight: Optional[str] = None
    estimated_value: float
    image_url: Optional[str] = None

class EvaluationCreate(EvaluationBase):
    pass

class EvaluationOut(EvaluationBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class UserOut(UserBase):
    id: int
    created_at: datetime
    evaluations: List[EvaluationOut] = []

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    phone_number: Optional[str] = None
