#!/usr/bin/env python3
"""
Tech News Dashboard
==================================
Servicio web para ver los resumenes del Tech News Agent con un diseño
moderno, filtros por categoria y la opcion de leer cada resumen en español.

Rutas:
    /                      -> lista de resumenes diarios (portada)
    /summary/<fecha>       -> resumen de un dia (tarjetas por noticia)
    /summary/<fecha>/raw   -> resumen en texto plano
    /db                    -> historico de noticias (SQLite) con filtros
    /db/<id>               -> detalle de una noticia
    /feed                  -> RSS con los ultimos resumenes
    /health                -> estado del servicio
"""

import json
import os
import re
import sqlite3
from datetime import datetime

from flask import Flask, abort, jsonify, render_template_string, request, Response


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.getenv("TECH_NEWS_DATA_DIR", os.path.join(BASE_DIR, "data"))
SUMMARY_DIR = os.path.join(DATA_DIR, "resumenes")
DB_PATH = os.path.join(DATA_DIR, "tech_news_history.db")
SITE_URL = "https://tech.mipi.dpdns.org"

CATEGORIES = [
    "Programacion",
    "Inteligencia Artificial",
    "Ciencias de la Computacion",
    "Frameworks y Web",
    "Noticias Tech",
    "Docker / DevOps",
]

CAT_COLORS = {
    "Programacion": "#38523a",
    "Inteligencia Artificial": "#8c2e1d",
    "Ciencias de la Computacion": "#3f3a68",
    "Frameworks y Web": "#1e5f74",
    "Noticias Tech": "#8a5800",
    "Docker / DevOps": "#33465f",
}

app = Flask(__name__)

# ===========================================================================
#  IDIOMAS (interfaz ES / EN)
# ===========================================================================
L = {
    "es": {
        "nav_ini": "Resumenes",
        "nav_db": "Historial",
        "footer": "Tech News Agent · Python · Flask · actualizado por el cron diario a las 08:00",
        "hero_h1a": "Tu dosis diaria de",
        "hero_h1b": "tecnología, IA y código",
        "hero_p": "Resumenes automáticos de programación, inteligencia artificial, frameworks, ciencias de la computación y más. Recopilados por el agente en tu servidor.",
        "stat_news": "noticias recopiladas",
        "stat_summaries": "resúmenes diarios",
        "stat_categories": "categorías",
        "stat_feeds": "fuentes RSS",
        "sec_summaries": "Resúmenes disponibles",
        "empty_summaries": "Aun no hay resumenes.<br>Corre: <code>python3 ~/tech-news-agent/tech_news_agent.py</code>",
        "today": "Hoy",
        "news": "noticias",
        "title_index": "Resumen de tecnología — Tech Agent",
        "summary_title": "Resumen",
        "back_all": "Todos los resúmenes",
        "back": "Volver",
        "plain": "Texto plano",
        "view_plain": "Ver texto plano",
        "today_sfx": " (hoy)",
        "read_more": "Leer más",
        "see_less": "Ver menos",
        "open_article": "Abrir artículo",
        "all_categories": "Todas las categorías",
        "search_ph": "Buscar noticias...",
        "search_btn": "Buscar",
        "saved": "noticias guardadas",
        "empty_db": "Sin resultados para esa búsqueda.",
        "prev": "Anterior",
        "next": "Siguiente",
        "page1": "Página",
        "page2": "de",
        "title_db": "Historial de noticias — Tech Agent",
        "back_db": "Volver al historial",
        "no_date": "Sin fecha",
        "relevance": "relevancia",
        "no_desc": "Sin descripción.",
        "open_orig": "Abrir artículo original",
        "title_detail": "Noticia — Tech Agent",
        "err404": "404 — No se encontró lo que buscabas.",
        "err500": "Ocurrió un error interno.",
        "feed_title": "Tech News Agent - Resúmenes",
        "feed_desc": "Resúmenes diarios de tecnología",
        "feed_item": "Resumen tecnológico",
        "dias": ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"],
    },
    "en": {
        "nav_ini": "Summaries",
        "nav_db": "History",
        "footer": "Tech News Agent · Python · Flask · updated daily by the cron at 08:00",
        "hero_h1a": "Your daily dose of",
        "hero_h1b": "technology, AI and code",
        "hero_p": "Automated summaries of programming, artificial intelligence, frameworks, computer science and more. Collected by the agent on your server.",
        "stat_news": "news collected",
        "stat_summaries": "daily summaries",
        "stat_categories": "categories",
        "stat_feeds": "RSS feeds",
        "sec_summaries": "Available summaries",
        "empty_summaries": "No summaries yet.<br>Run: <code>python3 ~/tech-news-agent/tech_news_agent.py</code>",
        "today": "Today",
        "news": "news",
        "title_index": "Technology Digest — Tech Agent",
        "summary_title": "Summary",
        "back_all": "All summaries",
        "back": "Back",
        "plain": "Plain text",
        "view_plain": "View plain text",
        "today_sfx": " (today)",
        "read_more": "Read more",
        "see_less": "See less",
        "open_article": "Open article",
        "all_categories": "All categories",
        "search_ph": "Search news...",
        "search_btn": "Search",
        "saved": "saved news",
        "empty_db": "No results for that search.",
        "prev": "Previous",
        "next": "Next",
        "page1": "Page",
        "page2": "of",
        "title_db": "News history — Tech Agent",
        "back_db": "Back to history",
        "no_date": "No date",
        "relevance": "relevance",
        "no_desc": "No description.",
        "open_orig": "Open original article",
        "title_detail": "News — Tech Agent",
        "err404": "404 — Page not found.",
        "err500": "An internal error occurred.",
        "feed_title": "Tech News Agent - Summaries",
        "feed_desc": "Daily technology summaries",
        "feed_item": "Tech summary",
        "dias": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    },
}


# ===========================================================================
#  PLANTILLA PRINCIPAL (diseño)
# ===========================================================================
LAYOUT = """
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<title>{{ titulo }}</title>
<meta name="description" content="{{ META_DESC }}">
<meta name="robots" content="index, follow">
<meta name="theme-color" content="#f8f6f0">
<link rel="canonical" href="{{ META_URL }}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Tech News Agent">
<meta property="og:title" content="{{ titulo }}">
<meta property="og:description" content="{{ META_DESC }}">
<meta property="og:url" content="{{ META_URL }}">
<meta property="og:image" content="https://tech.mipi.dpdns.org/favicon.svg">
<meta name="twitter:card" content="summary">
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"WebSite","name":"Tech News Agent","url":"https://tech.mipi.dpdns.org"}
</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,500;6..72,600;6..72,700&display=swap" rel="stylesheet">
<style>
:root{
    --paper:#f8f6f0; --panel:#efede4;
    --ink:#20242e; --ink2:#4a5060; --ink3:#5d6475;
    --rule:#e1ded2; --rule2:#c8c3b2;
    --accent:#8f2f2a; --on-accent:#fbf6ec;
    --radius:6px;
    --font-serif:"Newsreader","Iowan Old Style","Palatino Linotype",Georgia,serif;
    --font-sans:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;
    --font-num:"JetBrains Mono",ui-monospace,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace;
  }
  *{box-sizing:border-box}
  html{scroll-behavior:smooth}
  body{
    margin:0; background:var(--paper); font-family:var(--font-sans);
    font-size:1rem; line-height:1.6; color:var(--ink); min-height:100vh;
    -webkit-font-smoothing:antialiased;
  }
  ::selection{background:color-mix(in srgb,var(--accent) 22%, transparent); color:var(--ink)}
  ::-webkit-scrollbar{width:10px; height:10px}
  ::-webkit-scrollbar-thumb{background:var(--rule2); border:2px solid var(--paper); border-radius:8px}
  ::-webkit-scrollbar-thumb:hover{background:var(--ink3)}
  ::-webkit-scrollbar-track{background:transparent}
  input,textarea{caret-color:var(--accent)}
  a{color:var(--accent); text-decoration:none; text-underline-offset:3px; text-decoration-thickness:1px}
  a:hover{text-decoration:underline}
  :is(a,button,select,input):focus-visible{outline:2px solid var(--accent); outline-offset:2px; border-radius:4px}
  .wrap{max-width:1160px;margin:0 auto;padding:0 18px}

  /* Masthead */
  header{
    background:var(--paper); border-bottom:1px solid var(--rule); position:sticky; top:0; z-index:20;
  }
  .bar{display:flex; align-items:center; justify-content:space-between; padding:13px 0; gap:12px; flex-wrap:wrap}
  .logo{display:flex; align-items:center; gap:10px}
  .logo-mark{
    width:32px;height:32px;border-radius:4px; display:grid; place-items:center;
    background:var(--ink); color:var(--paper); font-family:var(--font-serif); font-weight:700; font-size:16px;
  }
  .logo b{font-family:var(--font-serif); font-size:1.08rem; font-weight:700; letter-spacing:.01em}
  .logo span{display:block; font-size:.7rem; color:var(--ink3); font-weight:600; letter-spacing:.11em; text-transform:uppercase}
  nav{display:flex; gap:2px; align-items:center}
  nav a{
    color:var(--ink3); padding:7px 13px; border-radius:4px; font-size:.9rem; font-weight:500;
    transition:.15s; border-bottom:2px solid transparent;
  }
  nav a:hover{color:var(--ink); text-decoration:none}
  nav a.on{color:var(--ink); border-bottom-color:var(--accent)}

  main{padding:26px 0 64px}

  /* Portada */
  .hero{padding:34px 4px 6px}
  .hero h1{
    font-family:var(--font-serif); font-size:2rem; font-weight:700; letter-spacing:-.01em; line-height:1.12;
    color:var(--ink); margin:0; text-wrap:balance; position:relative; padding-bottom:16px;
  }
  .hero h1::after{content:""; position:absolute; left:0; bottom:0; width:56px; height:2px;
    background:var(--accent); animation:rule-in .6s cubic-bezier(.16,1,.3,1) both}
  @keyframes rule-in{from{width:0}}
  .hero p{color:var(--ink2); margin:14px 0 0; max-width:66ch}

  .page-title{font-family:var(--font-serif); font-size:2rem; font-weight:700; letter-spacing:-.01em;
              line-height:1.15; text-wrap:balance; margin:0 0 16px}
  .stats{display:flex; flex-wrap:wrap; margin-top:22px; padding-top:16px; border-top:1px solid var(--rule);
         column-gap:46px; row-gap:12px}
  .stat b{display:block; font-family:var(--font-num); font-size:1.5rem; font-weight:700; color:var(--ink);
          letter-spacing:-.02em; font-variant-numeric:tabular-nums}
  .stat span{font-size:.72rem; color:var(--ink3); text-transform:uppercase; letter-spacing:.1em; font-weight:600}

  h2.sec{display:flex; align-items:baseline; gap:12px; font-family:var(--font-serif); font-size:1.56rem;
         font-weight:700; letter-spacing:-.01em; margin:48px 0 16px}
  h2.sec::after{content:""; flex:1; height:1px; background:var(--rule); transform:translateY(-7px)}
  h2.sec .dot{width:8px;height:8px; border-radius:1px; align-self:center}
  h2[id]{scroll-margin-top:96px}

  /* Rejilla de dias */
  .grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(250px,1fr)); gap:14px}
  .day{
    background:var(--panel); border:1px solid var(--rule); border-radius:var(--radius); padding:18px;
    position:relative; overflow:hidden;
    box-shadow:0 1px 2px rgba(32,36,46,.05), 0 10px 24px rgba(32,36,46,.05);
    transition:border-color .18s, transform .18s, box-shadow .18s;
  }
  .day:hover{transform:translateY(-2px); border-color:var(--rule2); box-shadow:0 2px 4px rgba(32,36,46,.06), 0 16px 32px rgba(32,36,46,.09)}
  .day .fecha{font-family:var(--font-num); font-size:1.05rem; font-weight:700; color:var(--ink);
              letter-spacing:.02em; font-variant-numeric:tabular-nums}
  .day .dow{color:var(--ink3); font-size:.82rem; margin-top:2px}
  .day .n{display:inline-block; margin-top:10px; font-size:.72rem; font-family:var(--font-num); color:var(--ink2);
          border:1px solid var(--rule2); border-radius:2px; padding:2px 8px; letter-spacing:.04em}
  .day .go{position:absolute; top:14px; right:14px; color:var(--ink3); width:26px; height:26px;
          display:grid; place-items:center; border-radius:4px; border:1px solid transparent; transition:.15s}
  .day .go .arrow-r{width:14px; height:14px}
  .day:hover .go{color:var(--accent); border-color:var(--rule2)}
  .day.featured{
    grid-column:span 2; grid-row:span 2; min-height:250px; display:flex; flex-direction:column;
    justify-content:flex-end; padding:22px 24px; background:var(--paper); border-width:1px;
  }
  .day.featured::before{content:''; position:absolute; top:0; left:0; right:0; height:3px; background:var(--accent)}
  .day.featured .fecha{font-size:1.5rem}
  .day.featured .preview{display:flex; flex-direction:column; gap:0; margin-top:14px; border-top:1px solid var(--rule)}
  .day.featured .preview span{
    color:var(--ink2); font-size:.84rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
    padding:9px 0; border-bottom:1px solid var(--rule); transition:color .15s;
  }
  .day.featured:hover .preview span{color:var(--ink)}

  /* Ficha de noticia */
  .item{
    display:block; background:var(--paper); border:1px solid var(--rule); border-radius:var(--radius);
    padding:16px 18px; box-shadow:0 1px 2px rgba(32,36,46,.05);
    transition:border-color .18s, transform .18s, box-shadow .18s;
  }
  .item:hover{border-color:var(--rule2); transform:translateY(-1px); box-shadow:0 10px 24px rgba(32,36,46,.08)}
  .item .row{display:flex; gap:14px; align-items:flex-start}
  .item .score{
    flex:0 0 auto; width:38px; height:38px; border-radius:4px; display:grid; place-items:center;
    font-family:var(--font-num); font-weight:700; font-size:.9rem; border:1.5px solid var(--cat); color:var(--cat);
    font-variant-numeric:tabular-nums; background:color-mix(in srgb,var(--cat) 8%, transparent);
  }
  .item h3{font-size:1.25rem; font-weight:700; line-height:1.3; letter-spacing:-.01em}
  .item h3 a{color:var(--ink)}
  .item h3 a:hover{color:var(--accent)}
  .item .meta{color:var(--ink3); font-size:.78rem; margin-top:6px; display:flex; gap:10px; flex-wrap:wrap;
              align-items:center; font-family:var(--font-num); font-variant-numeric:tabular-nums}
  .item .meta .cat{color:var(--cat); font-family:var(--font-sans); text-transform:uppercase;
                   font-size:.7rem; letter-spacing:.09em; font-weight:600}
  .item .summ{color:var(--ink2); margin-top:10px; font-size:.95rem; line-height:1.6; max-width:72ch}
  .item .summ.clamp{display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden}
  .item .tags{margin-top:10px; display:flex; flex-wrap:wrap; gap:6px}
  .tag{font-size:.7rem; color:var(--ink2); background:var(--panel); border:1px solid var(--rule);
       border-radius:3px; padding:2px 9px}
  .item .foot{display:flex; align-items:center; justify-content:space-between; margin-top:12px}
  .more{color:var(--accent); font-size:.82rem; cursor:pointer; border:none; background:none; padding:0;
        text-decoration:underline; text-underline-offset:3px}
  .more:hover{color:var(--ink)}
  .open{
    display:inline-flex; align-items:center; gap:6px; font-size:.8rem; color:var(--ink);
    background:var(--panel); border:1px solid var(--rule2); border-radius:4px; padding:6px 12px; transition:.15s;
    font-weight:500;
  }
  .open:hover{border-color:var(--ink); text-decoration:none}

  .arrow-l,.arrow-r{display:inline-block; width:.82em; height:.82em; background:currentColor; flex:0 0 auto;
    -webkit-mask:var(--ic) no-repeat center/contain; mask:var(--ic) no-repeat center/contain}
  .arrow-l{--ic:url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%23000" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>')}
  .arrow-r{--ic:url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%23000" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>')}
  .pill{display:inline-flex; align-items:center; gap:6px; font-size:.82rem; padding:7px 14px; border-radius:4px;
        cursor:pointer; border:1px solid var(--rule2); background:var(--panel); color:var(--ink2);
        font-weight:500; transition:.15s}
  .pill:hover{color:var(--ink); border-color:var(--ink2); text-decoration:none}
  .pill.on{color:var(--on-accent); background:var(--accent); border-color:var(--accent)}

  .toolbar{
    display:flex; align-items:center; justify-content:space-between; gap:10px; flex-wrap:wrap;
    background:var(--panel); border:1px solid var(--rule); border-radius:var(--radius);
    padding:10px 14px; margin-bottom:22px;
  }
  .toolbar .btns{display:flex; gap:8px; align-items:center; flex-wrap:wrap}

  .anchors{display:flex; gap:8px; flex-wrap:wrap; margin-bottom:22px}
  .anchors a{
    font-size:.78rem; color:var(--ink2); background:var(--panel); border:1px solid var(--rule);
    border-radius:3px; padding:4px 11px; font-weight:500; transition:.15s;
  }
  .anchors a:hover{color:var(--ink); border-color:var(--rule2); text-decoration:none}
  .anchors a i{display:inline-block; width:7px; height:7px; border-radius:1px; margin-right:6px}

  .filters{display:flex; gap:8px; flex-wrap:wrap; margin-bottom:16px; align-items:center}
  select,input,button{
    background:var(--paper); color:var(--ink); border:1px solid var(--rule2); border-radius:4px;
    padding:9px 13px; font-size:.88rem; font-family:inherit; font-weight:500;
  }
  select:focus,input:focus{border-color:var(--accent)}
  button{background:var(--accent); color:var(--on-accent); border-color:var(--accent); cursor:pointer}
  button:hover{border-color:var(--ink)}
  .count{color:var(--ink3); font-size:.9rem; margin:0 0 14px; font-family:var(--font-num); font-weight:500; letter-spacing:.02em; font-variant-numeric:tabular-nums}

  .pager{display:flex; justify-content:center; align-items:center; gap:16px; margin-top:24px; color:var(--ink3); font-size:.85rem}
  .pager a{padding:6px 12px; border:1px solid var(--rule2); border-radius:4px; background:var(--panel); color:var(--ink2); transition:.15s}
  .pager a:hover{color:var(--ink); border-color:var(--ink2); text-decoration:none}

  .detail{
    background:var(--paper); border:1px solid var(--rule); border-radius:var(--radius); padding:30px;
    box-shadow:0 1px 2px rgba(32,36,46,.05), 0 14px 34px rgba(32,36,46,.06);
  }
  .detail h1{font-family:var(--font-serif); font-size:1.45rem; line-height:1.35; letter-spacing:-.01em}
  .detail .meta{color:var(--ink3); font-size:.83rem; margin:12px 0; font-family:var(--font-num); font-variant-numeric:tabular-nums}
  .detail p{color:var(--ink2); line-height:1.7; max-width:72ch}
  .detail .actions{margin-top:20px; display:flex; gap:10px}

  pre.raw{
    background:var(--panel); border:1px solid var(--rule); border-radius:var(--radius); padding:20px;
    font-size:.86rem; line-height:1.55; white-space:pre-wrap; word-wrap:break-word; color:var(--ink2);
    max-height:70vh; overflow:auto; font-family:var(--font-num); font-variant-numeric:tabular-nums;
  }

  .items{display:grid; grid-template-columns:repeat(auto-fit,minmax(430px,1fr)); gap:14px}
  .items .item{margin-bottom:0}
  .empty{color:var(--ink3); text-align:center; padding:46px 0}
  footer{text-align:center; color:var(--ink3); font-size:.78rem; padding-bottom:36px}
  @media (max-width:860px){.items{grid-template-columns:1fr}}
  @media (max-width:760px){
    .bar{flex-direction:column; align-items:flex-start}
    nav{width:100%} nav a{flex:1; text-align:center; padding:11px 4px; font-size:.92rem}
    .grid{grid-template-columns:1fr}
    .day.featured{grid-column:span 1; grid-row:span 1; min-height:150px}
    .day.featured .preview{display:none}
    .filters select,.filters input,.filters button{flex:1 1 100%}
  }
  @media (prefers-reduced-motion:reduce){
    *,*::before,*::after{transition:none!important;animation:none!important}
    html{scroll-behavior:auto}
  }
  @media print{
    body{background:#fff;color:#000}
    header,.toolbar,.anchors,.pager,.filters,.more{display:none!important}
    .day,.item,.detail,pre.raw{background:#fff;border-color:#ddd;box-shadow:none;color:#000}
    .day .dow,.item .summ,.item .meta,.detail p,pre.raw{color:#333}
    a{color:#06c;text-decoration:underline}
    main{padding:0}
    .items{grid-template-columns:1fr}
    .day.featured{grid-column:span 1; grid-row:span 1; min-height:0}
    .hero h1::after{animation:none;width:56px}
  }
</style>
</head>
<body>
<header>
  <div class="wrap bar">
    <a class="logo" href="/" style="color:var(--ink)">
      <div class="logo-mark">T</div>
      <div><b>Tech Agent</b><span>Python · Flask</span></div>
    </a>
    <nav aria-label="Principal">
      <a href="/" class="{{ 'on' if nav=='inicio' else '' }}">{{ NAV_INI }}</a>
      <a href="/db" class="{{ 'on' if nav=='db' else '' }}">{{ NAV_DB }}</a>
      <a href="/feed" target="_blank">RSS</a>
    </nav>
  </div>
</header>
<main class="wrap">
{{ contenido }}
</main>
<footer>{{ FOOTER }}</footer>
</body>
</html>
"""


def page(contenido: str, titulo: str, nav: str = "inicio", desc: str = "", path: str = "/") -> str:
    t = L["es"]
    if not desc:
        desc = "Resúmenes diarios de tecnología, inteligencia artificial y programación, con historial y búsqueda."
    url = SITE_URL + path
    html = LAYOUT
    html = html.replace("{{ META_DESC }}", esc(desc)[:230])
    html = html.replace("{{ META_URL }}", url)
    html = html.replace("{{ NAV_INI }}", t["nav_ini"])
    html = html.replace("{{ NAV_DB }}", t["nav_db"])
    html = html.replace("{{ FOOTER }}", t["footer"])
    html = html.replace("{{ 'on' if nav=='inicio' else '' }}", "on" if nav == "inicio" else "")
    html = html.replace("{{ 'on' if nav=='db' else '' }}", "on" if nav == "db" else "")
    html = html.replace("{{ contenido }}", contenido)
    html = html.replace("{{ titulo }}", titulo)
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
    return L["es"]["dias"][d.weekday()]


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ===========================================================================
#  RUTA: PORTADA
# ===========================================================================
@app.route("/")
def index():
    t = L["es"]
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
    for i, s in enumerate(summaries[:14]):
        d = load_json_summary(s["fecha"])
        n = d.get("total", "?") if d else "?"
        dow = f" · {t['today']}" if s["fecha"] == hoy else ""
        extra = ""
        cls = "day featured" if i == 0 else "day"
        if i == 0 and d:
            previews = []
            for cat, items in d.get("categories", {}).items():
                for it in items[:8]:
                    previews.append(it.get("title", ""))
                    if len(previews) >= 3:
                        break
                if len(previews) >= 3:
                    break
            extra = '<div class="preview">' + "".join(
                f"<span>{esc(p)}</span>" for p in previews
            ) + "</div>"
        cards += f"""
        <a class="{cls}" href="/summary/{s['fecha']}">
          <div class="fecha">{s['fecha']}</div>
          <div class="dow">{dia_semana(s['fecha'])}{dow}</div>
          <span class="n">{n} {t['news']}</span>
          <span class="go"><span class="arrow-r"></span></span>
          {extra}
        </a>"""

    if not cards:
        cards = f"<div class='empty'>{t['empty_summaries']}</div>"

    contenido = f"""
    <section class="hero">
      <h1>{t['hero_h1a']}<br>{t['hero_h1b']}</h1>
      <p>{t['hero_p']}</p>
      <div class="stats">
        <div class="stat"><b>{total_items}</b><span>{t['stat_news']}</span></div>
        <div class="stat"><b>{len(summaries)}</b><span>{t['stat_summaries']}</span></div>
        <div class="stat"><b>6</b><span>{t['stat_categories']}</span></div>
        <div class="stat"><b>22</b><span>{t['stat_feeds']}</span></div>
      </div>
    </section>
    <h2 class="sec"><span class="dot" style="background:var(--accent)"></span>{t['sec_summaries']}</h2>
    <div class="grid">{cards}</div>
    """
    return page(contenido, t["title_index"], desc=t["hero_p"], path="/")


# ===========================================================================
#  RUTA: RESUMEN DE UN DIA
# ===========================================================================
@app.route("/summary/<fecha>")
def summary_detail(fecha):
    t = L["es"]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha):
        abort(400)
    data = load_json_summary(fecha)
    if not data:
        txt = os.path.join(SUMMARY_DIR, f"tech-resumen-{fecha}.txt")
        if not os.path.isfile(txt):
            abort(404)
        contenido = f"""
        <h1 class="page-title">{fecha}</h1>
        <div class="toolbar">
          <div class="btns">
            <a href="/" class="pill"><span class="arrow-l"></span>{t['back']}</a>
          </div>
          <a href="/summary/{fecha}/raw" class="pill">{t['view_plain']}</a>
        </div>
        <pre class="raw">{esc(read_txt(fecha))}</pre>"""
        return page(contenido, f"{t['summary_title']} {fecha}", desc=f"Resumen diario de tecnología e IA · {fecha}", path=f"/summary/{fecha}")

    total = data.get("total", 0)
    hoy = fecha == datetime.now().strftime("%Y-%m-%d")

    anchors = ""
    for cat in data["categories"]:
        color = CAT_COLORS.get(cat, "#5d6475")
        anchors += f"<a href='#cat-{cat.replace(' ', '-')}'><i style='background:{color}'></i>{cat}</a>"

    secciones = ""
    for cat, items in data["categories"].items():
        color = CAT_COLORS.get(cat, "#5d6475")
        body = ""
        for it in items:
            tags = "".join(f"<span class='tag'>{esc(t)}</span>" for t in it.get("tags", [])[:8])
            pub = ""
            if it.get("published"):
                pub = it["published"][:10]
            body += f"""
            <article class="item">
              <div class="row">
                <div class="score" style="--cat:{color}">{it.get('score', 0)}</div>
                <div>
                  <h3>{esc(it['title'])}</h3>
                  <div class="meta">
                    <span class="cat" style="color:{color}">{esc(cat)}</span>
                    <span>{esc(pub)}</span>
                  </div>
                  <p class="summ clamp">{esc(it['summary'] or '')}</p>
                  <button class="more" data-more>{t['read_more']}</button> <button class="more" data-less style="display:none">{t['see_less']}</button>
                </div>
              </div>
              <div class="tags">{tags}</div>
              <div class="foot">
                <a class="open" target="_blank" rel="noopener" href="{esc(it['link'] or '#')}">
                  {t['open_article']}
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M7 17L17 7M7 7h10v10"/></svg>
                </a>
              </div>
            </article>"""
        secciones += f"""
        <h2 class="sec" id="cat-{cat.replace(' ', '-')}">
          <span class="dot" style="background:{color}"></span>
          {cat} <span style="color:var(--ink3);font-size:.8rem;font-weight:400">({len(items)})</span>
        </h2>
        <div class="items">
        {body}
        </div>"""

    dow_line = f"{dia_semana(fecha)}{t['today_sfx'] if hoy else ''}"
    contenido = f"""
    <h1 class="page-title">{fecha}<span style="color:var(--ink3); font-weight:500"> · {dow_line}</span></h1>
    <div class="toolbar">
      <div class="btns">
        <a href="/" class="pill"><span class="arrow-l"></span>{t['back_all']}</a>
        <span class="pill on">{total} {t['news']}</span>
      </div>
      <div class="btns">
        <a href="/summary/{fecha}/raw" class="pill">{t['plain']}</a>
      </div>
    </div>
    <div class="anchors">{anchors}</div>
    {secciones}

    <script>
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
    return page(contenido, f"{t['summary_title']} {fecha}", desc=f"Resumen diario de tecnología e IA · {fecha}", path=f"/summary/{fecha}")


@app.route("/summary/<fecha>/raw")
def summary_raw(fecha):
    path = os.path.join(SUMMARY_DIR, f"tech-resumen-{fecha}.txt")
    if not os.path.isfile(path):
        abort(404)
    return Response(read_txt(fecha), mimetype="text/plain; charset=utf-8")


# ===========================================================================
#  RUTA: HISTORIAL (SQLite)
# ===========================================================================
@app.route("/db")
def db_view():
    t = L["es"]
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
    <h1 class="page-title">{t['title_db']}</h1>
    <form class="filters" method="get" aria-label="{t['title_db']}">
      <select name="cat" aria-label="{t['all_categories']}" onchange="this.form.submit()">
        <option value="">{t['all_categories']}</option>
        {''.join(f"<option value='{c}' {'selected' if c==cat else ''}>{c}</option>" for c in CATEGORIES)}
      </select>
      <input type="text" name="q" value="{esc(q)}" placeholder="{t['search_ph']}" aria-label="{t['search_ph']}">
      <button type="submit">{t['search_btn']}</button>
    </form>"""

    cards = '<div class="items">'
    for r in rows:
        color = CAT_COLORS.get(r["category"], "#5d6475")
        pub = (r["published"] or "-")[:10]
        cards += f"""
        <a class="item" href="/db/{r['id']}">
          <div class="row">
            <div class="score" style="--cat:{color}">{r['score']}</div>
            <div>
              <h3 style="color:var(--ink)">{esc(r['title'])}</h3>
              <div class="meta" style="margin-top:6px">
                <span class="cat" style="color:{color}">{esc(r['category'])}</span>
                <span>{esc(pub)}</span>
              </div>
              <p class="summ">{esc((r['summary'] or '')[:180])}</p>
            </div>
          </div>
        </a>"""

    if not rows:
        cards = f"<div class='empty'>{t['empty_db']}</div>"
    else:
        cards += "</div>"

    if total > limit:
        tp = (total - 1) // limit + 1
        pg = offset // limit + 1
        def href(o):
            return f"/db?offset={o}&cat={cat}&q={q}"
        prev = href(max(0, offset - limit))
        nxt = href(min(total - limit, offset + limit))
        pager = f'<div class="pager"><a href="{prev}"><span class="arrow-l"></span>{t["prev"]}</a><span>{t["page1"]} {pg} {t["page2"]} {tp}</span><a href="{nxt}">{t["next"]}<span class="arrow-r"></span></a></div>'
    else:
        pager = ""

    contenido = select + f"<h2 class='count'>{total} {t['saved']}</h2>" + cards + pager
    return page(contenido, t["title_db"], nav="db", desc="Historial completo de noticias de tecnología, con filtros por categoría y búsqueda.", path="/db")


@app.route("/db/<int:news_id>")
def db_detail(news_id):
    t = L["es"]
    conn = get_db()
    r = conn.execute("SELECT * FROM news WHERE id = ?", (news_id,)).fetchone()
    conn.close()
    if not r:
        abort(404)
    color = CAT_COLORS.get(r["category"], "#5d6475")
    contenido = f"""
    <p><a href="/db" class="pill" style="display:inline-flex; align-items:center; gap:6px; padding:7px 14px"><span class="arrow-l"></span>{t['back_db']}</a></p>
    <div class="detail" style="margin-top:14px">
      <div class="meta"><span class="cat" style="color:{color}; font-weight:600">{esc(r['category'])}</span></div>
      <h1>{esc(r['title'])}</h1>
      <div class="meta">{(r['published'] or '').strip()[:10] or t['no_date']} &middot; {t['relevance']} {r['score']}</div>
      <p>{esc(r['summary'] or t['no_desc'])}</p>
      <div class="actions">
        <a class="open" target="_blank" rel="noopener" href="{esc(r['link'] or '#')}">{t['open_orig']}<span class="arrow-r"></span></a>
      </div>
    </div>"""
    return page(contenido, t['title_detail'], nav='db', desc=(esc(r['title'])[:180]), path=f'/db/{news_id}')


# ===========================================================================
#  RUTAS VARIAS
# ===========================================================================
@app.route("/feed")
def feed():
    t = L["es"]
    items = ""
    for s in list_summaries()[:10]:
        total = "?"
        d = load_json_summary(s["fecha"])
        if d:
            total = d.get("total", "?")
        items += f"""
        <item>
          <title>{t['feed_item']} {s['fecha']} ({total})</title>
          <link>http://{request.host}/summary/{s['fecha']}</link>
          <guid>http://{request.host}/summary/{s['fecha']}</guid>
          <pubDate>{s['mtime'].strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>
          <description><![CDATA[{t['feed_desc']}.]]></description>
        </item>"""
    rss = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
  <title>{t['feed_title']}</title>
  <link>http://{request.host}/</link>
  <description>{t['feed_desc']}</description>
  {items}
</channel>
</rss>"""
    return Response(rss, mimetype="application/rss+xml")


@app.route("/health")
def health():
    return jsonify(ok=True, resumenes=len(list_summaries()))



@app.route('/favicon.svg')
def favicon():
    path = os.path.join(BASE_DIR, 'favicon.svg')
    if not os.path.isfile(path):
        abort(404)
    with open(path, 'rb') as fh:
        return Response(fh.read(), mimetype='image/svg+xml')


@app.errorhandler(404)
def not_found(_):
    msg = esc(L["es"]["err404"])
    home = f"<a class='pill' href='/'><span class='arrow-l'></span>{L['es']['back_all']}</a>"
    return page(
        f"<h1 class='page-title' style='text-align:center;margin-top:56px'>{msg}</h1>"
        f"<p class='empty'>{home}</p>",
        "404"), 404


@app.errorhandler(500)
def server_error(_):
    msg = esc(L["es"]["err500"])
    home = f"<a class='pill' href='/'><span class='arrow-l'></span>{L['es']['back_all']}</a>"
    return page(
        f"<h1 class='page-title' style='text-align:center;margin-top:56px'>{msg}</h1>"
        f"<p class='empty'>{home}</p>",
        "Error"), 500


if __name__ == "__main__":
    port = int(os.getenv("TECH_NEWS_PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)