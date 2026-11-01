import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update API stats to include breakdown
new_stats = '''def api_stats():
    global _GALLERY_CACHE
    if _GALLERY_CACHE is None:
        return jsonify({"error": "La galería aún no se ha cargado"}), 400
        
    total = 0
    clasificadas = 0
    pendientes = 0
    breakdown = {}
    
    for cat, idents in _GALLERY_CACHE.items():
        for ident, items in idents.items():
            count = len(items)
            total += count
            if cat == 'Personas Sin Nombre' or cat == 'Resultados':
                pendientes += count
            else:
                clasificadas += count
                # Build breakdown
                label = f"[{cat}] {ident}" if cat != 'Conocidos' else ident
                breakdown[label] = breakdown.get(label, 0) + count
                
    # Sort breakdown by count descending
    breakdown_sorted = dict(sorted(breakdown.items(), key=lambda item: item[1], reverse=True))
                
    return jsonify({
        "total": total,
        "clasificadas": clasificadas,
        "pendientes": pendientes,
        "breakdown": breakdown_sorted
    })'''

content = re.sub(r'def api_stats\(\):.*?return jsonify\(\{.*?"pendientes": pendientes\s*\}\)', new_stats, content, flags=re.DOTALL)

# 2. Update detector threshold
content = content.replace('detector.setScoreThreshold(0.40)', 'detector.setScoreThreshold(0.55)')

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Backend patched!")
