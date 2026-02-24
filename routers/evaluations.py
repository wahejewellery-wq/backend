from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import models, schemas, auth
from database import get_db

router = APIRouter(
    prefix="/evaluations",
    tags=["evaluations"],
)

@router.post("/", response_model=schemas.EvaluationOut)
def create_evaluation(
    evaluation: schemas.EvaluationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    db_evaluation = models.Evaluation(
        **evaluation.dict(),
        user_id=current_user.id
    )
    db.add(db_evaluation)
    db.commit()
    db.refresh(db_evaluation)
    return db_evaluation

@router.get("/me", response_model=List[schemas.EvaluationOut])
def read_my_evaluations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    evaluations = db.query(models.Evaluation).filter(models.Evaluation.user_id == current_user.id).all()
    return evaluations
