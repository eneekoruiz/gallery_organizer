import hashlib, os
from fastapi import HTTPException, Header, Depends
from db import SessionLocal, UserModel

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def register_or_login_user(email: str, password: str):
    db = SessionLocal()
    try:
        user = db.query(UserModel).filter(UserModel.email == email.lower()).first()
        p_hash = hash_password(password)
        
        if not user:
            # Register new user
            user = UserModel(email=email.lower(), password_hash=p_hash)
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"✓ Nuevo usuario registrado: {email}")
            return {"success": True, "action": "registered", "user_id": str(user.id), "email": user.email}
        else:
            if user.password_hash == p_hash:
                return {"success": True, "action": "logged_in", "user_id": str(user.id), "email": user.email}
            else:
                raise HTTPException(status_code=401, detail="Contraseña incorrecta")
    finally:
        db.close()

def get_current_user_email(x_user_email: str = Header(default="eneekoruiz@gmail.com")):
    return x_user_email
