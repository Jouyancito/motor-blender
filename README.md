# motor-blender — motor único de generación (Joan, 2026-07-17)

Blender headless como único generador de mallas 3D e imágenes 2D, compartido entre
proyectos (corpóreo Filomeno, Dungeon Party, lo que venga). Geometría separada de
estilo: una receta genera la FORMA; un preset de `lookdev/` decide cómo se PINTA.

## Estado (2026-07-17, primera consolidación)

Este folder es una **COPIA** de lo mejor probado dentro de `corporeo-3d/_motor`,
`_lookdev`, `_gate` — los originales de corpóreo NO se tocaron (su sesión de
edición seguía activa cuando se hizo esto; mover-y-borrar de verdad es el
siguiente paso, deliberado, cuando esa sesión esté tranquila). Hasta que se haga
esa migración final, este folder es la copia canónica para proyectos NUEVOS
(el juego), y corpóreo sigue usando su copia original sin cambios.

## Estructura

- **`recetas/`** — capa de GENERACIÓN. 11 técnicas de bpy verificadas en casos
  reales (no específicas de ningún proyecto): pintar por geometría, extraer
  contorno 2D, reproporcionar por perfil, líneas de tinta paramétricas, pegar
  a superficie, pose de huesos, preflight anti-explosión, etc. Índice completo
  y anti-recetas (métodos ya probados como callejón sin salida) en `RECETAS.md`
  — leerlo ANTES de escribir bpy nuevo.
- **`lookdev/`** — capa de ESTILO. `cel_banded.py` = preset ANIME/TOON, ya
  genérico (`blender -b --python cel_banded.py -- <in.glb> <out_dir>`, cualquier
  GLB sirve). `render_flat_freestyle.py` / `render_invhull_flat.py` = variantes
  de línea. `mood_valheim.py` = preset de MOOD/ATMÓSFERA (ver sección abajo).
  **Falta el preset REALISTA (PBR)** — hueco abierto.
- **`gate/`** — capa de VERIFICACIÓN. `g360_capture.py` + `gate360.py` = captura
  16 ángulos + auditoría numérica ("nunca un veredicto sin mirar"), parametrizado
  por `--object`. `_run_preflight_on_blend.py` = driver de ejemplo que corre
  `preflight_destructivo` sobre CUALQUIER .blend headless (ver prueba abajo).

## Proof-of-fire (2026-07-17)

Corrida real cross-proyecto: `preflight_destructivo` (receta de corpóreo) sobre
`game/tools/blender/golem_unify_wip.blend` (el WIP del golem del juego, un
proyecto que nunca había usado esta receta). Resultado real:

- 46 objetos mesh evaluados.
- 45 OK (todos los chunks de piedra individuales — geometría sana).
- 1 NOT SAFE: `golem_dp_body` — 61016 open edges (todas sus aristas son de
  borde, probablemente una malla no-manifold/point-cloud, no un sólido).

Sin escribir una línea de código nueva de generación, la receta ya encontró
algo real y accionable en un asset del juego. Esa es la prueba de que el
motor único sirve para más de un proyecto.

## Conocimiento de técnicas

`TECNICAS.md` — trucos observados en referencias reales (batch 2026-07-18), traducidos
a: cómo se hace, si es automatizable headless, y en qué capa de una escena encaja.
Organizado por el norte de ESCENAS COMPLETAS (presupuesto por distancia al foco).
Leerlo junto a `recetas/RECETAS.md` antes de generar escenas o elegir estilo.

## Lookdev — `mood_valheim.py` (2026-07-19)

Capa de mood REUTILIZABLE, separada de la generación de geometría: aplica una
jerarquía de luces cálida-clave/fría-relleno, bump procedural sobre los
materiales compartidos (madera/piedra/paja) sin necesitar UV unwrap, niebla
atmosférica muy sutil (World Mist Pass — se probó volumen 3D primero y
oscurecía toda la escena a escala de aldea, ver notas en el propio archivo) y
un post en compositor (glare/bloom + viñeta + grado de color derivado de los
`sun_color`/`sky` del bioma, no hardcodeado). API pública única:
`apply_mood(scene, biome_style)`. La invoca `recetas/village_gen.py` justo
antes de renderizar, activada por defecto — pasar `off` como 8vo argumento
posicional del CLI (`... -- <biome> <out> <seed> ... <mood>`) para desactivarla.

## Creation Protocol — reasoning ANTES de construir

`CREATION_PROTOCOL.md` — gate previo a `RECETAS.md`/`preflight_destructivo`: identifica la
categoría real del objeto, investiga referencias visuales (multi-fuente) Y lógica funcional
(bisagras, soportes, material según economía, tamaño según contenido) y fija dimensiones
contra el maniquí de 1.80m — ANTES de escribir bpy. Incluye auto-crítica multi-ángulo antes de
presentar. Nace del Judgment Day de `village_gen.py`/`mood_valheim.py` (v1→v12, 2026-07-18) —
leerlo junto a `RECETAS.md` antes de generar un asset/módulo nuevo.

## Próximos pasos

1. Escribir el preset REALISTA en `lookdev/` (hoy solo existe toon).
2. Migrar `game/tools/blender/` para que importe de acá en vez de reinventar
   cámara/luces/preflight (empezar por el golem de piedras flotantes).
3. Cuando la sesión activa de corpóreo esté tranquila: mover de verdad
   `_motor/_lookdev/_gate` desde `corporeo-3d/` a este folder (borrando el
   original) y apuntar `corporeo_step.py` acá — cierra la duplicación.
4. Comparar `game/tools/visual_gate/` (SSIM/IoU/ΔE propio del juego) contra
   `gate/` de acá — puede que ya sean equivalentes y uno sobre.

## Memoria (engram) — el motor es TRANSVERSAL

`.engram/config.json` declara `project_name: motor-blender` desde el 2026-09-02.
Antes decía `another-game-of-dungeon`, lo que archivaba las lecciones del motor
bajo el proyecto del juego — incorrecto, porque el motor ya se usa también para
arquitectura y para el corpóreo.

**Consecuencia que hay que conocer**: el servidor MCP de engram resuelve el
proyecto por SU PROPIO directorio de trabajo, no por la carpeta que uno está
editando. Así que el proyecto `motor-blender` recién existe cuando se abre una
sesión **desde esta carpeta**. Si trabajás el motor desde `~`, la memoria cae en
`the_j` y queda invisible para `joan-status` y para cualquier `mem_search` del
motor.

> Para trabajar el motor: abrir la sesión parado en `~/motor-blender`.

Observaciones históricas del motor anteriores a esa fecha están repartidas entre
los proyectos `another-game-of-dungeon` y `the_j`. Engram no expone borrado ni
reasignación de proyecto en la superficie MCP, así que quedan ahí; buscarlas por
`topic_key` (`motor/...`) antes que por proyecto.

## Paquete para revisión externa

El repo es privado, así que pasarle la URL a otra IA no sirve — no puede leerlo.
`python tools/make_review_bundle.py` genera `_out/MOTOR_BUNDLE.md` (~84 KB,
~22k tokens): brief + lecciones + protocolo + índice de recetas + auditorías +
una receta de ejemplo, sin el código de los generadores. Ese archivo se sube o
se pega en el chat de la otra IA. Se regenera, no se commitea.
