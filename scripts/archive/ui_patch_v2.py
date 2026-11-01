import sys, re

try:
    sys.stdout.reconfigure(encoding='utf-8')
except: pass

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

changes = 0

# ============================================================
# FIX 1: Sanitize _rejected / undefined in JS display names
# ============================================================
sanitize_js = """
function cleanDisplayName(name) {
    if (!name) return 'Desconocido';
    return name.replace(/_rejected/g, '').replace(/_solitario/g, '').replace(/_compania/g, '').replace(/\\/rejected/g, '').replace(/\\/undefined/g, '').trim() || 'Desconocido';
}
"""

if 'cleanDisplayName' not in html:
    pos = html.find('<script>')
    if pos > 0:
        insert_pos = html.find('\n', pos)
        html = html[:insert_pos+1] + sanitize_js + html[insert_pos+1:]
        changes += 1
        print("[1] Added cleanDisplayName JS function")

# ============================================================
# FIX 2: Apply cleanDisplayName to face identity labels
# ============================================================
# Replace raw identity display with cleaned version
html = html.replace("face.identity || 'Desconocido'", "cleanDisplayName(face.identity)")
html = html.replace("f.identity || 'Desconocido'", "cleanDisplayName(f.identity)")

# Also clean in tree rendering if raw folder names leak through
html = re.sub(r"ident\.name\s*\|\|\s*ident", "cleanDisplayName(ident.name || ident)", html)
changes += 1
print("[2] Applied cleanDisplayName to face identity displays")

# ============================================================
# FIX 3: Fix sharpness 'undefined' in UI
# ============================================================
html = html.replace("sharpness + '%'", "(sharpness !== undefined && sharpness !== null ? Math.round(sharpness) + '%' : 'Calculando...')")
if "sharpness !== undefined" not in html:
    # Try alternate patterns
    html = re.sub(r"data\.sharpness\s*\+\s*'%'", "((data.sharpness != null) ? Math.round(data.sharpness) + '%' : 'N/A')", html)
changes += 1
print("[3] Fixed sharpness undefined display")

# ============================================================
# FIX 4: Add relearn cascade trigger after each correction
# ============================================================
relearn_js = """
function triggerRelearnCascade(identity) {
    if (!identity || identity === 'Falso_Positivo' || identity === 'Ignorar_Irrelevante') return;
    fetch('/api/relearn_cascade', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({identity: identity})
    })
    .then(r => r.json())
    .then(data => {
        if (data.promoted > 0) {
            showToast('🧠 Re-aprendizaje: ' + data.promoted + ' fotos promovidas de _Dudosos a ' + identity, 'success');
            loadIdentities();
        }
    })
    .catch(() => {});
}
"""

if 'triggerRelearnCascade' not in html:
    pos = html.rfind('</script>')
    if pos > 0:
        html = html[:pos] + relearn_js + "\n" + html[pos:]
        changes += 1
        print("[4] Added triggerRelearnCascade JS function")

# Now wire it into inlineCorrect success callback
# Find the success handler in inlineCorrect and add the cascade call
if 'triggerRelearnCascade' in html and 'inlineCorrect' in html:
    # After successful correction, trigger relearn
    old_success = '"success": true'
    # Find inlineCorrect function and look for success handling
    inline_pattern = r"(inlineCorrect.*?\.then\(.*?data\.success.*?)(loadIdentities)"
    html = re.sub(
        r"(data\.success\s*&&\s*data\.success\s*===?\s*true[^}]*?)(loadIdentities\(\))",
        r"\1triggerRelearnCascade(newIdentidad);\n            \2",
        html,
        count=1
    )
    changes += 1
    print("[5] Wired relearn cascade into correction success flow")

# ============================================================
# FIX 5: Add auto-classify button in sidebar
# ============================================================
auto_classify_btn = """<button onclick="autoClassifyByFilename()" class="sidebar-btn" style="background: linear-gradient(135deg, #8b5cf6, #6366f1); color: white; margin-bottom: 8px;">
    🏷️ Auto-clasificar por Nombre de Archivo
</button>
"""

auto_classify_js = """
function autoClassifyByFilename() {
    showToast('🏷️ Clasificando fotos por nombre de archivo...', 'info');
    fetch('/api/auto_classify_filename', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'})
    .then(r => r.json())
    .then(data => {
        if (data.moved > 0) {
            showToast('✅ ' + data.moved + ' archivos clasificados automáticamente', 'success');
            loadIdentities();
        } else {
            showToast('No se encontraron archivos para clasificar', 'info');
        }
    })
    .catch(e => showToast('Error: ' + e, 'error'));
}
window.autoClassifyByFilename = autoClassifyByFilename;
"""

if 'autoClassifyByFilename' not in html:
    # Add button after the Quick Clean button in sidebar
    quick_clean_pos = html.find('Modo Limpieza')
    if quick_clean_pos > 0:
        btn_end = html.find('</button>', quick_clean_pos)
        if btn_end > 0:
            html = html[:btn_end + len('</button>')] + "\n" + auto_classify_btn + html[btn_end + len('</button>'):]
    
    pos = html.rfind('</script>')
    if pos > 0:
        html = html[:pos] + auto_classify_js + "\n" + html[pos:]
    changes += 1
    print("[6] Added auto-classify by filename button and function")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\n=== {changes} UI patches applied to index.html ===")
