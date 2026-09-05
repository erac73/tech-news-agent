<div align="center">

  <img src="logo.svg" alt="Logo de Tech News Agent" width="130" height="130">

  <h1>Tech News Agent</h1>

  <p><em>Agente de noticias de tecnología con panel web y lectura en español.</em></p>

  <p>
    <img src="https://img.shields.io/badge/Python-3.11-blue" alt="Python 3.11">
    <img src="https://img.shields.io/badge/Flask-2.2-lightblue" alt="Flask 2.2">
    <img src="https://img.shields.io/badge/SQLite-historial-brightgreen" alt="SQLite">
    <img src="https://img.shields.io/badge/Cloudflare-Tunnel-orange" alt="Cloudflare Tunnel">
  </p>

</div>

---

**Tech News Agent** recopila cada día información relevante sobre
**programación, inteligencia artificial, ciencias de la computación,
frameworks/web, DevOps y noticias tech**, la filtra según tus intereses y te
la presenta en un **panel web moderno** con la opción de **leer todo en
español**. Corre como servicio (cron + systemd) en un **servidor Linux**.

---

## Índice

- [Características](#características)
- [Arquitectura](#arquitectura)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Instalación](#instalación)
- [Uso del agente (CLI)](#uso-del-agente-cli)
- [Panel web](#panel-web)
- [Lectura en español](#lectura-en-español)
- [Automatización](#automatización)
- [Exponer con Cloudflare Tunnel](#exponer-con-cloudflare-tunnel)
- [Personalización](#personalización)
- [Rutas del panel](#rutas-del-panel)
- [Solución de problemas](#solución-de-problemas)

---

## Características

- **22 fuentes RSS** repartidas en 6 categorías:
  `Programación`, `Inteligencia Artificial`, `Ciencias de la Computación`,
  `Frameworks y Web`, `Noticias Tech` y `Docker / DevOps`
  (Hacker News, arXiv, OpenAI, GitHub Blog, StackOverflow, Reddit, dev.to,
  TechCrunch, Docker, NVIDIA, MIT y más).
- **Filtrado por relevancia**: puntúa cada noticia con palabras clave del
  desarrollo de software (python, machine learning, llm, backend, kubernetes,
  algorithm…).
- **Historial SQLite**: todas las noticias quedan guardadas para consulta.
- **Resumen diario** en texto plano y en **JSON estructurado**.
- **Panel web estético y responsive** con tema oscuro, tarjetas por noticia,
  buscador y filtros.
- **Traducción al español** de títulos y resúmenes (Google Translate) con
  **caché en disco** para que la consulta sea instantánea.
- **Cron diario + servicio systemd**: todo funciona solo tras reiniciar el
  servidor.
- **Exposición pública** opcional vía Cloudflare Tunnel con HTTPS.

---

## Arquitectura

```
 Servidor (serpico@mipi.dpdns.org)
 ┌─────────────────────────────────────────────────────────────┐
 │  cron (08:00)                                                │
 │   └─ tech_news_agent.py                                      │
 │        ├─ Descarga feeds RSS (22 fuentes / 6 categorías)     │
 │        ├─ Filtra por KEYWORDS y puntúa relevancia            │
 │        ├─ Guarda en SQLite (historial)                       │
 │        └─ Genera resumenes .txt y .json                      │
 │                                                              │
 │  systemd: tech-dashboard.service                             │
 │   └─ tech_dashboard.py  (Flask · puerto 8080)                │
 │        ├─ Portada con estadísticas                           │
 │        ├─ Resumen del día en tarjetas                        │
 │        ├─ Traducción EN→ES (deep-translator + caché)         │
 │        └─ Historial con búsqueda y filtros                   │
 │                                                              │
 │  cloudflared.service                                         │
 │   └─ tech.mipi.dpdns.org → http://localhost:8080             │
 └─────────────────────────────────────────────────────────────┘
```

### Flujo de datos

1. **08:00** el cron ejecuta `tech_news_agent.py --days 2`.
2. El agente descarga los feeds, filtra las noticias relevantes y las guarda:
   - `data/tech_news_history.db` → historial completo (SQLite).
   - `data/resumenes/tech-resumen-YYYY-MM-DD.{txt,json}` → resumen del día.
3. El panel web lee esos archivos y los muestra en el navegador.
4. Al pulsar **"Traducir a español"**, el panel pide la traducción al
   endpoint interno, que la cachea en `data/traducciones/` (solo la primera
   vez tarda; después es instantáneo).

---

## Estructura del proyecto

```
tech-news-agent/
├── tech_news_agent.py    # agente: descarga feeds, filtra y genera resumenes
├── tech_dashboard.py     # panel web Flask + traduccion al español
├── run_dashboard.sh      # lanzador del panel (usado por systemd)
├── tech-dashboard.service# unit de systemd
├── logo.svg              # logo del proyecto
├── favicon.svg           # icono del navegador
├── requirements.txt      # dependencias Python
├── README.md
└── data/                 # (generado, no se versiona)
    ├── tech_news_history.db      # historial SQLite
    ├── resumenes/                # resumenes .txt y .json por dia
    └── traducciones/             # cache de traducciones EN→ES
```

---

## Instalación

Requiere **Python 3.11+** y acceso a internet (para RSS y traducción).

```bash
# 1) Clonar / copiar el proyecto
git clone https://github.com/erac73/tech-news-agent.git
cd tech-news-agent

# 2) Dependencias
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3) Primera ejecución del agente
python tech_news_agent.py --days 2
```

Si instalas con el Python del sistema (Debian), puedes usar:

```bash
pip3 install --user --break-system-packages -r requirements.txt
```

---

## Uso del agente (CLI)

```bash
python tech_news_agent.py                # resumen de los últimos 2 días
python tech_news_agent.py --days 7       # ventana de 7 días
python tech_news_agent.py --test         # prueba rápida (solo 2 fuentes)
python tech_news_agent.py --list-feeds   # muestra las fuentes configuradas
python tech_news_agent.py --show-db      # últimas noticias del historial
python tech_news_agent.py --var          # muestra rutas y configuración
```

La salida incluye:

```
* Buscando noticias de los ultimos 2 dia(s)...
* 129 noticias relevantes, 112 nuevas guardadas en la base.
* Resumen guardado en: .../data/resumenes/tech-resumen-2026-09-05.txt
* Resumen JSON guardado en: .../data/resumenes/tech-resumen-2026-09-05.json
```

### Cómo se puntúa la relevancia

Cada noticia se compara contra `KEYWORDS` (todas relacionadas con el
desarrollo de software). Por cada coincidencia con límites de palabra se suma
**+1** al `score`; ciertos temas no deseados (cripto, celebridades, deportes)
restan **-2**. Las noticias con `score <= 0` se descartan.

---

## Panel web

Arranca el panel con:

```bash
python tech_dashboard.py                 # http://localhost:8080
# o configura el puerto:
TECH_NEWS_PORT=8085 python tech_dashboard.py
```

Vistas incluidas:

- **Resúmenes** (`/`) — portada con estadísticas y tarjetas por día.
- **Resumen del día** (`/summary/2026-09-05`) — tarjetas por noticia con
  puntaje, categoría, tags, "Leer más" y enlace al artículo.
- **Historial** (`/db`) — todas las noticias guardadas, con buscador y filtro
  por categoría.
- **Detalle de noticia** (`/db/123`) — descripción completa con enlace.
- **RSS** (`/feed`) — suscríbete a los resúmenes con tu lector favorito.

Los colores por categoría son consistentes en todo el panel:

| Categoría | Color |
|---|---|
| Programación | azul `#4c9aff` |
| Inteligencia Artificial | violeta `#9f6bff` |
| Ciencias de la Computación | naranja `#ff8a4c` |
| Frameworks y Web | teal `#2dd4bf` |
| Noticias Tech | rosa `#f43f5e` |
| Docker / DevOps | celeste `#38bdf8` |

---

## Lectura en español

Cada resumen tiene el botón **"Traducir a español"**:

1. Traduce los **títulos** de todas las noticias del día.
2. Traduce los **resúmenes** de las 10 más relevantes de cada categoría
   (las demás conservan su resumen original con la nota *"Solo en inglés"*).
3. Si Google devuelve un error o el texto contiene HTML, se conserva el
   original (no se rompe la lectura).
4. El resultado se **cachea** en `data/traducciones/`:
   - Primera vez: tarda ~2 minutos (se muestra un indicador de progreso).
   - Siguientes: respuesta instantánea.
5. El botón **"Ver original"** te devuelve al inglés al instante.

La caché expira automáticamente a los 30 días y se regenera.

---

## Automatización

### Cron (agente diario)

Se ejecuta a las **08:00** todos los días:

```cron
0 8 * * * cd /home/serpico/tech-news-agent && /usr/bin/env python3 tech_news_agent.py --days 2 >> data/tech_news_agent.log 2>&1
```

Instalarlo sin pisar tu crontab actual:

```bash
(crontab -l; echo "0 8 * * * cd /home/serpico/tech-news-agent && /usr/bin/env python3 tech_news_agent.py --days 2 >> data/tech_news_agent.log 2>&1") | crontab -
```

### systemd (panel web + arranque automático)

El archivo `tech-dashboard.service` incluido en el repo:

```ini
[Unit]
Description=Tech News Dashboard (Flask web UI)
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/bin/python3 /home/serpico/tech-news-agent/tech_dashboard.py
WorkingDirectory=/home/serpico/tech-news-agent
User=serpico
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Instalarlo:

```bash
sudo cp tech-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tech-dashboard
```

Comandos útiles:

```bash
systemctl status tech-dashboard
journalctl -u tech-dashboard -n 50 --no-pager
```

---

## Exponer con Cloudflare Tunnel

Para acceder al panel desde cualquier lugar con HTTPS (como
`https://tech.mipi.dpdns.org`):

1. Añade al archivo de configuración del túnel un hostname hacia el panel:
   ```yaml
   # /etc/cloudflared/config.yml
   ingress:
     - hostname: tech.mipi.dpdns.org
       service: http://localhost:8080
   ```
2. Crea el registro DNS apuntando al túnel:
   ```bash
   cloudflared tunnel route dns <ID_TUNEL> tech.mipi.dpdns.org
   ```
3. Valida y reinicia:
   ```bash
   cloudflared tunnel --config /etc/cloudflared/config.yml ingress validate
   sudo systemctl restart cloudflared
   ```

---

## Personalización

### Añadir o quitar fuentes

En `tech_news_agent.py`, edita el diccionario `FEEDS`:

```python
FEEDS = {
    "Programacion": [
        "https://dev.to/feed",
        "https://tu-nueva-fuente.com/rss",
    ],
    ...
}
```

### Ajustar las palabras clave

Edita las listas `KEYWORDS` (suman relevancia) y `EXCLUDE_KEYWORDS`
(restan). Se comparan con límites de palabra.

### Variables de entorno

| Variable | Por defecto | Descripción |
|---|---|---|
| `TECH_NEWS_DATA_DIR` | `./data` | Carpeta de datos (BD, resúmenes, caché) |
| `TECH_NEWS_PORT` | `8080` | Puerto del panel web |
| `TECH_NEWS_RETAIN_DAYS` | `30` | Días que se conservan los resúmenes |

---

## Rutas del panel

| Ruta | Descripción |
|---|---|
| `/` | Portada con resúmenes disponibles |
| `/summary/2026-09-05` | Resumen del día en tarjetas |
| `/summary/2026-09-05/raw` | Resumen en texto plano |
| `/summary/2026-09-05/es` | Datos traducidos al español (JSON) |
| `/db` | Historial con búsqueda y filtros |
| `/db/5` | Detalle de una noticia |
| `/feed` | RSS de los resúmenes |
| `/health` | Estado del servicio |

---

## Solución de problemas

**El panel no responde**
```bash
systemctl status tech-dashboard
journalctl -u tech-dashboard -n 50 --no-pager
```

**No puedo acceder desde fuera**
- Comprueba que el hostname esté en la config del túnel y que el registro
  DNS apunte a tu túnel (`cloudflared tunnel list`).
- Verifica que el servicio del panel escuche en `0.0.0.0:8080`
  (`ss -tln | grep 8080`).

**La traducción dice "No se pudo traducir"**
- El servicio necesita internet. Si Google responde con error de red,
  el panel conserva el texto original; reintenta en unos segundos.

**Demasiadas o muy pocas noticias**
- Ajusta `KEYWORDS` / `EXCLUDE_KEYWORDS` y el número de fuentes en `FEEDS`.

---

<div align="center">

  <p>
    Hecho con
    <svg viewBox="0 0 24 24" width="14" height="14" fill="#f43f5e" aria-hidden="true"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
    · Python · Flask
  </p>

</div>