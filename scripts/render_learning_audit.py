"""Render recorded learning-regression evidence; never imports the application.

Usage: python scripts/render_learning_audit.py evidence.json
The JSON records command, returncode, stdout, stderr and observations.
"""
import argparse
import html
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    data = json.loads(args.evidence.read_text(encoding="utf-8"))
    required = {"command", "returncode", "stdout", "stderr", "observations"}
    if not isinstance(data, dict) or not required.issubset(data):
        parser.error("Evidence must contain command, returncode, stdout, stderr and observations")
    if type(data["returncode"]) is not int or not isinstance(data["observations"], list):
        parser.error("returncode must be an integer and observations must be a list")
    esc = lambda value: html.escape(str(value))
    passed = data["returncode"] == 0
    observations = "".join(f"<li>{esc(item)}</li>" for item in data["observations"])
    output = esc(data["stdout"] + "\n" + data["stderr"])
    document = f"""<!doctype html>
<html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Evidencia de aprendizaje · Smart Gallery</title>
<style>
:root {{ color-scheme: light dark; --bg:#f4f5f7; --fg:#19212b; --panel:#fff; --line:#c6cbd2; --accent:#185740; }}
@media(prefers-color-scheme:dark) {{ :root {{ --bg:#15191e; --fg:#e7ecf2; --panel:#20262e; --line:#59636f; --accent:#a0ddbd; }} }}
* {{ box-sizing:border-box; }}
body {{ margin:0; padding:clamp(16px,4vw,48px); background:var(--bg); color:var(--fg); font:16px/1.55 system-ui,sans-serif; }}
main {{ max-width:1100px; margin:auto; }} h1 {{ font-size:clamp(26px,4vw,40px); line-height:1.15; margin:12px 0; }}
.status {{ color:var(--accent); font-weight:700; }} section {{ margin-top:24px; padding:20px; background:var(--panel); border:1px solid var(--line); border-radius:8px; }}
h2 {{ font-size:20px; margin:0 0 12px; }} pre {{ white-space:pre-wrap; overflow-wrap:anywhere; font-size:13px; }}
li {{ margin:8px 0; overflow-wrap:anywhere; }} code {{ overflow-wrap:anywhere; }}
</style><main>
<p>SMART GALLERY · VERIFICACIÓN LOCAL</p><h1>Contratos de aprendizaje</h1>
<p class="status">{'Pruebas ejecutadas correctamente' if passed else 'La ejecución registra fallos'} · código de salida {data['returncode']}</p>
<p>Este informe acredita las comprobaciones descritas. No mide precisión facial ni demuestra que una fotografía esté identificada correctamente.</p>
<section><h2>Observaciones y límites</h2><ul>{observations}</ul></section>
<section><h2>Comando reproducible</h2><code>{esc(data['command'])}</code></section>
<section><h2>Salida registrada sin resumir</h2><pre>{output}</pre></section>
</main></html>"""
    destination = args.evidence.with_suffix(".html")
    destination.write_text(document, encoding="utf-8")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1200, "height": 1000}, color_scheme="light")
            page.goto(destination.resolve().as_uri(), wait_until="load")
            page.screenshot(path=str(args.evidence.with_suffix(".png")), full_page=True)
        finally:
            browser.close()
    print(destination.resolve())
    print(args.evidence.with_suffix(".png").resolve())


if __name__ == "__main__":
    main()
