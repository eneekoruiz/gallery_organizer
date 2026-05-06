"""
ui/styles.py — Sistema de Diseño Premium
Dark theme · Masonry grid · Triage badges · BBox canvas · Log terminal
"""

PREMIUM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ── Reset ─────────────────────────────────────────────────────────────────── */
[data-testid="stAppViewContainer"] { background: #0a0c12; }
[data-testid="stSidebar"]          { background: #10121a; border-right:1px solid #1c1f2e; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.15rem; }
[data-testid="stSidebar"] .block-container { padding:1.1rem 1rem 2rem; }
.block-container { padding:1.5rem 2rem 3rem; max-width:1440px; }
*, *::before, *::after { box-sizing:border-box; }

/* ── Tipografía ─────────────────────────────────────────────────────────────── */
html,body,[class*="css"] { font-family:'Inter',system-ui,sans-serif; color:#d4d8e8; }
h1,h2,h3 { letter-spacing:-0.03em; color:#eef0f8; }

/* ── Tabs ───────────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"]  { background:#10121a; border-radius:14px; padding:4px; gap:2px; border:1px solid #1c1f2e; }
.stTabs [data-baseweb="tab"]       { border-radius:10px; color:#606880; font-weight:500; padding:8px 22px; font-size:14px; transition:all .15s; }
.stTabs [aria-selected="true"]     { background:linear-gradient(135deg,#1e2235,#252840) !important; color:#fff !important; box-shadow:0 2px 8px rgba(0,0,0,.4); }

/* ── Botones ────────────────────────────────────────────────────────────────── */
.stButton>button { border-radius:10px; font-weight:600; letter-spacing:-.01em; transition:all .15s; border:none; }
.stButton>button[kind="primary"]       { background:linear-gradient(135deg,#6366f1,#8b5cf6); color:#fff; }
.stButton>button[kind="primary"]:hover { transform:translateY(-1px); box-shadow:0 8px 24px rgba(99,102,241,.45); }
.stButton>button:not([kind])           { background:#1a1d2e; color:#a0a8c0; border:1px solid #252840; }
.stButton>button:not([kind]):hover     { background:#20233a; border-color:#353a5e; }

/* ── Metric Cards ───────────────────────────────────────────────────────────── */
.mc { background:linear-gradient(145deg,#10121a,#14172280); border:1px solid #1c1f2e; border-radius:16px; padding:20px 24px; text-align:center; transition:transform .2s,box-shadow .2s; }
.mc:hover { transform:translateY(-2px); box-shadow:0 8px 32px rgba(0,0,0,.45); }
.mc-v { font-size:34px; font-weight:800; letter-spacing:-.04em; margin:4px 0 2px; }
.mc-l { font-size:11px; font-weight:600; color:#505570; text-transform:uppercase; letter-spacing:.1em; }
.c-green  { color:#34d399; }
.c-blue   { color:#60a5fa; }
.c-amber  { color:#fbbf24; }
.c-red    { color:#f87171; }
.c-purple { color:#a78bfa; }
.c-teal   { color:#2dd4bf; }

/* ── Progress ───────────────────────────────────────────────────────────────── */
.stProgress>div>div>div { background:linear-gradient(90deg,#6366f1,#8b5cf6,#ec4899); border-radius:99px; }
.stProgress>div>div     { background:#1c1f2e; border-radius:99px; }

/* ── Log Terminal ───────────────────────────────────────────────────────────── */
.log-term { background:#080a10; border:1px solid #1c1f2e; border-radius:14px; padding:16px 20px; font-family:'JetBrains Mono','Fira Code',monospace; font-size:12px; line-height:1.8; max-height:300px; overflow-y:auto; }
.li  { color:#8be9fd; } .lw  { color:#fbbf24; } .le  { color:#f87171; }
.lp  { color:#34d399; } .ld  { color:#a78bfa; font-weight:700; }

/* ── Triage Bandejas ────────────────────────────────────────────────────────── */
.triage-header { display:flex; align-items:center; gap:10px; padding:14px 18px; border-radius:12px; margin-bottom:12px; border:1px solid; }
.triage-safe   { background:rgba(52,211,153,.08); border-color:rgba(52,211,153,.25); }
.triage-review { background:rgba(251,191,36,.08); border-color:rgba(251,191,36,.25); }
.triage-unk    { background:rgba(96,165,250,.08);  border-color:rgba(96,165,250,.2); }
.tier-badge    { border-radius:99px; padding:3px 12px; font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.08em; white-space:nowrap; }
.tb-safe       { background:rgba(52,211,153,.2); color:#34d399; }
.tb-review     { background:rgba(251,191,36,.2); color:#fbbf24; }
.tb-unk        { background:rgba(96,165,250,.2);  color:#60a5fa; }
.tb-fp         { background:rgba(248,113,113,.2); color:#f87171; }

/* ── Masonry Grid ───────────────────────────────────────────────────────────── */
.masonry { columns:4 210px; column-gap:10px; padding:4px 0; }
@media(max-width:900px)  { .masonry { columns:2 140px; } }
@media(max-width:500px)  { .masonry { columns:1; } }
.mi { break-inside:avoid; margin-bottom:10px; border-radius:14px; overflow:hidden; position:relative; cursor:pointer; border:2px solid transparent; transition:all .2s; background:#10121a; }
.mi:hover      { transform:scale(1.025); border-color:#6366f1; z-index:2; box-shadow:0 8px 32px rgba(0,0,0,.6); }
.mi.selected   { border-color:#8b5cf6; box-shadow:0 0 0 3px rgba(139,92,246,.35); }
.mi img        { width:100%; display:block; border-radius:12px; }
.mi-ov         { position:absolute; bottom:0; left:0; right:0; padding:28px 10px 10px; background:linear-gradient(transparent,rgba(0,0,0,.9)); opacity:0; transition:opacity .2s; pointer-events:none; }
.mi:hover .mi-ov { opacity:1; }
.tag-pill      { display:inline-block; border-radius:99px; padding:2px 9px; font-size:10px; font-weight:700; margin:2px 2px 0 0; }
.tp-person     { background:rgba(236,72,153,.75); color:#fff; }
.tp-object     { background:rgba(14,165,233,.75);  color:#fff; }
.tp-safe       { background:rgba(52,211,153,.75);  color:#000; }
.tp-review     { background:rgba(251,191,36,.75);  color:#000; }

/* ── Face Cards (HITL) ──────────────────────────────────────────────────────── */
.face-card { background:#10121a; border:1px solid #1c1f2e; border-radius:16px; padding:12px; text-align:center; transition:all .2s; }
.face-card:hover { border-color:#6366f1; transform:translateY(-2px); }
.face-card img   { border-radius:10px; width:100%; aspect-ratio:1; object-fit:cover; }

/* ── Búsqueda ───────────────────────────────────────────────────────────────── */
.stTextInput input { background:#10121a !important; border:1px solid #252840 !important; border-radius:12px !important; color:#eef0f8 !important; font-size:15px !important; }
.stTextInput input:focus { border-color:#6366f1 !important; box-shadow:0 0 0 3px rgba(99,102,241,.2) !important; }
[data-baseweb="select"]>div { background:#10121a !important; border-color:#252840 !important; border-radius:10px !important; }

/* ── Scrollbar ──────────────────────────────────────────────────────────────── */
::-webkit-scrollbar       { width:5px; height:5px; }
::-webkit-scrollbar-track { background:#0a0c12; }
::-webkit-scrollbar-thumb { background:#252840; border-radius:3px; }
::-webkit-scrollbar-thumb:hover { background:#353a5e; }

/* ── Misc ───────────────────────────────────────────────────────────────────── */
hr { border-color:#1c1f2e !important; }
.stAlert { border-radius:12px !important; border:none !important; }

/* ── Sidebar Help Panel ────────────────────────────────────────────────────── */
[data-testid="stSidebar"] code {
  background:#141722;
  border:1px solid #1c1f2e;
  color:#eef0f8;
  border-radius:8px;
  padding:1px 6px;
}
[data-testid="stSidebar"] .sidebar-help {
  background: linear-gradient(145deg,#10121a,#14172280);
  border:1px solid #1c1f2e;
  border-radius:16px;
  padding:14px;
  margin: 0 0 10px 0;
}
[data-testid="stSidebar"] .sidebar-help h4 {
  margin:0 0 4px 0;
  font-size:14px;
  color:#eef0f8;
}
[data-testid="stSidebar"] .sidebar-help p {
  margin:0;
  font-size:13px;
  line-height:1.55;
  color:#a6afc9;
}
</style>
"""

BBOX_SCRIPT = """
<script>
window.drawBBoxes = function(canvasId, bboxes, scaleX, scaleY) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const colors = ['#6366f1','#ec4899','#34d399','#fbbf24','#60a5fa','#f87171','#a78bfa'];
  (bboxes||[]).forEach(function(b,i){
    const c = colors[i%colors.length];
    const x1=b.left*scaleX, y1=b.top*scaleY, x2=b.right*scaleX, y2=b.bottom*scaleY;
    ctx.strokeStyle=c; ctx.lineWidth=2.5;
    ctx.strokeRect(x1,y1,x2-x1,y2-y1);
    const lbl = b.label||'?';
    ctx.font='bold 12px Inter,sans-serif';
    const tw=ctx.measureText(lbl).width;
    ctx.fillStyle=c; ctx.fillRect(x1,y1-22,tw+14,22);
    ctx.fillStyle='#fff'; ctx.fillText(lbl,x1+7,y1-6);
  });
};
</script>
"""


# ── Helpers de render ─────────────────────────────────────────────────────────
def mc(label: str, value, css: str = "") -> str:
    return (
        f'<div class="mc"><div class="mc-l">{label}</div>'
        f'<div class="mc-v {css}">{value}</div></div>'
    )


LOG_CSS = {"INFO": "li", "WARNING": "lw", "ERROR": "le", "PROCESS": "lp", "DONE": "ld"}
LOG_ICO = {"INFO": "ℹ", "WARNING": "⚠", "ERROR": "✗", "PROCESS": "⚙", "DONE": "✓"}


def log_line(tipo: str, msg: str) -> str:
    css = LOG_CSS.get(tipo, "li")
    ico = LOG_ICO.get(tipo, "·")
    return f'<span class="{css}">{ico} {msg}</span>'
