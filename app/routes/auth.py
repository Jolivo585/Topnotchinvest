from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import models, schemas
from app.db import SessionLocal, engine
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
import os

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretjwtkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def get_password_hash(password):
    return pwd_context.hash(password)

@router.post("/auth/register", response_model=schemas.UserOut)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    exists = db.query(models.User).filter(models.User.email == payload.email).first()
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = models.User(email=payload.email, username=payload.username, hashed_password=get_password_hash(payload.password), demo_account=payload.demo_account)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/auth/token", response_model=schemas.Token)
def login_for_access_token(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials")
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = jwt.encode({"sub": str(user.id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}

def get_current_user_from_token(db: Session, token: str):
    from jose import JWTError
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
@router.get("/auth/me", response_model=schemas.UserOut)
def read_users_me(token: str = Depends(lambda: None), db: Session = Depends(get_db)):
    if token is None:
        raise HTTPException(status_code=401, detail="Token missing")
    user = get_current_user_from_token(db, token)
    return user
@router.post("/auth/change-password")
def change_password(old_password: str, new_password: str, token: str = Depends(lambda: None), db: Session = Depends(get_db)):
    if token is None:
        raise HTTPException(status_code=401, detail="Token missing")
    user = get_current_user_from_token(db, token)
    if not verify_password(old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Old password is incorrect")
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    return {"msg": "Password updated successfully"}
@router.post("/auth/verify-kyc")
def verify_kyc(token: str = Depends(lambda: None), db: Session = Depends(get_db)):
    if token is None:
        raise HTTPException(status_code=401, detail="Token missing")
    user = get_current_user_from_token(db, token)
    user.kyc_verified = True
    db.commit()
    return {"msg": "KYC verified successfully"}
@router.post("/auth/delete-account")
def delete_account(token: str = Depends(lambda: None), db: Session = Depends(get_db)):
    if token is None:
        raise HTTPException(status_code=401, detail="Token missing")
    user = get_current_user_from_token(db, token)
    db.delete(user)
    db.commit()
    return {"msg": "Account deleted successfully"}
@router.get("/auth/users/{user_id}", response_model=schemas.UserOut)
def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
@router.get("/auth/users/", response_model=list[schemas.UserOut])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users
@router.post("/auth/stake", response_model=schemas.StakeCreate)
def create_stake(stake: schemas.StakeCreate, token: str = Depends(lambda: None), db: Session = Depends(get_db)):
    if token is None:
        raise HTTPException(status_code=401, detail="Token missing")
    user = get_current_user_from_token(db, token)
    new_stake = models.Stake(user_id=user.id, asset_type=stake.asset_type, asset_id=stake.asset_id, amount=stake.amount)
    db.add(new_stake)
    db.commit()
    db.refresh(new_stake)
    return new_stake
@router.get("/auth/stakes/", response_model=list[schemas.StakeCreate])
def list_stakes(token: str = Depends(lambda: None), db: Session = Depends(get_db)):
    if token is None:
        raise HTTPException(status_code=401, detail="Token missing")
    user = get_current_user_from_token(db, token)
    stakes = db.query(models.Stake).filter(models.Stake.user_id == user.id).all()
    return stakes
@router.delete("/auth/stake/{stake_id}")
def delete_stake(stake_id: int, token: str = Depends(lambda: None), db: Session = Depends(get_db)):
    if token is None:
        raise HTTPException(status_code=401, detail="Token missing")
    user = get_current_user_from_token(db, token)
    stake = db.query(models.Stake).filter(models.Stake.id == stake_id, models.Stake.user_id == user.id).first()
    if not stake:
        raise HTTPException(status_code=404, detail="Stake not found")
    db.delete(stake)
    db.commit()
    return {"msg": "Stake deleted successfully"}
@router.get("/auth/stake/{stake_id}", response_model=schemas.StakeCreate)
def get_stake(stake_id: int, token: str = Depends(lambda: None), db: Session = Depends(get_db)):
    if token is None:
        raise HTTPException(status_code=401, detail="Token missing")
    user = get_current_user_from_token(db, token)
    stake = db.query(models.Stake).filter(models.Stake.id == stake_id, models.Stake.user_id == user.id).first()
    if not stake:
        raise HTTPException(status_code=404, detail="Stake not found")
    return stake
