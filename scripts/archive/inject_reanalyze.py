import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

btn_code = '''
        <header style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h2 id="gallery-title">Selecciona una categoría</h2>
                <p id="gallery-subtitle" style="color: var(--text-dim); margin-top: 5px; font-size: 0.9rem;">Para ver las fotos</p>
            </div>
            <button id="btn-reanalyze" onclick="forceReanalyze()" style="display: none; padding: 10px 15px; background-color: #0a84ff; color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; transition: background 0.2s;">
                🔄 Forzar Re-Análisis (IA Actualizada)
            </button>
        </header>
'''
if '<header>' in content:
    content = re.sub(r'<header>.*?</header>', btn_code.strip(), content, flags=re.DOTALL)
    print("Injected button HTML!")
else:
    print("Could not find header")

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
    print("Injected JS!")

# Show the button only in Intelligent Cleanup
show_btn = '''
                document.getElementById('gallery-subtitle').textContent = `${currentFolderItems.length} caras pendientes encontradas`;
                document.getElementById('btn-reanalyze').style.display = 'block';
                document.getElementById('btn-reanalyze').style.opacity = '1';
                document.getElementById('btn-reanalyze').textContent = '🔄 Forzar Re-Análisis (IA Actualizada)';
                document.getElementById('btn-reanalyze').style.pointerEvents = 'auto';
'''
hide_btn = '''
            const titleEl = document.getElementById('gallery-title');
            const subEl = document.getElementById('gallery-subtitle');
            document.getElementById('btn-reanalyze').style.display = 'none';
'''

if 'document.getElementById(\'gallery-subtitle\').textContent = `${currentFolderItems.length} caras pendientes encontradas`;' in content:
    content = content.replace('document.getElementById(\'gallery-subtitle\').textContent = `${currentFolderItems.length} caras pendientes encontradas`;', show_btn)
    print("Injected show btn!")

if 'const titleEl = document.getElementById(\'gallery-title\');' in content:
    content = content.replace('const titleEl = document.getElementById(\'gallery-title\');', hide_btn)
    print("Injected hide btn!")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
