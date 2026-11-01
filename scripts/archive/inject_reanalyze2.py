import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

btn_code = '''
                <div style="display:flex; gap:10px;">
                    <button id="btn-reanalyze" class="premium-btn" onclick="forceReanalyze()" style="display:none; background:#0a84ff; color:white; width:auto; padding:10px 20px;">
                        🔄 Forzar Re-Análisis
                    </button>
                    <button id="btn-rename-group" class="premium-btn" onclick="renameCurrentGroup()" style="display:none; background:#30d158; color:white; width:auto; padding:10px 20px;">
'''

content = content.replace('''                <div style="display:flex; gap:10px;">
                    <button id="btn-rename-group" class="premium-btn" onclick="renameCurrentGroup()" style="display:none; background:#30d158; color:white; width:auto; padding:10px 20px;">''', btn_code)

js_code = '''
        async function forceReanalyze() {
            if (!confirm("¿Seguro que quieres forzar un re-análisis? Esto borrará la caché y tardará unos segundos, pero la IA usará su conocimiento actualizado para puntuar las caras.")) return;
            
            const btn = document.getElementById('btn-reanalyze');
            btn.style.opacity = '0.5';
            btn.textContent = 'Recalculando...';
            btn.style.pointerEvents = 'none';
            
            try {
                await fetch('/api/clear_confidence_cache', {method: 'POST'});
                await openIntelligentCleanup();
            } catch(e) {
                console.error(e);
                showToast("Error al re-analizar", true);
            }
        }
'''
if 'async function openIntelligentCleanup()' in content:
    content = content.replace('async function openIntelligentCleanup()', js_code + '\n        async function openIntelligentCleanup()')

show_btn = '''
                document.getElementById('gallery-subtitle').textContent = `${currentFolderItems.length} caras pendientes encontradas`;
                document.getElementById('btn-reanalyze').style.display = 'block';
                document.getElementById('btn-reanalyze').style.opacity = '1';
                document.getElementById('btn-reanalyze').textContent = '🔄 Forzar Re-Análisis';
                document.getElementById('btn-reanalyze').style.pointerEvents = 'auto';
'''
hide_btn = '''
            const titleEl = document.getElementById('gallery-title');
            const subEl = document.getElementById('gallery-subtitle');
            document.getElementById('btn-reanalyze').style.display = 'none';
'''

if 'document.getElementById(\'gallery-subtitle\').textContent = `${currentFolderItems.length} caras pendientes encontradas`;' in content:
    content = content.replace('document.getElementById(\'gallery-subtitle\').textContent = `${currentFolderItems.length} caras pendientes encontradas`;', show_btn)

if 'const titleEl = document.getElementById(\'gallery-title\');' in content:
    content = content.replace('const titleEl = document.getElementById(\'gallery-title\');', hide_btn)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched!")
