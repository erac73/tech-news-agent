# Design — Tech News Agent

<!-- impeccable:design-schema -->

Mundo visual: **papel editorial** (claro). Rediseño total que reemplaza el esquema oscuro "aurora + glass". Se preservan función, contenido, copia en español y rutas.

## Escena de uso

El dueño lee el resumen diario en pantalla, de día y con luz ambiente real (no un caso de uso nocturno). Fuerza la decisión de fondo claro: papel, tinta, hairline de periódico.

## Tokens

- Papel `#f8f6f0` · panel `#efede4`
- Tinta `#20242e` · tinta suave `#4a5060` · tinta tenue `#5d6475`
- Reglas `#e1ded2` · `#c8c3b2`
- Acento editorial (rojo) `#8f2f2a` · texto sobre acento `#fbf6ec`
- Tipografía: display serif **Newsreader**; UI/cuerpo **IBM Plex Sans**; datos/fechas **JetBrains Mono** (mono solo para data, no como disfraz)
- Radios 4–6px; sombras de papel con offset real, nunca halo.

## Categorías (tintas editoriales AA sobre papel)

| Categoría | Color |
|---|---|
| Programacion | `#38523a` |
| Inteligencia Artificial | `#8c2e1d` |
| Ciencias de la Computacion | `#3f3a68` |
| Frameworks y Web | `#1e5f74` |
| Noticias Tech | `#8a5800` |
| Docker / DevOps | `#33465f` |

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