# Design — Tech News Agent

<!-- impeccable:design-schema -->

Mundo visual: **papel editorial** (claro). Rediseño total que reemplaza el esquema oscuro "aurora + glass". Se preservan función, contenido, copia en español y rutas.

## Escena de uso

El dueño lee el resumen diario en pantalla, de día y con luz ambiente real (no un caso de uso nocturno). Fuerza la decisión de fondo claro: papel, tinta, hairline de periódico.

## Tokens

Variante cromática actual: **papel de tinta nocturno** (oscuro). Misma estructura editorial; la luz de uso pasa a lectura nocturna.

- Papel `#15171d` · panel `#1d212a`
- Tinta `#e9ebf0` · tinta suave `#b6bdcb` · tinta tenue `#98a0b1`
- Reglas `#2a2f3a` · `#3e4554`
- Acento editorial (rojo) `#e25242` · texto sobre acento `#191310`
- Tipografía: display serif **Newsreader**; UI/cuerpo **IBM Plex Sans**; datos/fechas **JetBrains Mono** (mono solo para data, no como disfraz)
- Radios 4–6px; sombras de papel con offset real, nunca halo.

## Categorías (tintas editoriales AA sobre papel oscuro)

| Categoría | Color |
|---|---|
| Programacion | `#93b069` |
| Inteligencia Artificial | `#e07b56` |
| Ciencias de la Computacion | `#9a93cf` |
| Frameworks y Web | `#5fb6c8` |
| Noticias Tech | `#e0a84e` |
| Docker / DevOps | `#79a6c9` |

## Componentes

- **Masthead**: barra de papel sólida con hairline; logo "Tech Agent", marca cuadrada de tinta con serif; nav con subrayado de acento en la página activa.
- **Portada**: titular serif 2rem con regla roja animada (único momento autoral de movimiento); estadísticas como fila de datos mono separadas por reglas, sin cajas.
- **Rejilla de días (bento)**: placas de papel; la tarjeta destacada es papel puro con regla superior roja de 3px + lista de avances con hairlines.
- **Secciones**: h2 serif con cola de regla (`::after`) y punto-cuadrador de categoría.
- **Fichas de noticia**: título serif-free sans 700 1.25rem, score mono en caja de 1.5px de la tinta categoría (tinte 8% vía `color-mix`), categoría en versalitas 600, resumen a 72ch, hover con tinta más oscura.
- **Controles**: pills/inputs como sellos (hapline + fondo panel); estado activo = relleno de acento con texto crema.
- **Superficies del navegador** tematizadas: selección, caret, scrollbar, foco de 2px acento.

## Escala tipográfica

Fija en rem con pasos ≥1.25× entre roles (lectura y documentos): body 1rem → h3 1.25rem → h2 1.56rem → h1 2rem.

## Comportamiento

- Hover 150–200ms; sin secuencias de entrada; `prefers-reduced-motion` apaga transiciones, animaciones y scroll suave.
- `@media print`: caso de uso real (imprimir el resumen) — papel blanco, solo tinta.
- Responsive estructural: rejilla de días a 1 col <760px, fichas a 1 col <860px, filtros full-width en móvil.

## Documents

- `PRODUCT.md` — ficha de producto (init del skill Impeccable).
- CSS incrustado en `tech_dashboard.py` (único archivo servido).