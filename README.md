<p align="center">
  <img src="logo.svg" alt="Logo de Tech News Agent" width="120" height="120">
</p>

# Tech News Agent

*Agente de noticias de tecnología con panel web y lectura en español.*

<p>
  <img src="https://img.shields.io/badge/Python-3.11-blue" alt="Python 3.11">
  <img src="https://img.shields.io/badge/Flask-2.2-lightblue" alt="Flask 2.2">
  <img src="https://img.shields.io/badge/SQLite-historial-brightgreen" alt="SQLite">
  <img src="https://img.shields.io/badge/Cloudflare-Tunnel-orange" alt="Cloudflare Tunnel">
</p>

Tech News Agent recopila cada día información relevante sobre programación, inteligencia artificial, ciencias de la computación, frameworks/web, DevOps y noticias tech, la filtra según tus intereses y la presenta en un panel web moderno con la opción de leer todo en español. Corre como servicio (cron + systemd) en un servidor Linux.

---

## Características

- **22 fuentes RSS** en 6 categorías (Hacker News, arXiv, OpenAI, GitHub Blog, StackOverflow, Reddit, dev.to, TechCrunch, Docker, NVIDIA, MIT y más).
- **Filtrado por relevancia** con palabras clave del desarrollo de software.
- **Historial SQLite**: todas las noticias quedan guardadas para consulta.
- **Resumen diario** en texto plano y en JSON estructurado.
- **Panel web responsive** con tema oscuro, tarjetas, buscador y filtros.
- **Traducción al español** (Google Translate) con caché en disco.
- **Cron diario + systemd**: funciona solo tras reiniciar el servidor.
- **Acceso público** opcional vía Cloudflare Tunnel con HTTPS.

---

## Arquitectura

```
Servidor (serpico@mipi.dpdns.org)
┌──────────────────────────────────────────────────────────────┐
│  cron (08:00)                                                 │
│   └─ tech_news_agent.py                                       │
│        ├─ Descarga feeds RSS (22 fuentes / 6 categorías)      │
│        ├─ Filtra por KEYWORDS y puntúa relevancia             │
│        ├─ Guarda en SQLite (historial)                        │
│        └─ Genera resumenes .txt y .json                       │
│                                                               │
│  systemd: tech-dashboard.service                              │
│   └─ tech_dashboard.py  (Flask · puerto 8080)                 │
│        ├─ Portada con estadísticas                            │
│        ├─ Resumen del día en tarjetas                         │
│        ├─ Traducción EN→ES (deep-translator + caché)          │
│        └─ Historial con búsqueda y filtros                    │
│                                                               │
│  cloudflared.service                                          │
│   └─ tech.mipi.dpdns.org → http://localhost:8080              │
└──────────────────────────────────────────────────────────────┘
```

---

## Instalación

Requiere **Python 3.11+** y acceso a internet.

```bash
git clone https://github.com/erac73/tech-news-agent.git
cd tech-news-agent

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Primera ejecución del agente
python tech_news_agent.py --days 2
```

En Debian/Ubuntu puedes usar también el Python del sistema:

```bash
pip3 install --user --break-system-packages -r requirements.txt
```

---

## Uso

```bash
python tech_news_agent.py                # resumen de los últimos 2 días
python tech_news_agent.py --days 7       # ventana de 7 días
python tech_news_agent.py --test         # prueba rápida (solo 2 fuentes)
python tech_news_agent.py --list-feeds   # muestra las fuentes configuradas
python tech_news_agent.py --show-db      # últimas noticias del historial
python tech_news_agent.py --var          # muestra rutas y configuración
```

### Puntaje de relevancia

Cada noticia se compara contra `KEYWORDS`. Por cada coincidencia se suma **+1**; temas no deseados restan **-2**. Las noticias con `score <= 0` se descartan.

---

## Panel web

```bash
python tech_dashboard.py                 # http://localhost:8080
TECH_NEWS_PORT=8085 python tech_dashboard.py  # puerto personalizado
```

Rutas disponibles:

| Ruta | Descripción |
|---|---|
| `/` | Portada con resúmenes |
| `/summary/YYYY-MM-DD` | Resumen del día |
| `/summary/YYYY-MM-DD/raw` | Texto plano |
| `/summary/YYYY-MM-DD/es` | Traducción al español (JSON) |
| `/db` | Historial con búsqueda |
| `/db/<id>` | Detalle de noticia |
| `/feed` | RSS |
| `/health` | Estado del servicio |

---

## Traducción al español

Al pulsar **"Traducir a español"** se traducen los títulos y los 10 resúmenes más relevantes de cada categoría. La caché se guarda en `data/traducciones/` (la primera vez tarda ~2 minutos; después es instantáneo). Caduca a los 30 días.

---

## Personalización

- **Fuentes**: edita `FEEDS` en `tech_news_agent.py`.
- **Palabras clave**: ajusta `KEYWORDS` y `EXCLUDE_KEYWORDS`.
- **Variables de entorno**:

| Variable | Por defecto | Descripción |
|---|---|---|
| `TECH_NEWS_DATA_DIR` | `./data` | Carpeta de datos |
| `TECH_NEWS_PORT` | `8080` | Puerto del panel |
| `TECH_NEWS_RETAIN_DAYS` | `30` | Días de retención |

---

## Solución de problemas

**El panel no responde**
```bash
systemctl status tech-dashboard
journalctl -u tech-dashboard -n 50 --no-pager
```

**No puedo acceder desde fuera**

Verifica que el hostname esté en la config del túnel y que el DNS apunte a tu túnel (`cloudflared tunnel list`).

**La traducción falla**

El servicio necesita internet. Si Google falla, se conserva el texto original.

---

<p align="center"><sub>Python · Flask · SQLite</sub></p>
