import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

btn_code = '''
            <div id="lb-faces-cards"></div>
            <button id="btn-ignore-unconfirmed" onclick="ignoreUnconfirmedFaces()" style="margin-top: 15px; width: 100%; padding: 10px; background-color: #ff453a; color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; display: none;">
                🗑️ Ignorar caras no confirmadas
            </button>
'''
if '<div id="lb-faces-cards"></div>' in content:
    content = content.replace('<div id="lb-faces-cards"></div>', btn_code.strip())
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Injected button!')
else:
    print('Could not find lb-faces-cards')
