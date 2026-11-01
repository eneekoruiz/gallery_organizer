import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_video_block = """                mediaEl = document.createElement('video');
                mediaEl.src = `/media?path=${encodeURIComponent(item.path)}`;
                mediaEl.controls = true;
                mediaEl.autoplay = false;
                mediaEl.preload = 'metadata';
                mediaEl.playsInline = true;
                mediaEl.className = 'lb-media-element';
                mediaEl.onloadedmetadata = () => {
                    if (window.liveScanTimestamp) {
                        mediaEl.currentTime = window.liveScanTimestamp;
                        window.liveScanTimestamp = null;
                    } else if (mediaEl.duration > 0 && (item.source.includes('IA') || item.status === 'Dudoso')) {
                        mediaEl.currentTime = mediaEl.duration / 2;
                        showToast("Mostrando el fotograma central (usado por la IA para detectar la cara).");
                    }
                };"""

new_video_block = """                mediaEl = document.createElement('video');
                mediaEl.src = `/media?path=${encodeURIComponent(item.path)}`;
                mediaEl.controls = true;
                mediaEl.autoplay = false;
                mediaEl.preload = 'auto';
                mediaEl.playsInline = true;
                mediaEl.className = 'lb-media-element';
                mediaEl.style.width = '100%';
                mediaEl.style.height = '100%';
                mediaEl.style.maxHeight = 'calc(100vh - 120px)';
                mediaEl.style.objectFit = 'contain';
                
                mediaEl.onloadedmetadata = () => {
                    if (window.liveScanTimestamp) {
                        try { mediaEl.currentTime = window.liveScanTimestamp; } catch(e){}
                        window.liveScanTimestamp = null;
                    }
                };"""

if old_video_block in content:
    content = content.replace(old_video_block, new_video_block)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched video player initialization and layout in index.html")
else:
    print("Could not find old_video_block")
