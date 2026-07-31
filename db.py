import os, time

try:
    from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker

    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./smart_gallery_cloud.db")

    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    if "sqlite" in DATABASE_URL:
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            pool_recycle=300
        )

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()

    class FileState(Base):
        __tablename__ = "file_states"

        file_key = Column(String, primary_key=True, index=True)
        user_id = Column(String, default="default_user", index=True)
        category = Column(String, index=True)
        identity = Column(String, index=True)
        status = Column(String, default="CONFIRMED")
        confidence = Column(Float, default=1.0)
        updated_at = Column(Float, default=time.time)

    class SyncLog(Base):
        __tablename__ = "sync_logs"

        id = Column(Integer, primary_key=True, index=True, autoincrement=True)
        action = Column(String, index=True)
        details = Column(String)
        timestamp = Column(Float, default=time.time)

    class UserModel(Base):
        __tablename__ = "users"

        id = Column(Integer, primary_key=True, index=True, autoincrement=True)
        email = Column(String, unique=True, index=True)
        password_hash = Column(String)
        created_at = Column(Float, default=time.time)

    def init_db():
        try:
            Base.metadata.create_all(bind=engine)
            print("✅ Base de datos Neon.tech (PostgreSQL) inicializada correctamente.")
        except Exception as e:
            print("Error al inicializar la base de datos:", e)

    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

except ImportError:
    # Graceful local fallback if sqlalchemy is not installed in local environment
    engine = None
    SessionLocal = None
    Base = None
    def init_db(): pass
    def get_db(): yield None
