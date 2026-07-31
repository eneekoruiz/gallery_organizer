import os, json, time, secrets
from pathlib import Path

# Try importing SQLAlchemy for Neon.tech PostgreSQL, fallback to JSON if missing locally
try:
    from db import SessionLocal, Base, engine, Column, String, Float, Integer
    class MagicLinkModel(Base):
        __tablename__ = "magic_links"

        token = Column(String, primary_key=True, index=True)
        category = Column(String, index=True)
        identity = Column(String, index=True)
        views_count = Column(Integer, default=0)
        created_at = Column(Float, default=time.time)
        expires_at = Column(Float, nullable=True)

    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        pass
except Exception:
    SessionLocal = None

MAGIC_FILE = Path("magic_links.json")

def load_magic_links_file():
    if MAGIC_FILE.exists():
        try:
            with open(MAGIC_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {}

def save_magic_links_file(data):
    with open(MAGIC_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def create_magic_link(category: str, identity: str, duration_days: int = None):
    token = secrets.token_urlsafe(16)
    now = time.time()
    expires_at = now + (duration_days * 86400) if duration_days else None

    data = load_magic_links_file()
    data[token] = {
        "token": token,
        "category": category,
        "identity": identity,
        "views_count": 0,
        "created_at": now,
        "expires_at": expires_at
    }
    save_magic_links_file(data)

    if SessionLocal:
        try:
            db = SessionLocal()
            m_link = MagicLinkModel(
                token=token,
                category=category,
                identity=identity,
                created_at=now,
                expires_at=expires_at
            )
            db.add(m_link)
            db.commit()
            db.close()
        except Exception as e:
            print("DB save magic link note:", e)

    return token

def get_magic_link_info(token: str):
    data = load_magic_links_file()
    if token in data:
        link_info = data[token]
        if link_info.get("expires_at") and time.time() > link_info["expires_at"]:
            return None
            
        link_info["views_count"] = link_info.get("views_count", 0) + 1
        data[token] = link_info
        save_magic_links_file(data)
        return link_info
    return None

def list_active_magic_links():
    data = load_magic_links_file()
    active = []
    now = time.time()
    for token, info in data.items():
        if not info.get("expires_at") or now <= info["expires_at"]:
            active.append(info)
    return active

def revoke_magic_link(token: str):
    data = load_magic_links_file()
    if token in data:
        del data[token]
        save_magic_links_file(data)
        return True
    return False
