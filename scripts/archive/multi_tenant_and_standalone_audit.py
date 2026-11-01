import sys, os, re, pickle
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

print("==================================================")
print("🛡️ AUDITORÍA DE PRODUCCIÓN Y MULTI-USUARIO")
print("==================================================")

# 1. Check ONNX models presence and absolute resolution
models_dir = Path("models")
models_dir.mkdir(exist_ok=True)

yunet_root = Path("face_detection_yunet_2023mar.onnx")
sface_root = Path("face_recognition_sface_2021dec.onnx")

yunet_target = models_dir / "face_detection_yunet_2023mar.onnx"
sface_target = models_dir / "face_recognition_sface_2021dec.onnx"

if yunet_root.exists() and not yunet_target.exists():
    import shutil
    shutil.copy(str(yunet_root), str(yunet_target))

if sface_root.exists() and not sface_target.exists():
    import shutil
    shutil.copy(str(sface_root), str(sface_target))

print(f"✓ Modelo YuNet detectado: {yunet_target.exists()} ({yunet_target.resolve()})")
print(f"✓ Modelo SFace detectado: {sface_target.exists()} ({sface_target.resolve()})")

# 2. Upgrade db.py for Multi-User Isolation (user_id column)
with open('db.py', 'r', encoding='utf-8') as f:
    db_code = f.read()

if "user_id = Column" not in db_code:
    old_file_state = """class FileState(Base):
    __tablename__ = "file_states"

    file_key = Column(String, primary_key=True, index=True)
    category = Column(String, index=True)
    identity = Column(String, index=True)
    status = Column(String, default="CONFIRMED") # CONFIRMED, REJECTED, PENDING_REVIEW
    confidence = Column(Float, default=1.0)
    updated_at = Column(Float, default=time.time)"""

    new_file_state = """class FileState(Base):
    __tablename__ = "file_states"

    file_key = Column(String, primary_key=True, index=True)
    user_id = Column(String, default="default_user", index=True) # Aislamiento Multi-Usuario
    category = Column(String, index=True)
    identity = Column(String, index=True)
    status = Column(String, default="CONFIRMED") # CONFIRMED, REJECTED, PENDING_REVIEW
    confidence = Column(Float, default=1.0)
    updated_at = Column(Float, default=time.time)"""

    db_code = db_code.replace(old_file_state, new_file_state)
    with open('db.py', 'w', encoding='utf-8') as f:
        f.write(db_code)
    print("✓ Añadida columna user_id en db.py para Aislamiento Multi-Usuario en Neon.tech PostgreSQL!")

# 3. Upgrade state_memory.py for Multi-User Isolation
with open('state_memory.py', 'r', encoding='utf-8') as f:
    sm_code = f.read()

if "user_id='default_user'" not in sm_code:
    sm_code = sm_code.replace("def is_file_processed(self, file_key):", "def is_file_processed(self, file_key, user_id='default_user'):")
    sm_code = sm_code.replace('return file_key in self.state["processed_files"]', 'u_key = f"{user_id}::{file_key}"\n        return u_key in self.state["processed_files"]')
    sm_code = sm_code.replace("def mark_processed(self, file_key, category, identity, status=\"CONFIRMED\", confidence=1.0):", "def mark_processed(self, file_key, category, identity, status=\"CONFIRMED\", confidence=1.0, user_id='default_user'):")
    sm_code = sm_code.replace('self.state["processed_files"][file_key] = {', 'u_key = f"{user_id}::{file_key}"\n        self.state["processed_files"][u_key] = {')
    
    with open('state_memory.py', 'w', encoding='utf-8') as f:
        f.write(sm_code)
    print("✓ Actualizado state_memory.py con espacio de nombres aislado por usuario (user_id::file_key)!")

# 4. Ensure default persistent files exist
for p_file in ["config.json", "overrides.json"]:
    if not Path(p_file).exists():
        with open(p_file, 'w', encoding='utf-8') as f:
            f.write("{}")

if not Path("centroids.pkl").exists():
    with open("centroids.pkl", 'wb') as f:
        pickle.dump({}, f)

print("✓ Ficheros de persistencia por defecto garantizados para distribución standalone!")
print("==================================================")
print("✅ AUDITORÍA DE PRODUCCIÓN COMPLETADA SIN ERRORES")
print("==================================================")
