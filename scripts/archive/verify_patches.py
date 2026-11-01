import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except: pass

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

checks = {
    'Settings button (openSetupModal)': 'openSetupModal()' in html,
    'PWA manifest link': 'manifest.json' in html,
    'Service Worker registration': 'serviceWorker' in html,
    'Semantic search function': 'semanticSearch' in html,
    'Timeline slider': 'filterTimeline' in html,
    'Leaflet.js CDN': 'leaflet' in html.lower(),
    'Map modal': 'modal-map' in html,
    'Face Evolution': 'openEvolutionModal' in html or 'evoluci' in html.lower(),
    'Quick Clean overlay': 'openQuickCleanOverlay' in html,
    'loadCategoryFilter': 'loadCategoryFilter' in html,
}

print('=== UI VERIFICATION ===')
passed = 0
for name, result in checks.items():
    status = 'PASS' if result else 'FAIL'
    if result: passed += 1
    print(f'[{status}] {name}')

print(f'\nTotal: {passed}/{len(checks)} checks passed')

# Backend checks
with open('app.py', 'r', encoding='utf-8') as f:
    py = f.read()

backend_checks = {
    'Config cache (_CONFIG_CACHE)': '_CONFIG_CACHE' in py or 'config.json' in py,
    'state_memory.mark_processed in correct': 'state_memory.mark_processed' in py,
    'memory_stats in gallery': 'memory_stats' in py,
    '/api/quick_clean endpoint': 'quick_clean' in py,
    'sanitize_display_name used': 'sanitize_display_name' in py,
    'Cache-Control header': 'Cache-Control' in py or 'cache_timeout' in py or 'max-age' in py,
}

print('\n=== BACKEND VERIFICATION ===')
bpassed = 0
for name, result in backend_checks.items():
    status = 'PASS' if result else 'FAIL'
    if result: bpassed += 1
    print(f'[{status}] {name}')

print(f'\nTotal: {bpassed}/{len(backend_checks)} checks passed')
print(f'\nGrand Total: {passed + bpassed}/{len(checks) + len(backend_checks)}')
