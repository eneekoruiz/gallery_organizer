import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_loop_logic = '''        item['confidence'] = max_conf
        _CONFIDENCE_CACHE[file_key] = max_conf
        dirty = True
        
    if dirty:
        save_confidence_cache()'''

new_loop_logic = '''        item['confidence'] = max_conf
        _CONFIDENCE_CACHE[file_key] = max_conf
        dirty = True
        
        # Guardado incremental para no perder el progreso si tarda mucho
        if len(_CONFIDENCE_CACHE) % 10 == 0:
            save_confidence_cache()
            
    if dirty:
        save_confidence_cache()'''

if old_loop_logic in content:
    content = content.replace(old_loop_logic, new_loop_logic)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched incremental save!")
else:
    print("Could not find the exact loop logic string. Using regex...")
    content = re.sub(
        r"item\['confidence'\] = max_conf\s*_CONFIDENCE_CACHE\[file_key\] = max_conf\s*dirty = True\s*if dirty:\s*save_confidence_cache\(\)",
        new_loop_logic,
        content
    )
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched with regex!")

