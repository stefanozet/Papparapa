"""Parent registration and login."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import (
    create_token,
    get_current_parent,
    hash_password,
    verify_password,
)

router = APIRouter(tags=["auth"])


@router.post("/auth/register", response_model=schemas.TokenOut, status_code=201)
def register(payload: schemas.RegisterIn, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.query(models.Parent).filter(models.Parent.email == email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    parent = models.Parent(email=email, password_hash=hash_password(payload.password))
    db.add(parent)
    db.commit()
    db.refresh(parent)
    return schemas.TokenOut(access_token=create_token(parent.id))


@router.post("/auth/login", response_model=schemas.TokenOut)
def login(payload: schemas.LoginIn, db: Session = Depends(get_db)):
    parent = (
        db.query(models.Parent)
        .filter(models.Parent.email == payload.email.lower())
        .first()
    )
    if not parent or not verify_password(payload.password, parent.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return schemas.TokenOut(access_token=create_token(parent.id))


@router.get("/auth/me", response_model=schemas.ParentOut)
def me(parent: models.Parent = Depends(get_current_parent)):
    return parent
