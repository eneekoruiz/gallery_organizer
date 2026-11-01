import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the keydown listener
pattern = re.compile(r"document\.addEventListener\('keydown', async \(e\) => \{.*?\}\);", re.DOTALL)

new_listener = '''
        document.addEventListener('keydown', async (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') return;

            const lightbox = document.getElementById('lightbox');
            const isLightboxOpen = lightbox && !lightbox.classList.contains('hidden');

            if (isLightboxOpen) {
                if (e.key === 'Escape') {
                    e.preventDefault();
                    lightbox.classList.add('hidden');
                    if (isCurrentVideo) {
                        const mediaEl = document.querySelector('.lb-media-element');
                        if (mediaEl) mediaEl.pause();
                    }
                }
                else if (e.key === 'ArrowLeft') {
                    e.preventDefault();
                    if (currentFolderItems && currentItemIndex > 0) {
                        currentItemIndex--;
                        openLightbox(currentFolderItems[currentItemIndex]);
                    }
                }
                else if (e.key === 'ArrowRight') {
                    e.preventDefault();
                    if (currentFolderItems && currentItemIndex < currentFolderItems.length - 1) {
                        currentItemIndex++;
                        openLightbox(currentFolderItems[currentItemIndex]);
                    }
                }
                return; // Stop here if lightbox is open
            }

            // Global shortcuts (if lightbox is closed)
            if (e.key === 'Delete' || e.key === 'Backspace') {
                e.preventDefault();
                // Handle global delete if needed, for now do nothing
            }
        });
'''

if pattern.search(content):
    content = pattern.sub(new_listener, content)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched keyboard listener!")
else:
    print("Could not find keydown listener.")
