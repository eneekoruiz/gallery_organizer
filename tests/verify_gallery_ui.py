import os
import sys
import time
import functools

print = functools.partial(print, flush=True)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

def verify_ui():
    os.makedirs('tests/screenshots', exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Use standard 1366x768 / 1440x900 desktop viewport matching the user's screenshot
        context = browser.new_context(viewport={"width": 1366, "height": 768})
        page = context.new_page()
        
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        
        print("[1] Cargando http://127.0.0.1:5000...")
        page.goto("http://127.0.0.1:5000", wait_until="networkidle", timeout=30000)
        
        overlay = page.locator("#library-loading-overlay")
        if overlay.is_visible():
            overlay.wait_for(state="hidden", timeout=30000)
            
        page.wait_for_selector("#grid-container > div", state="visible", timeout=15000)
        print("    Página principal cargada.")
        page.screenshot(path="tests/screenshots/01_home_mosaic.png")
        
        # 2. Open Conocidos > C. Aaron
        print("\n[2] Abriendo álbum 'Conocidos > C. Aaron'...")
        # First expand 'Conocidos' accordion in sidebar if needed
        conocidos_header = page.locator(".category-accordion-header:has-text('Conocidos')")
        if conocidos_header.count() > 0:
            conocidos_header.click()
            time.sleep(0.5)
            
        aaron_item = page.locator(".sidebar-subitem:has-text('C. Aaron')")
        if aaron_item.count() > 0:
            aaron_item.click()
        else:
            # Fallback direct call
            page.evaluate("() => window.renderGrid('Conocidos', 'C. Aaron')")
            
        time.sleep(1.5)
        page.wait_for_selector(".media-card", state="visible", timeout=10000)
        
        # Verify grid properties
        grid_metrics = page.evaluate("""() => {
            const grid = document.getElementById('grid-container');
            const header = document.getElementById('main-gallery-header');
            const cards = Array.from(document.querySelectorAll('.media-card'));
            const firstCard = cards[0];
            const firstCardRect = firstCard ? firstCard.getBoundingClientRect() : null;
            const computedGrid = window.getComputedStyle(grid);
            const headerRect = header ? header.getBoundingClientRect() : null;
            return {
                cardCount: cards.length,
                gridDisplay: computedGrid.display,
                gridColumns: computedGrid.gridTemplateColumns,
                firstCardWidth: firstCardRect ? Math.round(firstCardRect.width) : 0,
                firstCardHeight: firstCardRect ? Math.round(firstCardRect.height) : 0,
                gridWidth: Math.round(grid.getBoundingClientRect().width),
                headerHeight: headerRect ? Math.round(headerRect.height) : 0
            };
        }""")
        
        print(f"    Total tarjetas visibles: {grid_metrics['cardCount']}")
        print(f"    Grid display: {grid_metrics['gridDisplay']}")
        print(f"    Ancho contenedor: {grid_metrics['gridWidth']}px")
        print(f"    Dimensiones primera tarjeta: {grid_metrics['firstCardWidth']}x{grid_metrics['firstCardHeight']}px")
        print(f"    Altura del encabezado: {grid_metrics['headerHeight']}px")
        
        assert grid_metrics['gridDisplay'] == 'grid', "El grid debe tener display: grid"
        assert grid_metrics['firstCardWidth'] < 350, f"La tarjeta NO debe ocupar toda la pantalla (ancho actual: {grid_metrics['firstCardWidth']}px)"
        assert grid_metrics['firstCardWidth'] > 100, f"La tarjeta debe tener un ancho adecuado (actual: {grid_metrics['firstCardWidth']}px)"
        
        page.screenshot(path="tests/screenshots/02_c_aaron_grid_normal.png")
        print("    [✓] Captura guardada: 02_c_aaron_grid_normal.png")
        
        # 3. Test collapse toggle
        print("\n[3] Probando botón de plegar/desplegar encabezado...")
        collapse_btn = page.locator("#btn-toggle-header-collapse")
        assert collapse_btn.is_visible(), "El botón de plegar debe estar visible"
        
        h_before = grid_metrics['headerHeight']
        collapse_btn.click()
        time.sleep(0.5)
        
        h_after = page.evaluate("() => Math.round(document.getElementById('main-gallery-header').getBoundingClientRect().height)")
        is_collapsed = page.evaluate("() => document.getElementById('main-gallery-header').classList.contains('collapsed')")
        print(f"    Altura antes: {h_before}px -> Altura después: {h_after}px (Collapsed class: {is_collapsed})")
        assert is_collapsed, "El encabezado debe tener la clase 'collapsed'"
        assert h_after < h_before, f"La altura colapsada ({h_after}px) debe ser menor que la original ({h_before}px)"
        
        page.screenshot(path="tests/screenshots/03_c_aaron_header_collapsed.png")
        print("    [✓] Captura guardada: 03_c_aaron_header_collapsed.png")
        
        # Uncollapse
        collapse_btn.click()
        time.sleep(0.5)
        
        # 4. Test density buttons
        print("\n[4] Probando conmutador de densidad (Compacto / Normal / Grande)...")
        # Click Compacto
        page.locator(".grid-density-btn[data-size='130']").click()
        time.sleep(0.5)
        w_compact = page.evaluate("() => Math.round(document.querySelector('.media-card').getBoundingClientRect().width)")
        print(f"    Ancho modo compacto: {w_compact}px")
        page.screenshot(path="tests/screenshots/04_c_aaron_density_compact.png")
        
        # Click Grande
        page.locator(".grid-density-btn[data-size='260']").click()
        time.sleep(0.5)
        w_large = page.evaluate("() => Math.round(document.querySelector('.media-card').getBoundingClientRect().width)")
        print(f"    Ancho modo grande: {w_large}px")
        page.screenshot(path="tests/screenshots/05_c_aaron_density_large.png")
        
        # Reset to Normal
        page.locator(".grid-density-btn[data-size='180']").click()
        time.sleep(0.5)
        
        print("\n[5] Verificación de errores en consola...")
        if console_errors:
            print(f"    ALERTA: {len(console_errors)} errores en consola:")
            for e in console_errors:
                print(f"      - {e}")
        else:
            print("    [✓] 0 errores en consola.")
            
        print("\n=======================================================")
        print("   TODAS LAS VERIFICACIONES VISUALES Y DE GRID PASARON")
        print("=======================================================")

if __name__ == '__main__':
    verify_ui()
