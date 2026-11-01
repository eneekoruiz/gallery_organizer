import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update openLightbox for video
old_video_ui = '''                document.getElementById('person-cards-container').innerHTML = '<p style="font-size:0.8rem; color:var(--text-dim);">Haz clic en "Analizar Caras" para escanear el fotograma.</p>';'''
new_video_ui = '''                document.getElementById('person-cards-container').innerHTML = `
                    <button class="icon-btn" id="btn-scan-video" onclick="scanFullVideo()" style="width:100%; margin-bottom:15px; background:var(--glass-bg); color:var(--text); border:1px solid rgba(255,255,255,0.1); padding:10px; border-radius:12px; font-weight:bold; cursor:pointer;">🎬 Escanear Vídeo Completo (1 fps)</button>
                    <div id="video-scan-results" style="margin-bottom:15px;"></div>
                    <hr style="border:0; border-top:1px solid rgba(255,255,255,0.1); margin:15px 0;">
                    <p style="font-size:0.8rem; color:var(--text-dim); text-align:center;">O haz clic en "Analizar Caras en Fotograma Actual" abajo para corregir manualmente el fotograma visible.</p>
                `;'''

if old_video_ui in content:
    content = content.replace(old_video_ui, new_video_ui)
    print("Patched video UI")
else:
    print("Could not find video UI")

# 2. Add scanFullVideo function
scan_js = '''
        async function scanFullVideo() {
            if (!currentFileObj || !isCurrentVideo) return;
            const btn = document.getElementById('btn-scan-video');
            const resDiv = document.getElementById('video-scan-results');
            
            btn.textContent = "⏳ Escaneando (puede tardar unos segundos)...";
            btn.style.pointerEvents = 'none';
            btn.style.opacity = '0.5';
            resDiv.innerHTML = '<div style="text-align:center;"><div class="loader-small"></div></div>';
            
            try {
                const res = await fetch('/api/scan_video', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ path: currentFileObj.path })
                });
                const data = await res.json();
                
                if (data.error) {
                    resDiv.innerHTML = `<p style="color:#ff453a;">Error: ${data.error}</p>`;
                } else if (data.detections && data.detections.length > 0) {
                    let html = '<h4 style="margin:0 0 10px 0; color:var(--text); font-size:0.9rem;">Personas Detectadas:</h4>';
                    data.detections.forEach(d => {
                        html += `<div style="background:rgba(0,0,0,0.3); padding:8px; border-radius:8px; margin-bottom:8px;">`;
                        html += `<div style="font-weight:bold; color:#0a84ff; margin-bottom:4px;">👤 ${d.identity}</div>`;
                        html += `<div style="font-size:0.8rem; color:var(--text-dim);">Segundos: `;
                        d.seconds.forEach(sec => {
                            html += `<span onclick="document.getElementById('lb-media-container').querySelector('video').currentTime = ${sec}" style="cursor:pointer; display:inline-block; padding:2px 6px; background:rgba(255,255,255,0.1); border-radius:4px; margin:2px; transition:0.2s;">${sec}s</span>`;
                        });
                        html += `</div></div>`;
                    });
                    resDiv.innerHTML = html;
                } else {
                    resDiv.innerHTML = '<p style="color:var(--text-dim); font-size:0.8rem;">No se encontraron caras conocidas en todo el vídeo.</p>';
                }
            } catch (err) {
                resDiv.innerHTML = '<p style="color:#ff453a;">Error de conexión al escanear vídeo.</p>';
            }
            
            btn.textContent = "🎬 Volver a Escanear Vídeo";
            btn.style.pointerEvents = 'auto';
            btn.style.opacity = '1';
        }
'''

if 'async function scanFullVideo()' not in content:
    # Inject it before window.onload or at the bottom of the script
    content = content.replace('</script>\n</body>', scan_js + '\n</script>\n</body>')
    print("Added scanFullVideo function")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
