import os
import shutil
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app import models, schemas

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/posts/create", response_model=schemas.PostOut)
def create_post(
    author_id: int = Form(...),
    content: str = Form(...),
    media: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    media_url = None
    if media:
        # safe filename
        filename = Path(media.filename).name
        media_dir = os.path.join("media", "posts")
        os.makedirs(media_dir, exist_ok=True)
        path = os.path.join(media_dir, filename)

        # avoid collisions
        counter = 1
        base, ext = os.path.splitext(filename)
        while os.path.exists(path):
            filename = f"{base}_{counter}{ext}"
            path = os.path.join(media_dir, filename)
            counter += 1

        with open(path, "wb") as f:
            shutil.copyfileobj(media.file, f)

        # public URL served by route or static mount
        media_url = f"/media/posts/{filename}"

    post = models.Post(author_id=author_id, content=content, media_url=media_url)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post

@router.get("/posts", response_model=List[schemas.PostOut])
def list_posts(db: Session = Depends(get_db)):
    return db.query(models.Post).order_by(models.Post.created_at.desc()).all()

@router.post("/posts/like/{post_id}")
def like_post(post_id: int, db: Session = Depends(get_db)):
    post = db.get(models.Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    # ensure likes is numeric
    try:
        post.likes = int(getattr(post, "likes", 0)) + 1
    except Exception:
        post.likes = 1
    db.add(post)
    db.commit()
    return {"likes": post.likes}

@router.post("/stake", response_model=schemas.StakeCreate)
def stake_asset(
    user_id: int = Form(...),
    asset_type: str = Form(...),
    asset_id: int = Form(...),
    amount: float = Form(...),
    db: Session = Depends(get_db),
):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        user_balance = float(getattr(user, "balance", 0.0))
    except Exception:
        user_balance = 0.0
    if user_balance < amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    stake = models.Stake(user_id=user_id, asset_type=asset_type, asset_id=asset_id, amount=amount)
    user.balance = user_balance - amount
    db.add(stake)
    db.add(user)
    db.commit()
    db.refresh(stake)
    return stake

@router.post("/unstake/{stake_id}")
def unstake_asset(stake_id: int, db: Session = Depends(get_db)):
    stake = db.get(models.Stake, stake_id)
    if not stake:
        raise HTTPException(status_code=404, detail="Stake not found")
    user = db.get(models.User, stake.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        user.balance = float(getattr(user, "balance", 0.0)) + float(getattr(stake, "amount", 0.0))
    except Exception:
        # fallback: set to stake.amount if balance invalid
        try:
            user.balance = float(getattr(stake, "amount", 0.0))
        except Exception:
            user.balance = 0.0
    db.delete(stake)
    db.add(user)
    db.commit()
    return {"msg": "Stake removed and amount returned to user balance"} 
# --- IGNORE ---
File: app/routes/auth.py
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
def list_users(skip: int = 0, limit: int = 100, db:
    Session = Depends(get_db)):
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