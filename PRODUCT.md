# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Único propietario: alguien que revisa un resumen diario de noticias de tecnología, IA y programación, generado automáticamente por un agente en su servidor casero (Raspberry Pi). Primer uso al día: escaneo rápido del resumen de hoy; después: consulta del historial con búsqueda y lectura de un artículo guardado.

## Product Purpose

Recopilar cada mañana las noticias técnicas relevantes, resumirlas (LLM) y puntuarlas, sirviendo un breve diario legible y un historial buscable. El éxito es leer el resumen del día en un par de minutos sin salir de la página.

## Positioning

Un pipeline de prensa "agente-asistido" (resumen y score automáticos) servido desde un servidor casero con rendimiento de página simple y sin JavaScript pesado. Lo que otro no puede copiar: la recopilación automatizada y clasificada específica del dominio técnico.

## Operating Context

Servicio systemd `tech-dashboard` (Flask, Python) en la Pi 192.168.100.10, puerto 8080, expuesto por túnel Cloudflare en https://tech.mipi.dpdns.org. Los datos los genera por la noche un recolector ajeno a esta app en `data/resumenes/*.{txt,json}` y en la db SQLite `data/tech_news_history.db`. Interfaz fija en español (sin sistemas de idioma). Página servida en un solo archivo `tech_dashboard.py` con minímo JavaScript inline (mostrar/ocultar resumen).

## Capabilities and Constraints

- Rutas: `/` (portada con días recientes), `/summary/<fecha>`, `/summary/<fecha>/raw`, `/db` (historial con filtro por categoría, búsqueda y paginación), `/db/<id>` (detalle + abrir original), `/feed` (RSS).
- Restricciones técnicas: sin frameworks frontend, sin bundler; debe ser ligero para la Pi; sin autenticación; todo el CSS/HTML va en el archivo Python.
- Vocabulario del producto: "resumen", "noticias", "score", "categoría", "historial".
- Decisión deliberadamente abierta: dependencia `deep-translator` en requirements.txt ya no se usa (pendiente de retirar por el usuario).

## Brand Commitments

Nombre visible: "Tech Agent" (marca en el header) / "Tech News Agent". Sin compromisos visuales vinculantes previos (el esquema oscuro "aurora" anterior es mundo incumbente que el rediseño reemplaza; se preservan contenido, función y copia del producto).

## Evidence on Hand

- Datos reales: `data/resumenes/tech-resumen-2026-09-05.{txt,json}` y la SQLite con historial.
- Despliegue público funcionando (túnel Cloudflare); el rediseño se verifica en la Pi.

## Product Principles

1. El resumen diario se lee primero y rápido; el historial es la herramienta de consulta.
2. Ligero y honesto: sin clientes pesados, sin claims inventados sobre el contenido.
3. El score es la métrica de la casa: se muestra como dato, no como decoración.
4. El español de la interfaz es fijo y consistente.
5. Accesible y con buen contraste también de día (luz real del entorno de uso).

## Accessibility & Inclusion

Sin requisito de estándar declarado por el usuario; el rediseño mantiene contrastes AA, foco visible, `prefers-reduced-motion` y navegación por teclado que ya tenía el incumbente.