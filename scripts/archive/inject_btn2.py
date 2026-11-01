import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

btn_code = '''
                <div id="person-cards-container">
                    <p style="font-size: 0.8rem; color: var(--text-dim);">Abre una foto o analiza caras para ver la lista.</p>
                </div>
                <button id="btn-ignore-unconfirmed" onclick="ignoreUnconfirmedFaces()" style="margin-top: 15px; width: 100%; padding: 10px; background-color: #ff453a; color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; display: none;">
                    🗑️ Ignorar caras no confirmadas
                </button>
'''
if '<div id="person-cards-container">' in content:
    content = re.sub(r'<div id="person-cards-container">\s*<p.*?</p>\s*</div>', btn_code.strip(), content)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Injected button!')
else:
    print('Could not find person-cards-container')
