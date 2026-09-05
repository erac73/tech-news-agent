#!/usr/bin/env python3
"""
Tech News Agent
================================
Agente que busca informacion sobre el mundo de la tecnologia:
programacion, nuevas tecnologias, IA, frameworks, ciencias de la computacion,
y material relevante para el desarrollo de software.

- Descarga feeds RSS de multiples fuentes.
- Filtra noticias por palabras clave.
- Genera un resumen diario en archivos de texto/Markdown.
- Guarda un historico en formato SQLite.

Uso:
    python3 tech_news_agent.py                 # modulo por defecto: daily
    python3 tech_news_agent.py --days 3        # resume ultimos 3 dias
    python3 tech_news_agent.py --test          # prueba con pocas fuentes
    python3 tech_news_agent.py --var           # imprime variables de entorno
    python3 tech_news_agent.py --list-feeds    # lista las fuentes
"""

import argparse
import datetime as dt
import html
import json
import os
import re
import sqlite3
import sys
import textwrap
from collections import Counter

try:
    import feedparser
except ImportError:
    sys.stderr.write("Error: falta la libreria 'feedparser'. Instala con: pip3 install --user feedparser\n")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Rutas y configuracion
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.getenv("TECH_NEWS_DATA_DIR", os.path.join(BASE_DIR, "data"))
DB_PATH = os.path.join(DATA_DIR, "tech_news_history.db")
SUMMARY_DIR = os.path.join(DATA_DIR, "resumenes")

# ---------------------------------------------------------------------------
# Fuentes RSS por categoria (relevantes al desarrollo de software)
# ---------------------------------------------------------------------------
FEEDS = {
    "Programacion": [
        "https://www.reddit.com/r/programming/.rss",
        "https://dev.to/feed",
        "https://blog.codinghorror.com/rss/",
        "https://css-tricks.com/feed/",
        "https://www.freecodecamp.org/news/rss/",
    ],
    "Inteligencia Artificial": [
        "https://www.reddit.com/r/MachineLearning/.rss",
        "https://news.mit.edu/rss/topic/artificial-intelligence2",
        "https://blogs.nvidia.com/blog/feed/",
        "https://openai.com/blog/rss.xml",
    ],
    "Ciencias de la Computacion": [
        "https://news.ycombinator.com/rss",
        "https://www.reddit.com/r/compsci/.rss",
        "https://arxiv.org/rss/cs",
    ],
    "Frameworks y Web": [
        "https://reactjs.org/feed.xml",
        "https://blog.angular.io/feed",
        "https://github.blog/feed/",
        "https://stackoverflow.blog/feed/",
    ],
    "Noticias Tech": [
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://www.theverge.com/rss/index.xml",
        "https://www.wired.com/feed/tag/tech/latest/rss",
        "https://techcrunch.com/feed/",
    ],
    "Docker / DevOps": [
        "https://www.docker.com/blog/feed/",
        "https://devops.com/feed/",
    ],
}

# Palabras clave relevantes para el desarrollo de software
KEYWORDS = [
    "python", "javascript", "typescript", "java", "golang", "rust", "c++", "c#",
    "programming", "developer", "software", "engineering", "code", "coding",
    "machine learning", "deep learning", "neural", "artificial intelligence", "ai",
    "llm", "gpt", "language model", "transformer", "model",
    "framework", "react", "angular", "vue", "django", "flask", "fastapi",
    "node.js", "nodejs", "backend", "frontend", "fullstack", "api", "rest",
    "database", "sql", "nosql", "postgresql", "mysql", "mongodb",
    "docker", "kubernetes", "k8s", "devops", "ci/cd", "cloud", "aws", "azure",
    "open source", "opensource", "github", "git",
    "algorithm", "data structure", "computing", "computer science",
    "security", "cybersecurity", "performance", "optimization",
    "agile", "scrum", "design pattern", "architecture",
    "web development", "mobile", "android", "ios", "flutter",
    "cybersecurity", "testing", "tester", "unit test",
]

EXCLUDE_KEYWORDS = [
    "cryptocurrency", "bitcoin", "nft", "trading", "stock market",
    "celebrity", "hollywood", "sports scores",
]

# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def strip_html(text):
    """Elimina etiquetas HTML del texto y decodifica entidades."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_title(title):
    """Limpia titulos tipo [r/programming] que trae Reddit."""
    title = strip_html(title)
    title = re.sub(r"^\[[^\]]*\]\s*", "", title)
    return title.strip()


def relevance_score(text):
    """Calcula cuan relevante es un item respecto a la carrera."""
    text = text.lower()
    score = 0
    matched = set()

    def has(word):
        # Para palabras con caracteres no-alfanumericos usa una variante flexible
        if any(ch in word for ch in "+#/%"):
            return re.search(r"(?<![a-z0-9])" + re.escape(word) + r"(?![a-z0-9])", text)
        return re.search(r"\b" + re.escape(word) + r"\b", text)

    for kw in KEYWORDS:
        if has(kw):
            score += 1
            matched.add(kw)
    for kw in EXCLUDE_KEYWORDS:
        if has(kw):
            score -= 2
    return score, matched


# ---------------------------------------------------------------------------
# Descarga de feeds
# ---------------------------------------------------------------------------
def fetch_feed(url, timeout=30):
    """Descarga un feed RSS, con manejo de errores."""
    try:
        parsed = feedparser.parse(url)
        if parsed.get("bozo") and not parsed.entries:
            return []
        return parsed.entries
    except Exception as exc:
        sys.stderr.write(f"  [!] {url}: {exc}\n")
        return []


def collect_news(feed_list=None, days=2, max_per_source=15):
    """Recolecta noticias nuevas de todas las fuentes."""
    feed_list = feed_list if feed_list is not None else FEEDS
    news = []
    seen = set()
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)

    for category, urls in feed_list.items():
        for url in urls:
            entries = fetch_feed(url)[:max_per_source]
            for entry in entries:
                title = clean_title(entry.get("title", ""))
                summary = strip_html(entry.get("summary", entry.get("description", "")))
                full_text = f"{title} {summary}"

                score, matched = relevance_score(full_text)
                if score <= 0:
                    continue

                # Evitar duplicados por titulo normalizado
                norm = re.sub(r"[^a-z0-9]+", "", title.lower())[:60]
                if not norm or norm in seen:
                    continue
                seen.add(norm)

                pub_time = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pub_time = dt.datetime(*entry.published_parsed[:6], tzinfo=dt.timezone.utc)
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    pub_time = dt.datetime(*entry.updated_parsed[:6], tzinfo=dt.timezone.utc)

                link = entry.get("link", "")

                news.append({
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "score": score,
                    "matched": matched,
                    "category": category,
                    "published": pub_time,
                    "source": url,
                })
    return news


# ---------------------------------------------------------------------------
# Persistencia SQLite
# ---------------------------------------------------------------------------
def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            link TEXT,
            summary TEXT,
            category TEXT,
            score INTEGER,
            published TEXT,
            source TEXT,
            added_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_news_title ON news(title)")
    conn.commit()
    return conn


def save_news(conn, news):
    """Inserta noticias en la base (evitando duplicados por titulo)."""
    inserted = 0
    for item in news:
        exists = conn.execute(
            "SELECT 1 FROM news WHERE title = ?", (item["title"],)
        ).fetchone()
        if not exists and item["title"]:
            conn.execute(
                """INSERT INTO news (title, link, summary, category, score, published, source)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    item["title"],
                    item["link"],
                    item["summary"][:500],
                    item["category"],
                    item["score"],
                    item["published"].isoformat() if item["published"] else None,
                    item["source"],
                ),
            )
            inserted += 1
    conn.commit()
    return inserted


def get_recent(conn, limit=20):
    """Noticias recientes desde la base."""
    rows = conn.execute(
        """SELECT title, link, category, score, published, summary
           FROM news
           ORDER BY COALESCE(published, added_at) DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    return rows


# ---------------------------------------------------------------------------
# Generacion de resumen
# ---------------------------------------------------------------------------
def wrap(text, width=90):
    return textwrap.fill(text, width=width)


def generate_report(news, days=2):
    """Genera el reporte de texto plano con las noticias mas relevantes."""
    now_str = dt.datetime.now().strftime("%A, %d de %B de %Y")
    lines = []
    lines.append("=" * 78)
    lines.append("  RESUMEN TECH - NOTICIAS DE TECNOLOGIA")
    lines.append("=" * 78)
    lines.append(f"  Fecha: {now_str}")
    lines.append(f"  Noticias recopiladas: {len(news)}   Ventana: {days} dia(s)")
    lines.append("=" * 78)
    lines.append("")

    if not news:
        lines.append("  No se encontraron noticias relevantes en este periodo.")
        lines.append("")
        return "\n".join(lines)

    # Agrupar por categoria
    by_cat = {}
    for item in news:
        by_cat.setdefault(item["category"], []).append(item)

    for category, items in by_cat.items():
        lines.append("")
        lines.append("-" * 78)
        lines.append(f"  {category.upper()} ({len(items)})")
        lines.append("-" * 78)

        for item in sorted(items, key=lambda x: x["score"], reverse=True):
            lines.append("")
            kw = ", ".join(sorted(item["matched"]))
            lines.append(f"  >>> {item['title']}")
            if item["summary"]:
                lines.append(wrap(f"      {item['summary'][:350]}"))
            lines.append(f"      [score: {item['score']} | tags: {kw}]")
            if item["link"]:
                lines.append(f"      {item['link']}")

    lines.append("")
    lines.append("=" * 78)
    lines.append("  Generado por Tech News Agent")
    lines.append("=" * 78)

    return "\n".join(lines)


def save_report(report, summary_dir=None):
    """Guarda el resumen en un archivo fechado."""
    summary_dir = summary_dir or SUMMARY_DIR
    os.makedirs(summary_dir, exist_ok=True)
    fname = f"tech-resumen-{dt.datetime.now():%Y-%m-%d}.txt"
    path = os.path.join(summary_dir, fname)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(report)
    return path


def save_report_json(news, days=2, summary_dir=None):
    """Guarda el resumen estructurado en JSON para el dashboard."""
    summary_dir = summary_dir or SUMMARY_DIR
    os.makedirs(summary_dir, exist_ok=True)
    now = dt.datetime.now()
    date_str = now.strftime("%Y-%m-%d")

    by_cat = {}
    for item in news:
        cat = item["category"]
        by_cat.setdefault(cat, []).append({
            "title": item["title"],
            "summary": item["summary"][:500],
            "link": item["link"],
            "score": item["score"],
            "tags": sorted(item["matched"]),
            "published": item["published"].isoformat() if item["published"] else None,
        })

    # Ordenar categorias y items por relevancia
    ordered = {}
    for cat in by_cat:
        ordered[cat] = sorted(by_cat[cat], key=lambda x: x["score"], reverse=True)

    doc = {
        "generated": date_str,
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "days": days,
        "total": len(news),
        "categories": ordered,
    }

    path = os.path.join(summary_dir, f"tech-resumen-{date_str}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
    return path


def purge_old_summaries(retain_days=30, summary_dir=None):
    """Borra resumenes de mas de N dias para no llenar el disco."""
    summary_dir = summary_dir or SUMMARY_DIR
    if not os.path.isdir(summary_dir):
        return 0
    removed = 0
    cutoff = dt.datetime.now() - dt.timedelta(days=retain_days)
    for fname in os.listdir(summary_dir):
        if not fname.startswith("tech-resumen-"):
            continue
        if not (fname.endswith(".txt") or fname.endswith(".json")):
            continue
        path = os.path.join(summary_dir, fname)
        try:
            mtime = dt.datetime.fromtimestamp(os.path.getmtime(path))
            if mtime < cutoff:
                os.remove(path)
                removed += 1
        except OSError:
            pass
    return removed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Agente de noticias de tecnologia")
    parser.add_argument("--days", type=int, default=2,
                        help="Ventana de dias a considerar (default: 2)")
    parser.add_argument("--test", action="store_true",
                        help="Usa solo 2 fuentes para prueba rapida")
    parser.add_argument("--list-feeds", action="store_true",
                        help="Lista las fuentes configuradas")
    parser.add_argument("--var", action="store_true",
                        help="Muestra variables de entorno y rutas")
    parser.add_argument("--show-db", action="store_true",
                        help="Muestra las ultimas noticias guardadas en la base")
    args = parser.parse_args()

    if args.list_feeds:
        for cat, urls in FEEDS.items():
            print(f"[{cat}]")
            for url in urls:
                print(f"   {url}")
        print()
        print(f"Total fuentes: {sum(len(v) for v in FEEDS.values())}")
        return

    if args.var:
        print(f"BASE_DIR      : {BASE_DIR}")
        print(f"DATA_DIR      : {DATA_DIR}")
        print(f"DB_PATH       : {DB_PATH}")
        print(f"SUMMARY_DIR   : {SUMMARY_DIR}")
        print(f"Python        : {sys.executable}")
        return

    conn = init_db()

    if args.show_db:
        rows = get_recent(conn, limit=20)
        for title, link, cat, score, pub, summary in rows:
            print(f"[{pub or '?'}] [{cat}] ({score}) {title}")
        return

    feeds = FEEDS
    if args.test:
        feeds = {
            "Programacion": ["https://dev.to/feed"],
            "Noticias Tech": ["https://techcrunch.com/feed/"],
        }
        print("* Modo prueba: descargando feeds de muestra...")

    print(f"* Buscando noticias de los ultimos {args.days} dia(s)...")
    news = collect_news(feeds, days=args.days)

    inserted = save_news(conn, news)
    print(f"* {len(news)} noticias relevantes, {inserted} nuevas guardadas en la base.")

    report = generate_report(news, days=args.days)
    path = save_report(report)
    print(f"* Resumen guardado en: {path}")

    json_path = save_report_json(news, days=args.days)
    print(f"* Resumen JSON guardado en: {json_path}")

    removed = purge_old_summaries(retain_days=int(os.getenv("TECH_NEWS_RETAIN_DAYS", "30")))
    if removed:
        print(f"* Limpieza: {removed} resumen(es) antiguo(s) eliminado(s).")

    # Tambien mostramos en consola
    print()
    print(report)

    conn.close()


if __name__ == "__main__":
    main()