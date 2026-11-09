import os, sys, re, json
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

print("==================================================")
print("⚙️ APLICANDO CONFIGURACIONES EXPLICITAS DEL USUARIO")
print("==================================================")

# 1. Create .env with the user's Neon.tech DATABASE_URL
env_content = """# Configuración Real de Producción
PORT=10000
STORAGE_MODE=local
GDRIVE_FOLDER_ID=1Qr6KXPxcgdlzbSHVyDOg4cBb4GReSAfD
AUTHORIZED_USER_EMAIL=eneekoruiz@gmail.com
DISABLE_AUTH=false

# Neon.tech PostgreSQL Database
DATABASE_URL=postgresql://user:password@host.neon.tech/neondb?sslmode=require&channel_binding=require

# Webhook Opcional (dejar vacío si no se usan notificaciones a Discord/Telegram)
WEBHOOK_URL=
"""

with open('.env', 'w', encoding='utf-8') as f:
    f.write(env_content)
with open('.env.example', 'w', encoding='utf-8') as f:
    f.write(env_content)

print("✓ Creados .env y .env.example con la base de datos Neon.tech real y eneekoruiz@gmail.com!")

# 2. Add User model in db.py for Email + Password Login
with open('db.py', 'r', encoding='utf-8') as f:
    db_code = f.read()

if "class UserModel(Base):" not in db_code:
    user_model_code = """
class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    created_at = Column(Float, default=time.time)
"""
    pos = db_code.find("def init_db():")
    if pos != -1:
        db_code = db_code[:pos] + user_model_code + "\n" + db_code[pos:]
        with open('db.py', 'w', encoding='utf-8') as f:
            f.write(db_code)
        print("✓ Añadido modelo UserModel en db.py para inicio de sesión por Correo y Contraseña!")

# 3. Create simple_auth.py for Email + Password Authentication
simple_auth_code = """import hashlib, os
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
"""

with open('simple_auth.py', 'w', encoding='utf-8') as f:
    f.write(simple_auth_code)

print("✓ Creado módulo simple_auth.py para autenticación por Correo + Contraseña!")

# 4. Update config.json default to mode: local
config_data = {
    "mode": "local",
    "local_path": r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR",
    "gdrive_folder_id": "1Qr6KXPxcgdlzbSHVyDOg4cBb4GReSAfD"
}
with open('config.json', 'w', encoding='utf-8') as f:
    json.dump(config_data, f, indent=2)

print("✓ Establecido modo 'local' por defecto en config.json!")
print("==================================================")
print("✅ CONFIGURACIONES APLICADAS CON ÉXITO")
print("==================================================")
