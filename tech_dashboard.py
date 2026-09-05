#!/usr/bin/env python3
"""
Tech News Dashboard - Raspberry Pi
==================================
Servicio web para ver los resumenes del Tech News Agent con un diseño
moderno, filtros por categoria y la opcion de leer cada resumen en español.

Rutas:
    /                      -> lista de resumenes diarios (portada)
    /summary/<fecha>       -> resumen de un dia (tarjetas por noticia)
    /summary/<fecha>/raw   -> resumen en texto plano
    /summary/<fecha>/es    -> datos traducidos al español (para el toggle)
    /db                    -> historico de noticias (SQLite) con filtros
    /db/<id>               -> detalle de una noticia
    /feed                  -> RSS con los ultimos resumenes
    /health                -> estado del servicio
"""

import hashlib
import json
import os
import re
import sqlite3
import time
from datetime import datetime

from flask import Flask, abort, jsonify, render_template_string, request, Response

try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
except Exception:
    TRANSLATOR_AVAILABLE = False


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.getenv("TECH_NEWS_DATA_DIR", os.path.join(BASE_DIR, "data"))
SUMMARY_DIR = os.path.join(DATA_DIR, "resumenes")
TRANSL_DIR = os.path.join(DATA_DIR, "traducciones")
DB_PATH = os.path.join(DATA_DIR, "tech_news_history.db")

CATEGORIES = [
    "Programacion",
    "Inteligencia Artificial",
    "Ciencias de la Computacion",
    "Frameworks y Web",
    "Noticias Tech",
    "Docker / DevOps",
]

CAT_COLORS = {
    "Programacion": "#4c9aff",
    "Inteligencia Artificial": "#9f6bff",
    "Ciencias de la Computacion": "#ff8a4c",
    "Frameworks y Web": "#2dd4bf",
    "Noticias Tech": "#f43f5e",
    "Docker / DevOps": "#38bdf8",
}

app = Flask(__name__)

# ===========================================================================
#  PLANTILLA PRINCIPAL (diseño)
# ===========================================================================
LAYOUT = """
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ titulo }}</title>
<style>
  :root{
    --bg:#0b0e14; --bg2:#101525; --panel:#141a26; --panel2:#0f1420;
    --text:#e6e9f0; --muted:#9aa3b5; --muted2:#6b7488;
    --border:#232b3b; --border2:#333d52;
    --accent:#6da9ff; --accent2:#9f6bff; --link:#7cb4ff;
    --radius:14px;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  html{scroll-behavior:smooth}
  body{
    font:15px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",sans-serif;
    background:
      radial-gradient(900px 500px at 85% -10%, rgba(99,91,255,.14), transparent 60%),
      radial-gradient(700px 420px at -10% 10%, rgba(0,180,255,.10), transparent 55%),
      var(--bg);
    color:var(--text); min-height:100vh;
  }
  a{color:var(--link);text-decoration:none}
  a:hover{text-decoration:underline}
  .wrap{max-width:1000px;margin:0 auto;padding:0 18px}

  /* Header */
  header{
    background:rgba(11,14,20,.82); backdrop-filter:blur(12px);
    border-bottom:1px solid var(--border); position:sticky; top:0; z-index:20;
  }
  .bar{display:flex; align-items:center; justify-content:space-between; padding:14px 0; gap:12px; flex-wrap:wrap}
  .logo{display:flex; align-items:center; gap:10px}
  .logo-mark{
    width:34px;height:34px;border-radius:9px; display:grid; place-items:center;
    background:linear-gradient(135deg,var(--accent),var(--accent2));
    color:#0b0e14;font-weight:800;font-size:17px; letter-spacing:-1px; box-shadow:0 4px 14px rgba(99,120,255,.35);
  }
  .logo b{font-size:1.05rem; letter-spacing:.2px}
  .logo span{display:block; font-size:.72rem; color:var(--muted); font-weight:400}
  nav{display:flex; gap:6px}
  nav a{
    color:var(--muted); padding:7px 13px; border-radius:9px; font-size:.9rem;
    transition:.18s; border:1px solid transparent;
  }
  nav a:hover{color:var(--text); background:var(--panel); border-color:var(--border); text-decoration:none}
  nav a.on{color:var(--text); background:linear-gradient(135deg,rgba(109,169,255,.16),rgba(159,107,255,.16)); border-color:rgba(109,169,255,.35)}

  main{padding:26px 0 70px}

  /* Hero */
  .hero{padding:34px 4px 26px}
  .hero .kicker{
    display:inline-block; font-size:.74rem; letter-spacing:1.5px; text-transform:uppercase;
    color:var(--accent); background:rgba(109,169,255,.10); border:1px solid rgba(109,169,255,.25);
    padding:4px 11px; border-radius:20px; margin-bottom:14px;
  }
  .hero h1{font-size:clamp(1.6rem,4vw,2.3rem); font-weight:800; letter-spacing:-.5px; line-height:1.15}
  .hero p{color:var(--muted); margin-top:10px; max-width:640px}
  .stats{display:flex; gap:10px; flex-wrap:wrap; margin-top:20px}
  .stat{
    background:var(--panel); border:1px solid var(--border); border-radius:12px; padding:12px 16px; min-width:120px;
  }
  .stat b{display:block; font-size:1.35rem; color:var(--accent); letter-spacing:-.5px}
  .stat span{font-size:.78rem; color:var(--muted)}

  /* Titulos de seccion */
  h2.sec{display:flex; align-items:center; gap:10px; font-size:1.05rem; margin:30px 0 14px; letter-spacing:.2px}
  h2.sec .dot{width:9px;height:9px;border-radius:50%; display:inline-block}

  /* Cards genericas (portada de dias) */
  .grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:14px}
  .day{
    background:var(--panel); border:1px solid var(--border); border-radius:var(--radius);
    padding:18px; position:relative; overflow:hidden; transition:.18s;
  }
  .day:hover{transform:translateY(-2px); border-color:rgba(109,169,255,.4); background:var(--panel2)}
  .day .fecha{font-size:1.15rem; font-weight:700}
  .day .dow{color:var(--muted); font-size:.82rem; margin-top:2px}
  .day .n{display:inline-block; margin-top:12px; font-size:.78rem; color:var(--accent);
          background:rgba(109,169,255,.10); border-radius:18px; padding:3px 10px}
  .day .go{position:absolute; top:16px; right:16px; color:var(--muted); font-size:1.15rem}
  .day:hover .go{color:var(--accent)}

  /* Tarjeta de noticia */
  .item{
    background:var(--panel); border:1px solid var(--border); border-radius:var(--radius);
    padding:18px 20px; margin-bottom:14px; transition:border-color .18s;
  }
  .item:hover{border-color:var(--border2)}
  .item .row{display:flex; gap:12px; align-items:flex-start}
  .item .score{
    flex:0 0 auto; width:40px; height:40px; border-radius:11px; display:grid; place-items:center;
    font-weight:700; font-size:.95rem; border:2px solid var(--cat); color:var(--cat);
    background:rgba(255,255,255,.03);
  }
  .item h3{font-size:1.02rem; font-weight:650; line-height:1.35; letter-spacing:.1px}
  .item h3 a{color:var(--text)}
  .item .meta{color:var(--muted2); font-size:.78rem; margin-top:6px; display:flex; gap:8px; flex-wrap:wrap; align-items:center}
  .item .meta .cat{color:var(--cat)}
  .item .summ{color:var(--muted); margin-top:10px; font-size:.92rem; line-height:1.6}
  .item .summ.clamp{display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden}
  .item .tags{margin-top:10px; display:flex; flex-wrap:wrap; gap:6px}
  .tag{font-size:.7rem; color:var(--muted); background:rgba(255,255,255,.05); border:1px solid var(--border);
       border-radius:20px; padding:2px 9px}
  .item .foot{display:flex; align-items:center; justify-content:space-between; margin-top:12px}
  .more{color:var(--accent); font-size:.8rem; cursor:pointer; border:none; background:none; padding:0}
  .more:hover{text-decoration:underline}
  .open{
    display:inline-flex; align-items:center; gap:6px; font-size:.8rem; color:var(--text);
    background:rgba(109,169,255,.12); border:1px solid rgba(109,169,255,.35); border-radius:8px; padding:6px 12px; transition:.15s;
  }
  .open:hover{background:rgba(109,169,255,.22); text-decoration:none}

  /* Barra de herramientas del resumen */
  .toolbar{
    display:flex; align-items:center; justify-content:space-between; gap:10px; flex-wrap:wrap;
    background:var(--panel); border:1px solid var(--border); border-radius:var(--radius); padding:12px 16px; margin-bottom:20px;
  }
  .toolbar .btns{display:flex; gap:8px; align-items:center; flex-wrap:wrap}
  .pill{
    font-size:.82rem; padding:7px 14px; border-radius:9px; cursor:pointer; border:1px solid var(--border);
    background:var(--panel2); color:var(--muted); transition:.15s;
  }
  .pill:hover{color:var(--text); border-color:#3a4a63}
  .pill.on{color:var(--text); background:linear-gradient(135deg,rgba(109,169,255,.22),rgba(159,107,255,.22)); border-color:rgba(109,169,255,.5)}
  .state{padding:7px 12px; font-size:.78rem}
  .state.busy{color:var(--accent)}
  .state.err{color:#ff6b6b}
  .state.ok{color:#4ade80}

  /* Anchors de categorias */
  .anchors{display:flex; gap:8px; flex-wrap:wrap; margin-bottom:22px}
  .anchors a{
    font-size:.78rem; color:var(--muted); border:1px solid var(--border); border-radius:20px; padding:4px 12px;
  }
  .anchors a:hover{color:var(--text); border-color:var(--border2); text-decoration:none}
  .anchors a i{display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:6px}

  /* Filtros del historial */
  .filters{display:flex; gap:8px; flex-wrap:wrap; margin-bottom:16px; align-items:center}
  select,input,button{
    background:var(--panel2); color:var(--text); border:1px solid var(--border); border-radius:9px;
    padding:9px 13px; font-size:.88rem; font-family:inherit;
  }
  button{background:linear-gradient(135deg,rgba(109,169,255,.18),rgba(159,107,255,.18)); border-color:rgba(109,169,255,.4); cursor:pointer}
  button:hover{border-color:rgba(109,169,255,.7)}
  .count{color:var(--muted2); font-size:.8rem; margin-bottom:14px}

  .pager{display:flex; justify-content:center; align-items:center; gap:16px; margin-top:22px; color:var(--muted); font-size:.85rem}

  /* Detalle */
  .detail{background:var(--panel); border:1px solid var(--border); border-radius:var(--radius); padding:26px}
  .detail h1{font-size:1.35rem; line-height:1.4; letter-spacing:-.2px}
  .detail .meta{color:var(--muted); font-size:.83rem; margin:12px 0}
  .detail p{color:var(--muted); line-height:1.7}
  .detail .actions{margin-top:18px; display:flex; gap:10px}

  /* Enlace cruda */
  pre.raw{
    background:var(--panel2); border:1px solid var(--border); border-radius:var(--radius);
    padding:20px; font-size:.86rem; line-height:1.55; white-space:pre-wrap; word-wrap:break-word;
    color:#cdd5e1; max-height:70vh; overflow:auto;
  }

  .empty{color:var(--muted); text-align:center; padding:46px 0}
  footer{text-align:center; color:var(--muted2); font-size:.78rem; padding-bottom:36px}
  .es-note{font-size:.76rem; color:var(--muted2); margin-top:6px}
  .spin{display:inline-block; width:12px; height:12px; border:2px solid var(--border); border-top-color:var(--accent);
        border-radius:50%; animation:rot .7s linear infinite; vertical-align:-2px; margin-right:6px}
  @keyframes rot{to{transform:rotate(360deg)}}
  @media (max-width:600px){ .bar{flex-direction:column; align-items:flex-start} nav{width:100%} nav a{flex:1; text-align:center} }
</style>
</head>
<body>
<header>
  <div class="wrap bar">
    <a class="logo" href="/" style="color:var(--text)">
      <div class="logo-mark">T</div>
      <div><b>Tech Agent</b><span>Ingenieria de Software · Raspberry Pi</span></div>
    </a>
    <nav>
      <a href="/" class="{{ 'on' if nav=='inicio' else '' }}">Resumenes</a>
      <a href="/db" class="{{ 'on' if nav=='db' else '' }}">Historial</a>
      <a href="/feed" target="_blank">RSS</a>
    </nav>
  </div>
</header>
<main class="wrap">
{{ contenido }}
</main>
<footer>Tech News Agent &middot; Raspberry Pi &middot; actualizado por el cron diario a las 08:00</footer>
</body>
</html>
"""


def page(contenido: str, titulo: str, nav: str = "inicio") -> str:
    html = LAYOUT.replace("{{ contenido }}", contenido)
    html = html.replace("{{ titulo }}", titulo)
    html = html.replace("{{ 'on' if nav=='inicio' else '' }}", "on" if nav == "inicio" else "")
    html = html.replace("{{ 'on' if nav=='db' else '' }}", "on" if nav == "db" else "")
    return render_template_string(html)


def esc(txt: str) -> str:
    return txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# ===========================================================================
#  HELPERS DE DATOS
# ===========================================================================
def list_summaries() -> list:
    if not os.path.isdir(SUMMARY_DIR):
        return []
    items = []
    for fname in os.listdir(SUMMARY_DIR):
        m = re.match(r"tech-resumen-(\d{4}-\d{2}-\d{2})\.(txt|json)$", fname)
        if not m:
            continue
        fecha, ext = m.group(1), m.group(2)
        path = os.path.join(SUMMARY_DIR, fname)
        entry = next((x for x in items if x["fecha"] == fecha), None)
        if entry is None:
            entry = {"fecha": fecha, "txt": None, "json": None, "mtime": datetime.fromtimestamp(os.path.getmtime(path))}
            items.append(entry)
        entry[ext] = path
        entry["mtime"] = max(entry["mtime"], datetime.fromtimestamp(os.path.getmtime(path)))
    items.sort(key=lambda x: x["fecha"], reverse=True)
    return items


def load_json_summary(fecha: str) -> dict | None:
    path = os.path.join(SUMMARY_DIR, f"tech-resumen-{fecha}.json")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def read_txt(fecha: str) -> str:
    with open(os.path.join(SUMMARY_DIR, f"tech-resumen-{fecha}.txt"), "r", encoding="utf-8") as fh:
        return fh.read()


def dia_semana(fecha: str) -> str:
    try:
        d = datetime.strptime(fecha, "%Y-%m-%d")
    except ValueError:
        return ""
    nombres = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]
    return nombres[d.weekday()]


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def item_id(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()[:12]


# ===========================================================================
#  TRADUCCION AL ESPAÑOL (con cache en disco)
# ===========================================================================
def _trans_cache_path(fecha: str) -> str:
    os.makedirs(TRANSL_DIR, exist_ok=True)
    return os.path.join(TRANSL_DIR, f"traduccion-{fecha}.json")


def _purge_old_translations(max_age_days: int = 30) -> None:
    if not os.path.isdir(TRANSL_DIR):
        return
    cutoff = time.time() - max_age_days * 86400
    for fname in os.listdir(TRANSL_DIR):
        path = os.path.join(TRANSL_DIR, fname)
        try:
            if os.path.getmtime(path) < cutoff:
                os.remove(path)
        except OSError:
            pass


CACHE_VERSION = 2


def _is_trans_failure(text: str) -> bool:
    """Detecta si el traductor devolvio una pagina de error en vez de texto."""
    if not text:
        return False
    low = text.lower()
    markers = ("that's an error", "please try again", "error 5", "error 4", "server error",
               "an error was", "error 500", "error 503", "too many requests", "internal server error")
    return any(m in low for m in markers) or text.strip().startswith("<!doctype html")


def _translate_one(translator, text: str) -> str:
    if not text or len(text.strip()) == 0:
        return text
    if "<" in text and ">" in text:
        return text  # texto con HTML: mantener original
    try:
        if len(text) > 4800:
            text = text[:4800]
        out = translator.translate(text)
        return text if _is_trans_failure(out) else out
    except Exception:
        try:
            time.sleep(1.2)
            out = translator.translate(text)
            return text if _is_trans_failure(out) else out
        except Exception:
            return text  # fallback: se deja el original


def translate_summary(fecha: str) -> dict:
    """Traduce titulos y resumenes del dia. Devuelve cache si ya existe."""
    _purge_old_translations()
    cache_path = _trans_cache_path(fecha)
    if os.path.isfile(cache_path):
        with open(cache_path, "r", encoding="utf-8") as fh:
            cached = json.load(fh)
        if cached.get("version") == CACHE_VERSION:
            return cached

    data = load_json_summary(fecha)
    if not data:
        abort(404)

    translator = GoogleTranslator(source="auto", target="es") if TRANSLATOR_AVAILABLE else None
    items_es = []
    fallback = 0

    for cat, items in data["categories"].items():
        for idx, it in enumerate(items):
            title, summary = it["title"], it["summary"]
            if translator is None:
                fallback += 1
                items_es.append({"id": item_id(title), "title_es": title, "summary_es": summary})
                continue
            title_es = _translate_one(translator, title)
            time.sleep(0.25)
            # Traducir resumen solo hasta los 10 primeros por categoria (evita excesivo trafico)
            if idx < 10:
                summary_es = _translate_one(translator, summary) if summary else ""
                time.sleep(0.25)
            else:
                summary_es = None  # cliente conserva el resumen original
            if title_es == title and summary_es == summary:
                fallback += 1
            items_es.append({"id": item_id(title), "title_es": title_es, "summary_es": summary_es})

    doc = {
        "version": CACHE_VERSION,
        "fecha": fecha,
        "translated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fallback": fallback,
        "items": items_es,
    }
    with open(cache_path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
    return doc


# ===========================================================================
#  RUTA: PORTADA
# ===========================================================================
@app.route("/")
def index():
    summaries = list_summaries()
    total_items = 0
    total_cat = 0
    for s in summaries[:10]:
        d = load_json_summary(s["fecha"])
        if d:
            total_items += d.get("total", 0)
            total_cat += len(d.get("categories", {}))

    cards = ""
    hoy = datetime.now().strftime("%Y-%m-%d")
    for s in summaries[:14]:
        d = load_json_summary(s["fecha"])
        n = d.get("total", "?") if d else "?"
        cards += f"""
        <a class="day" href="/summary/{s['fecha']}">
          <div class="fecha">{s['fecha']}</div>
          <div class="dow">{dia_semana(s['fecha'])}{' · Hoy' if s['fecha']==hoy else ''}</div>
          <span class="n">{n} noticias</span>
          <span class="go">→</span>
        </a>"""

    if not cards:
        cards = "<div class='empty'>Aun no hay resumenes.<br>Corre: <code>python3 ~/tech-news-agent/tech_news_agent.py</code></div>"

    contenido = f"""
    <section class="hero">
      <span class="kicker">Ingenieria de Software</span>
      <h1>Tu dosis diaria de<br>tecnología, IA y código</h1>
      <p>Resumenes automáticos de programación, inteligencia artificial, frameworks,
         ciencias de la computación y más. Recopilados por el agente en tu Raspberry Pi.</p>
      <div class="stats">
        <div class="stat"><b>{total_items}</b><span>noticias recopiladas</span></div>
        <div class="stat"><b>{len(summaries)}</b><span>resúmenes diarios</span></div>
        <div class="stat"><b>6</b><span>categorías</span></div>
        <div class="stat"><b>22</b><span>fuentes RSS</span></div>
      </div>
    </section>
    <h2 class="sec"><span class="dot" style="background:var(--accent)"></span>Resúmenes disponibles</h2>
    <div class="grid">{cards}</div>
    """
    return page(contenido, "Resumen de tecnología — Tech Agent")


# ===========================================================================
#  RUTA: RESUMEN DE UN DIA
# ===========================================================================
@app.route("/summary/<fecha>")
def summary_detail(fecha):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha):
        abort(400)
    data = load_json_summary(fecha)
    if not data:
        txt = os.path.join(SUMMARY_DIR, f"tech-resumen-{fecha}.txt")
        if not os.path.isfile(txt):
            abort(404)
        contenido = f"""
        <div class="toolbar">
          <div class="btns">
            <a href="/" class="pill">← Volver</a>
            <span class="pill on">{fecha}</span>
          </div>
          <a href="/summary/{fecha}/raw" class="pill">Ver texto plano</a>
        </div>
        <pre class="raw">{esc(read_txt(fecha))}</pre>"""
        return page(contenido, f"Resumen {fecha}")

    total = data.get("total", 0)
    hoy = fecha == datetime.now().strftime("%Y-%m-%d")

    anchors = ""
    for cat in data["categories"]:
        color = CAT_COLORS.get(cat, "#9aa3b5")
        anchors += f"<a href='#cat-{cat.replace(' ', '-')}'><i style='background:{color}'></i>{cat}</a>"

    secciones = ""
    js_items = []
    for cat, items in data["categories"].items():
        color = CAT_COLORS.get(cat, "#9aa3b5")
        body = ""
        for it in items:
            iid = item_id(it["title"])
            js_items.append({
                "id": iid,
                "title": it["title"],
                "summary": it["summary"] or "",
                "link": it.get("link", ""),
                "cat": cat,
                "score": it.get("score", 0),
                "tags": it.get("tags", []),
                "published": it.get("published"),
            })
            tags = "".join(f"<span class='tag'>{esc(t)}</span>" for t in it.get("tags", [])[:8])
            pub = ""
            if it.get("published"):
                pub = it["published"][:10]
            body += f"""
            <article class="item" data-id="{iid}">
              <div class="row">
                <div class="score" style="--cat:{color}">{it.get('score', 0)}</div>
                <div>
                  <h3 data-f="title">{esc(it['title'])}</h3>
                  <div class="meta">
                    <span class="cat" style="color:{color}">{esc(cat)}</span>
                    <span>{esc(pub)}</span>
                  </div>
                  <p class="summ clamp" data-f="summary">{esc(it['summary'] or '')}</p>
                  <button class="more" data-more>Leer más</button> → <button class="more" data-less style="display:none">Ver menos</button>
                </div>
              </div>
              <div class="tags">{tags}</div>
              <div class="foot">
                <span class="es-note" data-f="note"></span>
                <a class="open" target="_blank" rel="noopener" href="{esc(it['link'] or '#')}">
                  Abrir artículo
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M7 17L17 7M7 7h10v10"/></svg>
                </a>
              </div>
            </article>"""
        secciones += f"""
        <h2 class="sec" id="cat-{cat.replace(' ', '-')}">
          <span class="dot" style="background:{color}"></span>
          {cat} <span style="color:var(--muted2);font-size:.8rem;font-weight:400">({len(items)})</span>
        </h2>
        <div style="margin-bottom:8px"></div>
        {body}"""

    estado_es = "listo" if os.path.isfile(_trans_cache_path(fecha)) else ("no" if not TRANSLATOR_AVAILABLE else "pendiente")

    contenido = f"""
    <div class="toolbar">
      <div class="btns">
        <a href="/" class="pill">← Todos los resúmenes</a>
        <span class="pill on">{fecha} · {dia_semana(fecha)}{' (hoy)' if hoy else ''} · {total} noticias</span>
      </div>
      <div class="btns">
        <button id="btn-es" class="pill" onclick="traducir()" data-state="{estado_es}">Traducir a español</button>
        <a href="/summary/{fecha}/raw" class="pill">Texto plano</a>
        <button id="btn-en" class="pill" onclick="original()" style="display:none">Ver original</button>
      </div>
    </div>
    <div class="anchors">{anchors}</div>
    <div id="state" class="state" style="display:none"></div>
    {secciones}

    <script>
    const EN = {json.dumps(js_items, ensure_ascii=False)};
    let ES = null;
    function u(el){{ el.style.display='none' }}

    function espera(){{
      const s=document.getElementById('state'); s.style.display=''; s.className='state busy';
      s.innerHTML='<span class=\\'spin\\'></span> Traduciendo a español... esto puede tomar un momento. Se guardará en caché.';
    }}
    function fin(){{
      const s=document.getElementById('state'); s.style.display='none';
    }}

    async function traducir(){{
      if(ES){{ aplicar(ES); return; }}
      espera();
      try{{
        const r = await fetch('/summary/{fecha}/es');
        if(!r.ok) throw new Error(r.status);
        ES = await r.json();
        aplicar(ES);
        document.getElementById('btn-es').style.display='none';
        document.getElementById('btn-en').style.display='';
        fin();
      }}catch(e){{
        const s=document.getElementById('state'); s.style.display=''; s.className='state err';
        s.textContent='No se pudo traducir en este momento. Inténtalo de nuevo en unos segundos.';
      }}
    }}
    function original(){{
      document.querySelectorAll('[data-f]').forEach(el=>{{
        const it=EN.find(x=>x.id===el.closest('.item')?.dataset.id);
        if(!it) return;
        if(el.dataset.f==='title') el.textContent=it.title;
        if(el.dataset.f==='summary') el.textContent=it.summary||'';
        if(el.dataset.f==='note') el.textContent='';
      }});
      document.getElementById('btn-en').style.display='none';
      document.getElementById('btn-es').style.display='';
    }}
    function aplicar(es){{
      const map = Object.fromEntries(es.items.map(i=>[i.id,i]));
      document.querySelectorAll('.item').forEach(card=>{{
        const e=map[card.dataset.id]; if(!e) return;
        card.querySelector('[data-f=\\'title\\']').textContent = e.title_es;
        const sm=card.querySelector('[data-f=\\'summary\\']');
        if(e.summary_es){{ sm.textContent=e.summary_es; sm.classList.remove('clamp'); }}
        const note=card.querySelector('[data-f=\\'note\\']');
        note.textContent = e.summary_es ? 'Traducido al español' : 'Solo en inglés (título traducido)';
      }});
    }}
    document.querySelectorAll('[data-more]').forEach(b=>b.onclick=()=>{{
      const c=b.closest('.item'); c.querySelector('.summ').classList.remove('clamp');
      c.querySelector('[data-less]').style.display=''; b.style.display='none';
    }});
    document.querySelectorAll('[data-less]').forEach(b=>b.onclick=()=>{{
      const c=b.closest('.item'); c.querySelector('.summ').classList.add('clamp');
      c.querySelector('[data-more]').style.display=''; b.style.display='none';
    }});
    </script>
    """
    return page(contenido, f"Resumen {fecha}")


@app.route("/summary/<fecha>/raw")
def summary_raw(fecha):
    path = os.path.join(SUMMARY_DIR, f"tech-resumen-{fecha}.txt")
    if not os.path.isfile(path):
        abort(404)
    return Response(read_txt(fecha), mimetype="text/plain; charset=utf-8")


@app.route("/summary/<fecha>/es")
def summary_es_data(fecha):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha):
        abort(400)
    if not TRANSLATOR_AVAILABLE:
        # Sin traductor disponible: devolver "traduccion" identica para no romper el JS
        data = load_json_summary(fecha) or abort(404)
        items = [{"id": item_id(it["title"]), "title_es": it["title"], "summary_es": None}
                 for cat, lst in data["categories"].items() for it in lst]
        return jsonify({"version": CACHE_VERSION, "fecha": fecha, "fallback": len(items), "items": items})
    return jsonify(translate_summary(fecha))


# ===========================================================================
#  RUTA: HISTORIAL (SQLite)
# ===========================================================================
@app.route("/db")
def db_view():
    conn = get_db()
    cat = request.args.get("cat", "")
    q = request.args.get("q", "").strip()
    limit = min(int(request.args.get("limit", 20)), 100)
    offset = max(int(request.args.get("offset", 0)), 0)

    where, params = [], []
    if cat in CATEGORIES:
        where.append("category = ?"); params.append(cat)
    if q:
        where.append("(title LIKE ? OR summary LIKE ?)"); params += [f"%{q}%", f"%{q}%"]
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    total = conn.execute(f"SELECT COUNT(*) AS n FROM news {where_sql}", params).fetchone()["n"]
    rows = conn.execute(
        f"""SELECT id, title, link, category, score, published, summary
            FROM news {where_sql}
            ORDER BY COALESCE(published, added_at) DESC
            LIMIT ? OFFSET ?""",
        params + [limit, offset],
    ).fetchall()
    conn.close()

    select = f"""
    <form class="filters" method="get">
      <select name="cat" onchange="this.form.submit()">
        <option value="">Todas las categorías</option>
        {''.join(f"<option value='{c}' {'selected' if c==cat else ''}>{c}</option>" for c in CATEGORIES)}
      </select>
      <input type="text" name="q" value="{esc(q)}" placeholder="Buscar noticias...">
      <button type="submit">Buscar</button>
    </form>"""

    cards = ""
    for r in rows:
        color = CAT_COLORS.get(r["category"], "#9aa3b5")
        pub = (r["published"] or "-")[:10]
        cards += f"""
        <a class="item" href="/db/{r['id']}" style="display:block; text-decoration:none">
          <div class="row">
            <div class="score" style="--cat:{color}">{r['score']}</div>
            <div>
              <h3 style="color:var(--text)">{esc(r['title'])}</h3>
              <div class="meta" style="margin-top:6px">
                <span class="cat" style="color:{color}">{esc(r['category'])}</span>
                <span>{esc(pub)}</span>
              </div>
              <p class="summ">{esc((r['summary'] or '')[:180])}</p>
            </div>
          </div>
        </a>"""

    if not cards:
        cards = "<div class='empty'>Sin resultados para esa búsqueda.</div>"
    elif total > limit:
        tp = (total - 1) // limit + 1
        pg = offset // limit + 1
        def href(o):
            return f"/db?offset={o}&cat={cat}&q={q}"
        prev = href(max(0, offset - limit))
        nxt = href(min(total - limit, offset + limit))
        pager = f'<div class="pager"><a href="{prev}">← Anterior</a><span>Página {pg} de {tp}</span><a href="{nxt}">Siguiente →</a></div>'
    else:
        pager = ""

    contenido = select + f"<div class='count'>{total} noticias guardadas</div>" + cards + pager
    return page(contenido, "Historial de noticias — Tech Agent", nav="db")


@app.route("/db/<int:news_id>")
def db_detail(news_id):
    conn = get_db()
    r = conn.execute("SELECT * FROM news WHERE id = ?", (news_id,)).fetchone()
    conn.close()
    if not r:
        abort(404)
    color = CAT_COLORS.get(r["category"], "#9aa3b5")
    contenido = f"""
    <p><a href="/db" class="pill" style="display:inline-block; padding:7px 14px">← Volver al historial</a></p>
    <div class="detail" style="margin-top:14px">
      <div class="meta"><span class="cat" style="color:{color}; font-weight:600">{esc(r['category'])}</span></div>
      <h1>{esc(r['title'])}</h1>
      <div class="meta">{esc(r['published'] or 'Sin fecha')} &middot; relevancia {r['score']}</div>
      <p>{esc(r['summary'] or 'Sin descripción.')}</p>
      <div class="actions">
        <a class="open" target="_blank" rel="noopener" href="{esc(r['link'] or '#')}">Abrir artículo original →</a>
      </div>
    </div>"""
    return page(contenido, "Noticia — Tech Agent", nav="db")


# ===========================================================================
#  RUTAS VARIAS
# ===========================================================================
@app.route("/feed")
def feed():
    items = ""
    for s in list_summaries()[:10]:
        total = "?"
        d = load_json_summary(s["fecha"])
        if d:
            total = d.get("total", "?")
        items += f"""
        <item>
          <title>Resumen tecnológico {s['fecha']} ({total} noticias)</title>
          <link>http://{request.host}/summary/{s['fecha']}</link>
          <guid>http://{request.host}/summary/{s['fecha']}</guid>
          <pubDate>{s['mtime'].strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>
          <description><![CDATA[Resumen diario de tecnolog{chr(237)}a para Ingenier{chr(237)}a de Software.]]></description>
        </item>"""
    rss = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
  <title>Tech News Agent - Resúmenes</title>
  <link>http://{request.host}/</link>
  <description>Resúmenes diarios de tecnología para Ingeniería de Software</description>
  {items}
</channel>
</rss>"""
    return Response(rss, mimetype="application/rss+xml")


@app.route("/health")
def health():
    return jsonify(ok=True, resumenes=len(list_summaries()))


@app.errorhandler(404)
def not_found(_):
    return page("<div class='empty'>404 — No se encontró lo que buscabas.</div>", "404"), 404


@app.errorhandler(500)
def server_error(_):
    return page("<div class='empty'>Ocurrió un error interno.</div>", "Error"), 500


if __name__ == "__main__":
    port = int(os.getenv("TECH_NEWS_PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)