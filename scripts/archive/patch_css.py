import re

with open('static/style.css', 'r', encoding='utf-8') as f:
    content = f.read()

css_enhancements = '''
/* LUXURY APPLE-LEVEL ENHANCEMENTS */

/* Smoother Buttons */
button {
    transition: transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275), background 0.2s, box-shadow 0.2s !important;
}
button:active {
    transform: scale(0.95) !important;
}

/* Glassmorphism Panels */
.sidebar, .lightbox, .floating-action-bar, #stats-modal {
    background: rgba(20, 20, 22, 0.75) !important;
    backdrop-filter: blur(25px) saturate(180%) !important;
    -webkit-backdrop-filter: blur(25px) saturate(180%) !important;
    border-right: 1px solid rgba(255,255,255,0.05);
}

/* Media Cards Hover */
.media-card {
    transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275), box-shadow 0.3s !important;
    border-radius: 12px;
    overflow: hidden;
}
.media-card:hover {
    transform: scale(1.03) translateY(-4px) !important;
    box-shadow: 0 12px 30px rgba(0,0,0,0.5) !important;
    z-index: 5;
}

/* Custom Scrollbar for extreme elegance */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}
::-webkit-scrollbar-track {
    background: transparent;
}
::-webkit-scrollbar-thumb {
    background: rgba(255,255,255,0.2);
    border-radius: 10px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(255,255,255,0.4);
}

/* Better Badges */
.status-badge {
    box-shadow: 0 4px 15px rgba(0,0,0,0.4);
    backdrop-filter: blur(10px);
}
'''

if '/* LUXURY APPLE-LEVEL ENHANCEMENTS */' not in content:
    content = content + '\n' + css_enhancements
    with open('static/style.css', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched CSS enhancements!")
else:
    print("Already patched CSS.")
