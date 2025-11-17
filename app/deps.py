from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from datetime import datetime, timedelta
from .models import Base, User
from passlib.hash import bcrypt

DB_URL = "sqlite:///./erp.db"
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

SECRET = "change_me_long_random"
ALGO = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def _ensure_columns():
    with engine.begin() as conn:
        cols = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(products)").fetchall()]
        if "photo_path" not in cols:
            conn.exec_driver_sql("ALTER TABLE products ADD COLUMN photo_path TEXT")
        if "produced_qty" not in cols:
            conn.exec_driver_sql("ALTER TABLE products ADD COLUMN produced_qty INTEGER DEFAULT 0")
        if "produced_at" not in cols:
            conn.exec_driver_sql("ALTER TABLE products ADD COLUMN produced_at DATETIME")

def init_db():
    Base.metadata.create_all(bind=engine)
    _ensure_columns()
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            db.add(User(username="admin", password_hash=bcrypt.hash("admin123"), role="admin"))
            db.commit()
    finally:
        db.close()

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_token(username: str):
    payload = {"sub": username, "exp": datetime.utcnow() + timedelta(hours=8)}
    return jwt.encode(payload, SECRET, algorithm=ALGO)

def get_user(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGO])
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = get_user(db, username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
