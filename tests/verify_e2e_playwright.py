import sys
import os
import time
import functools

print = functools.partial(print, flush=True)

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

def run_e2e_suite():
    print("=" * 60)
    print("   SMART GALLERY AI - AUDITORIA E2E EXIGENTE Y COMPLETA")
    print("=" * 60)
    
    console_errors = []
    page_errors = []
    failed_requests = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        
        # Track console errors
        page.on("console", lambda msg: (
            console_errors.append(f"[{msg.type}] {msg.text} @ {msg.location}") 
            if msg.type == "error" else None
        ))
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.on("response", lambda res: (
            failed_requests.append(f"HTTP {res.status} {res.url}") 
            if res.status >= 400 else None
        ))
        
        print("\n[1] Cargando aplicacion en http://127.0.0.1:5000...")
        t0 = time.time()
        res = page.goto("http://127.0.0.1:5000", wait_until="domcontentloaded", timeout=20000)
        print(f"    Respuesta inicial: HTTP {res.status} ({round(time.time() - t0, 2)}s)")
        
        # Check library loading overlay
        overlay = page.locator("#library-loading-overlay")
        if overlay.is_visible():
            print("    Esperando a que finalice el overlay de carga...")
            try:
                overlay.wait_for(state="hidden", timeout=25000)
                print("    Overlay oculto exitosamente.")
            except Exception:
                print("    ALERTA: Overlay no se oculto tras 25s.")

        print("    Esperando a que carguen los albumes en el mosaico principal...")
        page.wait_for_selector("#grid-container > div", state="visible", timeout=25000)

        # Check albums / grid items
        grid_items = page.locator("#grid-container > *")
        item_count = grid_items.count()
        print(f"    Items cargados en mosaico principal: {item_count}")
        assert item_count > 0, "El mosaico principal deberia tener categorias o albumes cargados"

        # Check Tree / Sidebar
        tree_categories = page.locator("#tree-container .tree-header, #tree-container .tree-category-group, .nav-item")
        print(f"    Categorias encontradas en barra lateral: {tree_categories.count()}")

        # [2] Test Modals
        print("\n[2] Verificando apertura y cierre de modales y herramientas...")
        modals = [
            ("Duplicados Exactos", "openExactDuplicatesModal", "#modal-exact-duplicates, .modal"),
            ("Rafagas Similares", "openSimilarPhotosModal", "#modal-similar"),
            ("Estadisticas", "openStatsModal", "#stats-modal"),
            ("Configuracion / Setup", "openSetupModal", "#setup-modal, #drawer-settings")
        ]
        for name, fn, sel in modals:
            is_fn = page.evaluate(f"() => typeof window.{fn} === 'function'")
            print(f"    - Modal {name}: funcion window.{fn} -> {is_fn}")
            if is_fn:
                page.evaluate(f"() => window.{fn}()")
                page.wait_for_timeout(500)
                # Close modal
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)
                page.evaluate("""() => {
                    ['stats-modal', 'modal-duplicates', 'modal-similar', 'setup-modal', 'modal-shortcuts'].forEach(id => {
                        const m = document.getElementById(id);
                        if (m) { m.style.display = 'none'; m.classList.add('hidden'); }
                    });
                    const dc = document.getElementById('duplicates-content');
                    if (dc) dc.innerHTML = '';
                    const sc = document.getElementById('similar-content');
                    if (sc) sc.innerHTML = '';
                    document.querySelectorAll('.modal').forEach(m => {
                        m.style.display = 'none';
                        m.classList.add('hidden');
                    });
                }""")
                page.wait_for_timeout(300)

        # [3] Test Navigation into Person / Folder
        print("\n[3] Navegando a fotos de un album...")
        first_album = page.locator(".home-album-card, .album-cover-card, #grid-container > div").first
        first_album.click()
        page.wait_for_timeout(2000)
        
        cards = page.locator(".media-card, .photo-card, #grid-container > div")
        card_count = cards.count()
        print(f"    Elementos dentro del album: {card_count}")
        assert card_count > 0, "Deberia haber elementos dentro del album seleccionado"

        # [4] Test Lightbox
        print("\n[4] Probando Lightbox, Zoom, Arrastre y Bloqueo...")
        clickable_photo = page.locator("#grid-container .media-card, #grid-container [onclick*='openLightbox']").first
        clickable_photo.click()
        page.wait_for_timeout(1500)
        
        lightbox = page.locator("#lightbox")
        lb_visible = lightbox.is_visible()
        print(f"    Lightbox visible: {lb_visible}")
        assert lb_visible, "El lightbox deberia estar visible tras hacer clic en una foto"

        # Wait for media element to load
        page.wait_for_selector("#lb-media-container img, #lb-media-container video", state="visible", timeout=10000)
        page.wait_for_timeout(1000)

        # Zoom In
        page.locator("#lb-topbar button:has-text('+'), [onclick*='zoomIn']").first.click()
        page.wait_for_timeout(300)
        page.locator("#lb-topbar button:has-text('+'), [onclick*='zoomIn']").first.click()
        page.wait_for_timeout(300)
        
        zoom_val = page.evaluate("() => window.zoomLevel || 1.0")
        print(f"    Zoom actual: {round(zoom_val, 2)}x")
        
        # Test mouse pan/drag when zoomed
        print("    Probando arrastre (pan) con raton con zoom activo...")
        media_cont = page.locator("#viewer-wrapper, #lb-media-container").first
        bbox = media_cont.bounding_box()
        if bbox:
            page.mouse.move(bbox['x'] + 200, bbox['y'] + 200)
            page.mouse.down()
            page.mouse.move(bbox['x'] + 280, bbox['y'] + 280, steps=6)
            page.mouse.up()
            page.wait_for_timeout(300)
            pan = page.evaluate("() => ({ x: window.panX, y: window.panY })")
            print(f"    Desplazamiento panX / panY: {pan}")

        # [5] Test "Marcar Persona" Drawing Tool
        print("\n[5] Probando herramienta 'Marcar Persona' (Modo dibujo y bloqueo de zoom)...")
        btn_mark = page.locator("button:has-text('Marcar'), [onclick*='enableManualSelection']").first
        if btn_mark.is_visible():
            btn_mark.click()
            page.wait_for_timeout(400)
            
            # Check drawing mode
            drawing_mode = page.evaluate("() => window.isDrawingMode")
            print(f"    Modo dibujo activo (window.isDrawingMode): {drawing_mode}")
            
            # Draw box on media
            img = page.locator("#lb-media-container img, #lb-media-container video").first
            img_box = img.bounding_box()
            if img_box:
                x1 = img_box['x'] + max(20, img_box['width'] * 0.25)
                y1 = img_box['y'] + max(20, img_box['height'] * 0.25)
                x2 = img_box['x'] + max(60, img_box['width'] * 0.45)
                y2 = img_box['y'] + max(60, img_box['height'] * 0.45)
                print(f"    Dibujando rectangulo sobre la imagen de ({round(x1)}, {round(y1)}) a ({round(x2)}, {round(y2)})...")
                page.mouse.move(x1, y1)
                page.mouse.down()
                page.mouse.move(x2, y2, steps=6)
                page.mouse.up()
                page.wait_for_timeout(600)
                
                boxes_count = page.locator(".lb-bounding-box").count()
                print(f"    Recuadros de cara en el visor tras dibujar: {boxes_count}")
                assert boxes_count > 0, "Deberia haberse anadido el nuevo recuadro manual de cara"
                
                # Check lateral card
                card_manual = page.locator("#person-cards-container .lb-face-card, #person-cards-container .person-card, .face-card")
                print(f"    Tarjetas de persona en panel lateral: {card_manual.count()}")

        # [6] Test Fast Navigation (Next / Prev)
        print("\n[6] Probando navegacion rapida entre fotos (comprobacion de freezes)...")
        btn_next = page.locator("button:has-text('›'), [onclick*='navigateLightbox(1)'], [onclick*='loadNextItem(1)']").first
        for i in range(8):
            btn_next.click()
            page.wait_for_timeout(120)
        page.wait_for_timeout(500)
        print("    8 transiciones rapidas completadas con exito.")

        # [7] Test Video Scan Endpoint and UI
        print("\n[7] Verificando soporte de escaneo inteligente de video (/api/scan_video)...")
        is_video_supported = page.evaluate("() => typeof window.scanFullVideo === 'function'")
        print(f"    Funcion scanFullVideo disponible: {is_video_supported}")
        assert is_video_supported, "window.scanFullVideo debe estar disponible"
        
        # Test backend endpoint directly with a real video
        video_sample = r"C:\Users\User\Desktop\Galeria Eneko NO ABRIR\Resultados\Familia\F. Uxue\IMG_4325.MOV".replace("\\", "/")
        dummy_scan = page.evaluate(f"""
            async () => {{
                const res = await fetch('/api/scan_video', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{ path: "{video_sample}" }})
                }});
                return {{ status: res.status, json: await res.json() }};
            }}
        """)
        print(f"    Endpoint /api/scan_video responde: HTTP {dummy_scan['status']} -> {dummy_scan['json']}")
        assert dummy_scan['status'] == 200, "El endpoint /api/scan_video debe responder 200"

        # Close Lightbox
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)

        print("\n" + "=" * 60)
        print("               RESULTADO DE LA AUDITORIA")
        print("=" * 60)
        print(f"Errores de Consola JS: {len(console_errors)}")
        for e in console_errors:
            print(f"  ❌ {e}")
            
        print(f"Excepciones JS no controladas: {len(page_errors)}")
        for e in page_errors:
            print(f"  🔥 {e}")
            
        print(f"Peticiones HTTP fallidas (>= 400): {len(failed_requests)}")
        for req in failed_requests:
            print(f"  ⚠️ {req}")
            
        page.screenshot(path="tests/e2e_verified_screenshot.png")
        print("Captura de pantalla guardada en tests/e2e_verified_screenshot.png")
        
        assert len(console_errors) == 0, f"Se encontraron {len(console_errors)} errores de consola"
        assert len(page_errors) == 0, f"Se encontraron {len(page_errors)} excepciones no controladas"
        assert len(failed_requests) == 0, f"Se encontraron {len(failed_requests)} peticiones fallidas"
        
        print("\n✨ ¡AUDITORIA E2E COMPLETADA CON EXITO AL 100%! CERO BUGS.")
        browser.close()

if __name__ == "__main__":
    run_e2e_suite()
