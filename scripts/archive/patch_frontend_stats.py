import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update text
content = content.replace('Total de elementos (caras detectadas):', 'Total de fotos procesadas:')

# 2. Inject breakdown HTML rendering
new_js = '''
                    <div style="width: 100%; background-color: #333; border-radius: 10px; height: 20px; overflow: hidden;">
                        <div style="width: ${percentage}%; background-color: #30d158; height: 100%; text-align: center; font-size: 12px; line-height: 20px; color: black; font-weight: bold;">
                            ${percentage}%
                        </div>
                    </div>
                    <div style="text-align: center; font-size: 12px; color: #aaa; margin-top: 5px; margin-bottom: 20px;">Progreso de clasificación</div>
                    
                    <h3 style="color: #0a84ff; font-size: 16px; margin-bottom: 10px; border-bottom: 1px solid #333; padding-bottom: 5px;">Desglose de Conocidos</h3>
                    <div style="max-height: 250px; overflow-y: auto; padding-right: 10px; font-size: 14px;" class="custom-scrollbar">
                        ${Object.entries(data.breakdown || {}).map(([name, count]) => `
                            <div style="display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid rgba(255,255,255,0.05);">
                                <span>${name}</span>
                                <strong style="color: #30d158;">${count}</strong>
                            </div>
                        `).join('')}
                        ${Object.keys(data.breakdown || {}).length === 0 ? '<div style="text-align: center; color: #777; font-style: italic;">No hay personas clasificadas</div>' : ''}
                    </div>
'''

content = re.sub(
    r'<div style="width: 100%; background-color: #333; border-radius: 10px; height: 20px; overflow: hidden;">.*?Progreso de clasificación</div>',
    new_js,
    content,
    flags=re.DOTALL
)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Frontend patched!")
