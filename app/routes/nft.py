from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app import models, schemas
import os, shutil
import mimetypes
from pathlib import Path
from typing import List, Optional

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/nfts", response_model=List[schemas.NFTOut])
def list_nfts(db: Session = Depends(get_db)):
    return db.query(models.NFT).all()

@router.post("/nfts/upload", response_model=schemas.NFTOut, status_code=status.HTTP_201_CREATED)
def upload_nft(
    name: str = Form(...),
    description: str = Form(""),
    price: float = Form(0.0),
    owner_id: Optional[int] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    media_url = None
    if file:
        # safe filename
        filename = Path(file.filename).name
        media_dir = os.path.join("media", "nfts")
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
            shutil.copyfileobj(file.file, f)

        # public URL (served by route or static mount)
        media_url = f"/media/nfts/{filename}"

    nft = models.NFT(name=name, description=description, price=price, owner_id=owner_id)
    # attach media_url if model supports it
    try:
        setattr(nft, "media_url", media_url)
    except Exception:
        pass

    db.add(nft)
    db.commit()
    db.refresh(nft)
    return nft

@router.post("/nfts/buy/{user_id}/{nft_id}", response_model=dict)
def buy_nft(user_id: int, nft_id: int, db: Session = Depends(get_db)):
    # prefer Session.get for modern SQLAlchemy
    user = db.get(models.User, user_id)
    nft = db.get(models.NFT, nft_id)
    if not user or not nft:
        raise HTTPException(status_code=404, detail="User or NFT not found")

    # safe numeric conversions
    try:
        user_balance = float(getattr(user, "balance", 0.0))
    except Exception:
        user_balance = 0.0
    try:
        nft_price = float(getattr(nft, "price", 0.0))
    except Exception:
        nft_price = 0.0

    if user_balance < nft_price:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    user.balance = user_balance - nft_price
    nft.owner_id = user.id
    db.add(user)
    db.add(nft)
    db.commit()
    db.refresh(nft)

    platform_share = float(getattr(nft, "platform_share", 0.0))
    client_share = float(getattr(nft, "client_share", 0.0))
    platform_profit = nft_price * platform_share
    client_profit = nft_price * client_share

    return {"platform_profit": platform_profit, "client_profit": client_profit}

@router.get("/media/nfts/{filename}")
def serve_nft_media(filename: str):
    safe_name = Path(filename).name
    path = os.path.join("media", "nfts", safe_name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    media_type, _ = mimetypes.guess_type(path)
    return FileResponse(path, media_type=media_type or "application/octet-stream")