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

## Asset lifecycle and the harvest gate (2026-10-16)

Every modeling job goes through four doors, each one enforced by code, not by memory
(LECCIONES 1):

1. `tools/start_asset.py` -- route the subject, declare a technique per part, write
   `_motor/manifest.json`. Without it the PreToolUse hook refuses Blender runs.
2. Build through the motor (`motor_run.py` + gates). Recipes stamp their output.
3. `tools/verify_asset.py <file.blend> <manifest>` -- writes `verdict.json`; the Stop hook
   blocks the turn until it is fresh and PASS.
4. **Harvest** -- the verdict only passes if the manifest's `harvest` section says what
   this asset taught the motor. `start_asset.py` writes the section EMPTY, and an empty or
   missing section is a FAIL row (`harvest`) in the verdict. Fill it with
   `tools/harvest_asset.py`, in one of two forms:

   ```
   # (a) techniques promoted or proposed for the motor, each a checkable file:line + a why
   python3 tools/harvest_asset.py <asset>/_motor/manifest.json \
       --add rana/rana_gen.py:403-442 "decal rides the final surface with its smooth normals" \
       --status promoted --technique surface_decal
   # (b) an explicit nothing, from a CLOSED list (free text is refused)
   python3 tools/harvest_asset.py <asset>/_motor/manifest.json --none "reused_only:bvh_glue,paint_por_geometria"
   python3 tools/harvest_asset.py <asset>/_motor/manifest.json --none "asset_specific:gen.py:42"
   ```

   The gate (`recetas/harvest.py`) refuses: no section, empty section, a `none` outside the
   closed list (`reused_only:<techniques>` where every one is registered AND called with
   `part=` by a manifest generator; `asset_specific:<file:line>` of real code), entries and
   `none` together, a source that does not resolve INSIDE the asset dir or `recetas/`
   (no `..`, no foreign absolute paths, symlinks resolved), is not a `.py`, or whose lines
   do not sit inside one def/class body, a one-line `why` under 3 words, a status other
   than promoted/proposed, and a "promoted" technique that is not registered or whose
   module was first committed BEFORE the manifest was created (it was not learned here).
   A harvest problem never turns an unjudged blend (NOT_TESTED) into FAIL. It proves the question was answered with citations a
   reviewer can open; it cannot prove the answer is complete.

   Manifests written before this gate have no `harvest` section and will FAIL until one is
   added (`reused_only:` / `asset_specific:` when the asset really taught nothing new).

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

Este repo es **público** desde el 2026-09-02, así que a un revisor se le puede
pasar la URL directamente.

Aun así conviene darle además el paquete: `python tools/make_review_bundle.py`
genera `_out/MOTOR_BUNDLE.md` (~165 KB, ~43k tokens) con el pedido, el estado
actual, la capa 0 del repo consumidor, las lecciones, el protocolo, las
auditorías y los gates — **en ese orden**. Un modelo al que le das un repo lo
navega en el orden que se le ocurre, y la primera ronda de revisión demostró qué
pasa cuando lee las auditorías de agosto antes que el estado actual: dos de
cuatro revisores describieron como problema presente algo resuelto diez días
antes.

Se regenera, no se commitea (`_out/` está ignorado).
