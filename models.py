from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, nullable=True) # Optional email for profile
    otp_code = Column(String, nullable=True) # Used for OTP Login
    otp_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    evaluations = relationship("Evaluation", back_populates="user")

class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    category = Column(String)
    purity = Column(String)
    gold_weight = Column(String)
    diamond_weight = Column(String, nullable=True)
    estimated_value = Column(Float)
    image_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="evaluations")
