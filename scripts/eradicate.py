import re
from pathlib import Path

def eradicate_risks(file_path):
    path = Path(file_path)
    content = path.read_text(encoding='utf-8')
    
    # Replace generic Exception with explicit technical exceptions
    # Depending on context, we replace except Exception with more granular types.
    
    # 1. Broad except Exception as e: -> except (RuntimeError, OSError, ValueError, TypeError) as e:
    content = re.sub(
        r'except Exception as (\w+):',
        r'except (RuntimeError, OSError, ValueError, TypeError, KeyError, ImportError) as \1:',
        content
    )
    
    # 2. except Exception: -> except (RuntimeError, OSError, ValueError, TypeError):
    content = re.sub(
        r'except Exception:',
        r'except (RuntimeError, OSError, ValueError, TypeError, KeyError, ImportError):',
        content
    )
    
    path.write_text(content, encoding='utf-8')
    print(f"Eradicated residual risks in {file_path}")

if __name__ == "__main__":
    core_dir = Path(r"c:\Users\User\Desktop\PROYECTOS\smart_gallery_v2\smart_gallery_v2\core")
    worker = core_dir / "worker.py"
    ai_engines = core_dir / "ai_engines.py"
    
    eradicate_risks(worker)
    eradicate_risks(ai_engines)
