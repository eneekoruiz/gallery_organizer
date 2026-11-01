import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Update source flag logic
old_logic = '''                            # Determinación estricta de la etiqueta (Dataset vs Manual vs IA)
                            if file_key in overrides and len(overrides[file_key]) > 0:
                                label = "Manual"
                            elif is_orig_dataset:
                                label = "Dataset"
                            else:
                                label = "IA"'''

new_logic = '''                            # Determinación estricta de la etiqueta (Dataset vs Manual vs IA)
                            labels = []
                            if is_orig_dataset:
                                labels.append("Dataset")
                            else:
                                labels.append("IA")
                                
                            if file_key in overrides and len(overrides[file_key]) > 0:
                                labels.append("Manual")
                                
                            label = " + ".join(labels)'''

# Some older lines might have decoding issues with the ó in Determinación
old_logic_fallback = '''                            if file_key in overrides and len(overrides[file_key]) > 0:
                                label = "Manual"
                            elif is_orig_dataset:
                                label = "Dataset"
                            else:
                                label = "IA"'''

if old_logic in content:
    content = content.replace(old_logic, new_logic)
elif old_logic_fallback in content:
    content = content.replace(old_logic_fallback, new_logic)
else:
    # Use regex
    content = re.sub(
        r'if file_key in overrides and len\(overrides\[file_key\]\) > 0:\s*label = "Manual"\s*elif is_orig_dataset:\s*label = "Dataset"\s*else:\s*label = "IA"',
        new_logic,
        content
    )

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("app.py patched!")
