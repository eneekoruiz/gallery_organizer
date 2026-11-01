import re

with open('static/style.css', 'r', encoding='utf-8') as f:
    content = f.read()

stack_css = '''
/* CSS PARA APILAMIENTO DE FOTOS (MEDIA-STACK) */
.media-stack {
    position: relative;
    box-shadow: 0 4px 10px rgba(0,0,0,0.4);
    transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

/* Efecto de baraja debajo de la foto */
.media-stack::before, .media-stack::after {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: #2c2c2e;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px;
    z-index: -1;
    transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.media-stack::before {
    transform: rotate(3deg) translate(4px, 4px);
    z-index: -2;
    background-color: #1c1c1e;
}

.media-stack::after {
    transform: rotate(-2deg) translate(-4px, 2px);
    z-index: -1;
}

.media-stack:hover {
    transform: scale(1.05) translateY(-5px);
}

.media-stack:hover::before {
    transform: rotate(6deg) translate(8px, 8px);
    box-shadow: 0 5px 15px rgba(0,0,0,0.5);
}

.media-stack:hover::after {
    transform: rotate(-4deg) translate(-8px, 4px);
    box-shadow: 0 5px 15px rgba(0,0,0,0.5);
}

/* Badge especial para indicar que es un grupo */
.media-stack .badge {
    box-shadow: 0 0 10px rgba(0,0,0,0.5);
}
'''

if '/* CSS PARA APILAMIENTO DE FOTOS' not in content:
    content += '\n' + stack_css
    with open('static/style.css', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched style.css with stack effects!")
else:
    print("Already patched style.css")
