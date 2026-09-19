# Revisión externa — ronda 2 (revisor: Fable / Opus 5)

**Fecha: 2026-09-08.** Corte de código: repo `motor-blender` en `e8e922f` + `ANALISIS_INTEGRAL_2026-09-08.md`;
repo del juego `DungeonParty-A` en su árbol de trabajo de hoy; hooks en `~/.claude/hooks`.

Estructura espejada de `PROMPT_REVISION_EXTERNA.md` para que sea comparable con las cuatro revisiones
de la primera ronda. Metodología: 71 hallazgos candidatos, cada uno sometido a dos verificadores
adversariales independientes con acceso al código; 8 refutados (sección 8), 63 sobrevivientes.
**Ninguno de los 63 quedó sin verificación adversarial**: no hay hallazgos "sin verificar" que ranquear
por debajo. Toda medición que sustenta un hallazgo se corrió con sonda de control positiva; donde el
control falló, el hallazgo se refutó.

---

## 1. Veredicto (8 líneas)

Esto es una **biblioteca de verificación bien escrita conectada a casi nada**, envuelta en una capa
documental que se auto-diagnostica mejor de lo que se auto-corrige. El rigor conceptual está en el
percentil ~95 de equipos que producen assets 3D: la taxonomía de fallos, el veredicto de cuatro
estados y `ESTADO_ACTUAL.md` son mejores que los de la mayoría de los equipos con QA formal. La
**ejecución** del rigor está en el percentil ~40: los tres gates de 2026-09-02 tienen cero call sites,
los dos hooks que sí bloquean midieron hoy una población de cero archivos, y el umbral calibrado del
único gate con número vive por debajo del piso de cuantización de su propio instrumento.
Modo de muerte más probable: **no es abandono, es rendimiento decreciente por lastre documental**.
El motor sigue produciendo assets, cada iteración cuesta más leer que construir, y en algún punto
Joan deja de cargar el canon y el motor vuelve a ser un montón de `build_*.py` con un README grande.
El segundo modo, más rápido: se cablea `require_structure()` tal como está, revienta el primer build
sobre la tortuga —su propio caso fundacional— y el gate se borra o se bypassea en dos semanas.

---

## 2. Defectos estructurales confirmados

Ordenados por gravedad. Los 63 hallazgos se agrupan en 12 bloques porque varios son la misma falla
vista desde ángulos distintos; se indica el id de cada uno para trazabilidad.

---

### D1 — Los gates que bloquean midieron hoy una población de cero, y los cuatro defectos que los motivaron son inmunes por construcción
**Gravedad: ALTA.** Ids 0, 12, 50, 63, 57. **NUEVO** (la mitad de "gate de propiedad" fue pedida por
`AUDIT_2026-08-23.md:141` y `AUDIT_ACTIVACION §8.3`; el agujero del backfill no lo dijo nadie).

`~/.claude/hooks/motor-glb-color-gate.ps1:55-57`:

> "Only git-dirty (modified or untracked) .glb files can be 'never checked': a tracked, unmodified
> file was already reviewed at commit time."

`:81` — `$glbs = $glbs | Where-Object { $dirty.Contains($_.FullName) }`. Filtro idéntico en
`motor-showcase-gate.ps1:121`.

Medición de hoy, con control positivo: `git status --porcelain -- '*.glb'` en DungeonParty-A devuelve
**0 líneas**, mientras `git status --porcelain` pelado devuelve 6 entradas (el instrumento ve) y
`git ls-files '*.glb'` cuenta **128** trackeados. En paralelo, el propio checker del gate corrido sobre
esos trackeados sale con rc=1: `SIN COLOR bird.glb 2 de 5 primitivas`, `king_slime/king_slime.glb 1 de 7`,
`snake.glb 1 de 1`, `wasp.glb 2 de 3`. Los cuatro están trackeados (`git ls-files --error-unmatch`).

Segunda mitad, independiente: `motor-blender/.gitignore:1` es `_out/`, y ese mismo directorio figura
como raíz monitoreada en `motor-glb-color-gate.ps1:28`. `git status --porcelain --untracked-files=all`
nunca lista ignorados (`git check-ignore -v _out/foo.glb` → `.gitignore:1:_out/`), así que esa raíz
**no puede producir un candidato jamás**.

**Por qué es invisible desde adentro**: el gate se escribió *porque* esos cuatro mobs salieron blancos
un mes. Un gate que nace después del defecto y filtra por "sucio" es ciego al defecto por construcción,
y cada cierre de turno en verde se lee como "el gate funciona" cuando significa "no había nada que
mirar". Es la propia lección de la casa —un cero y un instrumento roto devuelven lo mismo— aplicada al
instrumento que la implementa. Ninguno de los dos hooks imprime cuántos candidatos evaluó: hay cinco
puntos de salida silenciosa (`color-gate:45,53,82,85,88`).

**Además**: el gate de evidencia de `motor-showcase-gate.ps1:27` es un regex de nombre
(`showcase|board|ficha|g360|contact_sheet`) aplicado a las tres raíces, y `:128-138` toma el PNG
**globalmente más nuevo** y compara `if ($g -le $p) { exit 0 }`. No hay ninguna variable que ate la
evidencia al asset. Conté 66 PNGs que matchean el patrón sólo bajo `game/tools/blender`: cualquiera de
ellos, regenerado para otro asset, satisface el gate para todos. Y `$glbRoots` (`:15-18`) **no incluye**
`game/tools/blender`, que es donde ocurre todo el flujo de mobs, aunque `$pngRoots` sí lo incluye.

**Consecuencia si no se corrige**: "committed = reviewed" es falso para todo lo anterior al 2026-08-23,
los cuatro archivos blancos siguen con nombre canónico junto a sus gemelos `_vcol.glb` sanos
(`wasp.glb` 19-jul junto a `wasp_vcol.glb` 23-ago), y una copia a mano del archivo equivocado reintroduce
el mes blanco sin que nada pueda notarlo. Hoy nadie carga esos GLB en el juego, así que es una mina, no
una herida abierta — pero es exactamente la mina que el motor ya pisó una vez.

**Arreglo**: (a) backfill único de `_glb_color_check.py` sobre `git ls-files '*.glb'`, arreglar o borrar
los cuatro; (b) manifiesto de sha256 chequeados, para que "ya revisado" sea una propiedad y no un estado
de git; (c) imprimir el conteo de candidatos en cada corrida; (d) agregar `game/tools/blender` a
`$glbRoots` y exigir que el PNG de evidencia contenga el basename del GLB; (e) para la raíz `_out`, usar
mtime o `--ignored`. **Costo: S** (b y d suman M si se hace el manifiesto completo).

---

### D2 — Los gates del 2026-09-02 no tienen un solo call site, y los 26/26 verdes cubren exactamente los gates que no pueden frenar nada
**Gravedad: ALTA.** Ids 3, 27, 35, 14, 60, 61, 22, 10. **YA DICHO A MEDIAS** por `ESTADO_ACTUAL.md:50`
(sólo `require_structure`/`require_technique`) y por la revisión externa del 2026-09-02 ("reglas escritas
que nada hace cumplir"). **NUEVO**: el bloqueo real, la omisión de `material_swatch`, y que la suite verde
se cite como capa de verificación.

`ESTADO_ACTUAL.md:50`:

> "`require_structure()` / `require_technique()` | `recetas/` | **Escritos y probados, todavía no
> cableados a ningún generador del juego**"

Grep sobre `DungeonParty-A/game/tools` con control positivo (`import bpy` = 90 archivos;
`require_use_size` = 6 hits reales en `build_river_segment.py:67/1744`, `_v3.py:66/1427`, `_v4.py:66/1589`):
`require_structure|require_technique|assert_materials_vary|material_swatch|preflight_destructivo|require_complete`
→ **0 call sites**. Dentro del motor los únicos llamadores son `tools/test_gates.py` y un driver manual.
`test_gates.py:27-30` importa `verdict`, `asset_spec`, `preflight_router` y nada más. Corrí la suite hoy:
26/26 ok.

Dos precisiones que el propio `ESTADO_ACTUAL` no hace:

1. **`material_swatch` figura en la tabla "Implementado y verificado" (`:31`) sin la salvedad**, y
   `LECCIONES.md:251` dice "falla el build si no". Tiene cero llamadores en ambos repos y cero fixtures.
   La suite que se escribió *porque cuatro revisores criticaron `material_swatch`* (`test_gates.py:6-11`)
   es la única que nunca lo importa. Y el bloqueo declarado para importarlo es falso: `assert_materials_vary`
   (`material_swatch.py:186-253`) no toca `bpy` — sólo el `import bpy` de módulo en `:50` lo impide.
   Mover ese import adentro de `_cube`/`render_swatches`/`_measure` son dos líneas.
2. **Cablear `require_structure()` hoy revienta todos los builds.** No es un hueco de agenda, es un hueco
   de datos, y eso no está escrito en ningún lado. Corpus: 84 carpetas, 83 `_synthesis.md`,
   3 `_motion_spec.md`, **0 specs estructurales**. Ejecutado en vivo: `find_spec('.../\_references/turtle')`
   devuelve `turtle\motion\_motion_spec.md` (porque `_motion_spec.md` está en `SPEC_BASENAMES`,
   `asset_spec.py:61`), `parse_structure` devuelve 0 filas, y `require_structure(turtle, ['humerus_L','neck','head'])`
   → `SystemExit "3 propiedad(es) SIN EVIDENCIA"`. **El gate hace SystemExit sobre el asset que su propio
   encabezado (`:16-19`, `:38-42`) cita como caso fundacional y ejemplo de uso.**

**Por qué es invisible desde adentro**: el 26/26 es real y se corre sin Blender, así que produce la
sensación de una capa de verificación operativa. `ESTADO_ACTUAL.md:76`, el README del bundle y el commit
`1ffee21` lo citan como evidencia. Pero prueba la lógica de tres funciones, no que ningún camino de build
las alcance. Es la lección 14 del propio motor ("lo escrito no es lo gateado") una capa más abajo: los
gates ya son código, la **llamada** sigue siendo prosa.

**Consecuencia**: cualquier `blender -b --python turtle/build_turtle.py` corre sin gate de estructura,
de técnica ni de variación de material. Cuando vuelva el fallo del pelo (dos técnicas descartadas
construidas el 2026-08-22) o el de la tortuga (sin renglón estructural), el post-mortem va a volver a
decir "el gate existía".

**Arreglo**: un solo call site en `build_mob.py` (ya conoce el nombre del mob y ya encadena
build → color → truth, `:74-104`), **precedido** por escribir el primer `_structure_spec.md` de la tortuga
con las 7 partes móviles que `preflight_router.py:80-81` ya enumera. Fixture en `test_gates.py` que grepee
`build_mob.py` por las tres llamadas para que descablear no sea silencioso. **Costo: M.**

---

### D3 — Después de la purga de texturas, village_gen renderiza los tres biomas del mismo tan, y el docstring certifica el estado como intencional
**Gravedad: ALTA.** Ids 24, 39, 9. **NUEVO** (`CREATION_PROTOCOL §5` marcó el bug vecino de `jitter_tone`
en 2026-07-21; la regresión post-purga no está reportada en ningún lado).

`recetas/village_gen.py:686` — `def mat_textured(key, slug, scale=2.0, projection='top', fallback_color=(0.45, 0.40, 0.32), …, tint=None)`.
`:746` — `bsdf.inputs["Base Color"].default_value = (*fallback_color, 1.0)`, incondicional.
La cadena de textura *y el nodo de tint* viven adentro de `if diff_img is not None:` (`:764`) → `if tint is not None:` (`:772`).
`mat()` (`:920-932`) rutea `ground`, `roof_thatch`, `roof_thatch_dark`, `wood`, `wood_dark` a `mat_textured`
pasando `tint=color` y **nunca** `fallback_color`; la rama de `ground` ni siquiera pasa tint. Enumeré los
10 call sites de `mat_textured` (924, 926, 928, 930, 932, 2420, 3356, 3404, 3406, 3438): **ninguno** pasa
`fallback_color`, así que también caen piedra de casona, sendero y plaza.

`_textures/` no existe en disco (`.gitignore:10-13`), así que `_tex_path` devuelve `None` para todo slug.
Resultado: suelo, paja, madera, piedra, sendero y plaza salen `(0.45,0.40,0.32)` en pradera, bosque **y
hielo** — el suelo de nieve del bioma hielo renderiza tan. Y como el tint sí entra en la clave de caché
(`:741`), `jitter_tone` genera N materiales byte-idénticos: el bug que `CREATION_PROTOCOL` marcó en julio
volvió, y el comentario `:906-917` sigue diciendo que ya no es código muerto.

El docstring `:689-695` dice:

> "`_textures/` was emptied on purpose … every call here takes the `fallback_color` path and renders flat.
> **That is a supported state, not a bug.**"

Y `:893-898` va más lejos: afirma que "the per-house `jitter_tone()` tint … is what makes wood visually
distinct per house/biome in the meantime" — una mitigación que la guarda de `diff_img` hace estructuralmente
imposible.

**Por qué es invisible desde adentro**: la purga (`3f5a91d`, 2026-09-01) dice en su propio mensaje
"Safe by construction … Verified the fallback path before deleting". Esa verificación probó que **no
crashea**, no que se **vea** bien. El render más nuevo de village en `_out/` es `village_v18a_test`
(2026-07-26), cinco semanas anterior a la purga: nadie miró. Es la regla "Look Before You Report" violada
en el acto mismo de purgar, y el commit que crea la regresión edita el comentario que desvía el diagnóstico.

**Consecuencia**: el próximo render de village vuelve plano *y con el color equivocado*, y el arco v1–v11
("todo se lee como color sólido", once rondas) se reinicia — esta vez con el doc afirmando que el estado
es el esperado. Además `build_tree_pack.py:101` sigue hardcodeando `POLYHAVEN_DIR = C:\Users\the_j\motor-blender\_textures`,
y su caché `_tex/` está gitignoreada: desde un clone limpio ese generador crashea en tiempo de import.

**Arreglo**: pasar `fallback_color=color` en cada rama de `mat()` (una línea por rama), borrar la cláusula
falsa del comentario `:893-898`, y agregar un assert de 10 líneas al final del build: `Base Color` de
`ground_hielo` ≠ `ground_pradera`, o `len(set(base_colors)) > 1`. Después **renderizar hielo una vez y
mirarlo**. **Costo: S.**

---

### D4 — El ciclo atómico juzga un artefacto que el juego no carga, y el documento de estado lo describe con una garantía que el código no da
**Gravedad: ALTA.** Ids 69, 1, 15, 37. **NUEVO** (la atomización fue pedida por `AUDIT_ACTIVACION §8.5`;
se implementó y después se sobre-declaró).

`ESTADO_ACTUAL.md:29`:

> "Corre `_glb_truth_render.py` con `--python-exit-code 1` y hace `return rc` hacia `sys.exit`.
> **Es fail-closed**, no una herramienta invocable a mano"

La primera mitad es verdad (`build_mob.py:76-104`). La segunda la contradice el propio archivo:
`:31` importa `argparse`, `:66-72` define el posicional `mob` y `--skip-build`, `:16` imprime la invocación
a mano. Nada lo invoca: ningún hook en `~/.claude/settings.json` lo referencia, y `_mob_pipeline.md`
—el doc que `CLAUDE.md:111` llama "el primer doc que se abre"— tiene 0 menciones de `build_mob`,
`_glb_color_check` o truth render (control: 9-12 hits de "gate" en el mismo archivo). Los timestamps de
`_truth/` prueban que **sí se corrió a mano** varias veces desde el 08-23 (rat 24-ago, turtle_dp_01 24-ago,
golem_guardian 27-ago), que es justo lo que la frase niega.

La mitad grave es la cobertura: `find_glb` (`:52-57`) hace glob sobre `game/tools/blender/<mob>/*.glb` y
devuelve el más nuevo. Pero `_deploy.py:40` declara el origen de la tortuga como `turtle/turtle.glb`, que
ya no existe; lo único que queda en `turtle/` es `turtle_vcol.glb` (22-ago 23:55, 890 KB), mientras el juego
carga `game/assets/art/piso1_pradera/enemies/small/turtle_dp_01.glb` (25-ago 00:50, 16.2 MB). `hawk/` no
tiene ningún `.glb` (`find_glb('hawk')` → `SystemExit "el build no dejó ningún .glb"`), y no existe
`hawk_TRUTH.png`. Para `slime`, `find_glb` agarraría `king_slime.glb` por mtime.

**Por qué es invisible desde adentro**: `build_mob.py` se escribió el 08-23; `_deploy.py` movió tortuga y
halcón a `assets/art` el 08-24/25 — un día después. El ciclo quedó apuntando al lugar viejo y nunca se
notó porque nunca falló ruidosamente: para la tortuga **pasa en silencio sobre un archivo obsoleto de agosto**.
Un gate que aprueba el artefacto equivocado sin decirlo es peor que no tenerlo.

**Consecuencia**: `ESTADO_ACTUAL.md:29` es la fila que responde la crítica más fuerte de dos revisores, en
el documento escrito para que se le crea por encima de las auditorías. Es la afirmación con más chance de
ser re-auditada en la ronda 2, y es falsa en su cláusula portante.

**Arreglo**: `find_glb` consulta `_deploy.DEPLOY` primero y cae al glob sólo si el builder no está en DEPLOY;
fallar si existen ambos con sha256 distinto. Reescribir `:29` como "ciclo atómico fail-closed **cuando se
invoca**; el respaldo que no se puede olvidar es el Stop hook `motor-glb-color-gate.ps1`" — hook que la
tabla "Implementado" omite por completo. Agregar `build_mob.py` a la fase 4 de `_mob_pipeline.md`. **Costo: S.**

---

### D5 — El umbral 0.00010 de material_swatch está por debajo del piso de cuantización de su propio instrumento
**Gravedad: ALTA.** Id 48 (+10, 22, 61). **NUEVO** — `ESTADO_ACTUAL.md:92-94` advierte sobre resolución,
cámara, denoiser y tamaño de feature; **nunca menciona profundidad de bits**, que es el mecanismo real.

`render_swatches` escribe `scene.render.image_settings.file_format = 'PNG'` (`material_swatch.py:124`) y
en todo el archivo no hay un solo `color_depth` (grep con control: el único `image_settings` es `:124`).
Blender default = PNG de 8 bits. `_measure` recarga ese PNG con `bpy.data.images.load` (`:158`) y calcula
`detail` como mediana de |diferencias| en luminancia 0-1 (`:176-178`).

Recalculé el tamaño lineal de **un paso de código de 8 bits** en esa luminancia:
0.000304 en sRGB 0.031 · 0.000762 en 0.125 · 0.001591 en 0.251 · **0.003666 en 0.502**.

La calibración publicada (`:199-203`, y reproducida en `ESTADO_ACTUAL.md:66-72`) es:
CONTROL 0.00000 · slab 0.00028 · floor 0.00083 · wood 0.00112 · column 0.00364.

**Los cinco puntos caben dentro de un solo paso de cuantización**, y "column (la más fuerte) 0.00364" es
exactamente 1 LSB en gris medio. El margen que el docstring `:205` declara ("below the weakest REAL material
by ~3x and above the uniform control") es un margen de menos de un valor de código del instrumento. Y la
única explicación causal que el archivo da del 0.00000 del control (`:206-211`: el denoiser) queda no
identificada: la cuantización explica lo mismo y nunca se controló. Súmese que `render.dither_intensity`
default 1.0 nunca se desactiva, o sea que se inyecta ruido de escala LSB justo en las superficies planas
que el gate debe rechazar.

**Por qué es invisible desde adentro**: la tabla de cinco puntos *parece* una banda medida. Se publica bajo
"Medido, no estimado". Nadie miró qué resolución tiene el instrumento antes de leer la banda.

**Consecuencia**: `detail < 0.00010` no es un umbral calibrado, es el test binario "¿más de la mitad de los
pares de píxeles caen en el mismo byte?". Funciona como detector plano/texturado por accidente; no funciona
como la banda continua que el doc presenta. El día que se cablee, un límite no testeado pasa a ser portante.

**Arreglo**: `color_depth = '16'` (una línea) o leer los floats de `Render Result` sin round-trip a archivo;
re-medir los cinco materiales y **publicar los números nuevos**. Mover `import bpy` adentro de las tres
funciones que lo usan y agregar fixtures sin Blender: control 0.00000 debe FALLAR, 0.00028 debe PASAR, un
valor a caballo del umbral, y `exempt` como lista o string debe lanzar. **Costo: S.**

---

### D6 — El truth render existió para los mobs blancos un mes antes del diagnóstico, y nunca se registró un veredicto contra él
**Gravedad: ALTA.** Id 54. **NUEVO** (Perplexity pidió un ledger de feedback; esto es su mitad interna).

Listado de `game/tools/blender/_truth/` hoy: `snake_TRUTH.png` (2026-07-29 23:44), `wasp_TRUTH.png` (23:44),
`king_slime_TRUTH.png` (23:45), slime, rat, turtle, turtle_dp_01, golem_*. **No hay `bird_TRUTH.png`.**
Abrí `snake_TRUTH.png` (no confié en una métrica): se ve una serpiente **blanca pura** junto al maniquí de
1.80 m; control positivo, `slime_TRUTH.png` del mismo tool muestra un slime claramente verde. El defecto de
los mobs blancos se diagnosticó el 2026-08-22 (`motor-glb-color-gate.ps1:5`). **24 días con la prueba
fotográfica en disco.**

`_truth_report.txt` tiene hoy exactamente una fila (`golem_guardian True 25 18392 6.96m`) porque
`_glb_truth_render.py:239-240` lo abre en modo `'w'`: cada corrida destruye el ledger anterior.
`build_mob.py` termina en `:109` con `print("  MIRALO:  %s" % shot)` y no registra si alguien miró.

Nota metodológica que confirma la tesis: una sonda de saturación media era **ciega** acá (todos los archivos
dan ~0.27 porque el fondo lila domina el cuadro). Sólo abrir la imagen resolvió.

**Por qué es invisible desde adentro**: el pipeline trata "el render existe" como el final del loop. Un
render producido-y-no-leído es indistinguible de un check aprobado. `LECCIONES 14` ahora se lee como si el
truth render hubiera cerrado el ciclo; lo que lo cerró fue un check de propiedad agregado un mes después.

**Consecuencia**: cualquier afirmación futura de la forma "truth-rendered" no lleva información sobre si un
humano miró, y como el reporte se sobrescribe, tampoco es auditable después.

**Arreglo**: modo append en `_truth_report.txt` (un carácter) más un campo que nadie pueda autocompletar:
quién calificó y qué dijo. Un render sin calificador registrado es un renglón `NOT_TESTED` en un
`verdict.Report` — `verdict.py` ya modela exactamente ese estado y no tiene productor en producción. **Costo: S.**

---

### D7 — El cero que justifica asset_spec.py es un artefacto del instrumento: la investigación estructural de la tortuga existe y el gate no puede verla
**Gravedad: ALTA.** Id 47 (+58, 60). **NUEVO**.

`asset_spec.py:20-25` y `LECCIONES.md:223` reportan "84 carpetas / 83 `_synthesis.md` / 3 `_motion_spec.md` /
**0 specs estructurales**", y `:16-19` concluye sobre la tortuga: "no fue una falla de verificación: no había
nada que verificar".

El instrumento es `SPEC_BASENAMES = ("_structure_spec.md", "_spec.md", "_motion_spec.md")` (`:62`) recorrido
por `find_spec` (`:71`). Sonda de control corrida hoy sobre el corpus vivo:
`grep -rl "## *STRUCTURE\|## *ESTRUCTURA" --include=*.md` → **3 carpetas** (turtle, turtle_aquatic,
turtle_terrestrial); control positivo `grep -rl "^## "` → 77 archivos, o sea la sonda ve.
`turtle/_synthesis.md:197` es literalmente `### ESTRUCTURA — plano, ángulo y límite por parte móvil`,
escrito el 2026-08-24, con `UPPER_LIMB_PLANE horizontal`, `HUMERUS_PITCH -13 a -2°`, `ELBOW_ABOVE_HORIZ 62-74°`,
`RETRACTION_LIMITER = el puente carapacho-plastrón`, con fuente en *J. Exp. Biol.*

Se apilan **tres** cegueras: (1) `find_spec` nunca abre `_synthesis.md`; (2) `parse_structure` corta en el
primer subtítulo (`if line.startswith("#"): break`, `:111-112`) mientras la tabla real vive bajo
`#### Miembros` en `:204`; (3) las tablas de la tortuga son de **tres** columnas (`| Parámetro | Valor | Fuente |`)
y `parse_structure` exige `len(cells) >= 4` (`:107-108`). Corpus y gate no discrepan sólo en el nombre del
archivo: discrepan en el esquema.

**Por qué es invisible desde adentro**: el 0 es literalmente cierto bajo la definición del gate. Lo que nunca
se hizo fue la sonda de control sobre el censo que motivó el gate — la regla de la casa aplicada al número
que justifica la obra.

**Consecuencia**: el primer intento honesto de cablear el gate va a leer "el corpus está vacío" por segunda
vez, sobre el caso fundacional, y el reflejo va a ser borrar o bypassear. Además el censo mide conformidad de
nombre de archivo, no ausencia de investigación: hay 2 `_motion.md` más que el censo tampoco cuenta
(`slime_tensura/motion/`, `turtle_terrestrial/motion/`), y `SPEC_BASENAMES` tampoco los ve.

**Arreglo**: antes de cablear, correr el gate contra las 84 carpetas y **publicar la distribución** — ese es
el control positivo y es un loop. Después, o (a) `find_spec` cae a cualquier `*.md` con encabezado
STRUCTURE/ESTRUCTURA, `parse_structure` escanea hasta el siguiente encabezado de nivel igual o mayor y acepta
3 columnas; o (b) se declara `_structure_spec.md` único hogar legal y se migran las tres carpetas de tortuga
primero. En cualquier caso, **sacar `_motion_spec.md` de `SPEC_BASENAMES`**: aceptar un spec de movimiento
como spec estructural garantiza `NOT_TESTED` para las tres carpetas que tienen uno. **Costo: M.**

---

### D8 — La evidencia con la que se refuta a dos revisores no está en el repo público al que se los manda
**Gravedad: ALTA.** Id 64 (+59). **NUEVO**.

`LECCIONES.md:229-233`:

> "dos de los cuatro modelos afirmaron que `_glb_truth_render.py` *'no está en ningún gate'*. Es falso
> desde el 2026-08-23 — `build_mob.py` lo corre fail-closed."

La refutación es correcta en sustancia (`build_mob.py:87-104` verificado). Pero `PROMPT_REVISION_EXTERNA.md:95-99`
le dice al revisor: "El repo completo es público … Si una crítica necesita ver un generador entero, andá al
repo", y `git ls-files` en `motor-blender` (58 archivos, control OK) devuelve **cero** hits para
`build_mob|glb_color|truth_render|bake_vcol`. Esos cuatro archivos viven en el repo privado del juego, y los
dos Stop hooks —la única aplicación fail-closed que corre sin que nadie se acuerde— viven en `~/.claude/hooks`,
fuera de todo repo (o sea: sin versionar y sin backup).

Lo que **sí** viaja en el bundle (`make_review_bundle.py:50-66`) es `material_swatch.py`, `verdict.py`,
`asset_spec.py`, `preflight_router.py`: exactamente los cuatro que no tienen llamador en producción.
La asimetría es perfecta — el revisor sólo puede leer lo que no dispara.

Agravante en la parte 1 del bundle: `BRIEF_REVISION_EXTERNA.md:30` (escrito el 2026-09-02, **para** la ronda 2)
sigue diciendo "El preflight tiene 8 puntos", y `:35` titula "Los 13 patrones de fallo" mientras su propio pie
(`:147`) dice "LECCIONES.md (14 lecciones)". `make_review_bundle.py:27-31` pone ese archivo primero por diseño:
"Someone who stops reading after part 1 has still got the ask".

**Consecuencia**: un revisor que sigue la instrucción y no encuentra nada va a repetir razonablemente el
hallazgo de la ronda 1, y el motor va a volver a anotarlo como error del revisor. El costo de la revisión se
paga dos veces.

**Arreglo**: vendorizar copias read-only de `build_mob.py`, `_glb_color_check.py`, `_glb_truth_render.py` y
los dos `.ps1` al repo público (o sumarlos a `EXTERNAL_PARTS`, que ya implementa el manejo "la ausencia es un
warning" en `:69-79`). Actualizar §1 del BRIEF a 10 puntos y §2 a 14 patrones, y agregar en
`make_review_bundle.py` un assert que falle el bundle si esos conteos discrepan de `CLAUDE.md`/`LECCIONES.md`
— el mecanismo ya existe (`:112-117` falla ruidosamente ante partes faltantes). **Costo: S.**

---

### D9 — El gate de paridad sha256 cubre 2 de 4 destinos declarados, y una entrada faltante es un PASS silencioso
**Gravedad: ALTA.** Ids 62, 8, 23, 56. **YA DICHO A MEDIAS**: los cuatro revisores pidieron grafo de
procedencia por hashes (`ESTADO_ACTUAL.md:103-106`, listado como **totalmente** aplazado). **NUEVO**: que la
mitad ya está construida y cubre la mitad.

`motor-showcase-gate.ps1:56` — `foreach ($prop in $manifest.PSObject.Properties)`. La cobertura del gate es
igual a lo que el manifiesto ya contiene: un destino ausente nunca se hashea y nunca bloquea.
`_deploy_manifest.json` tiene **2** claves (`hawk_dp_01.glb`, `turtle_dp_01.glb`); `_deploy.py:39-45` declara
**4** destinos (turtle, slime, king_slime, hawk) y los cuatro archivos existen en disco.
`build_slime.py` no importa `_deploy` (exporta directo en `:923`), lo mismo `build_king_slime.py:382`.

Peor: el propio docstring de `_deploy.py:59-64` afirma que el hook "BLOCKS if they differ **or the entry is
missing**" — cláusula que el `foreach` no puede implementar. Y `audit()` (`:137-138`) tiene el mismo agujero
(`if entry is not None and ...`), así que el instrumento manual es ciego en la misma dirección que el automático.

`slime_dp_01.glb` y `king_slime_dp_01.glb` están cargados por tres escenas vivas (`slime.tscn:4`,
`mini_slime.tscn:4`, `king_slime.tscn:5`). Hoy no hay deriva (mismos tamaños y md5 que las copias del builder,
ambos 30-jul), pero el próximo rebuild de slime sin `export_glb` desincroniza en silencio: **exactamente el
fallo por el que se escribió `_deploy.py`** ("la tortuga pasó dos builds obsoleta en el juego sin que nada
pudiera notarlo").

**Consecuencia**: "no medido" puntúa como "aprobado" para la mitad de los mobs desplegados, dentro del gate que
implementa la recomendación estructural más votada de la ronda 1. Y presentar esa recomendación como 100 %
aplazada esconde que el paso barato que falta es poblar dos filas.

**Arreglo**: tratar un destino de `DEPLOY` sin fila de manifiesto como `NOT_TESTED` y bloquear (o al menos
avisar); re-exportar slime y king_slime por `_deploy.export_glb`; imprimir la cobertura en cada corrida
("parity: 2/4 declarados"). Agregar una línea a la sección aplazada de `ESTADO_ACTUAL` diciendo que la mitad
"deploy obsoleto" del grafo de procedencia ya está cubierta desde el 2026-08-25. **Costo: S.**

---

### D10 — Los gates fallan abierto en los bordes: técnica desconocida pasa, celda placeholder pasa, bake rechazado pasa, GLB ilegible pasa
**Gravedad: MEDIA.** Ids 5, 46, 67, 52, 2, 4, 49, 6, 26. **NUEVO**.

Cuatro fugas del mismo tipo — `NOT_TESTED` leído como `PASS` — dentro de los módulos que importan `verdict.py`,
escrito para eliminar ese patrón:

1. **Router.** `preflight_router.py:194-195` — `if not rules.matched: return rules`. Sin excepción, sin reporte.
   Probado en vivo: `require_technique('escorpion del piso 1','polygon_shells')` → PASS;
   `('un lobo','uv_sphere_painted')` → PASS. Y `route()` es matching de substring sin anclar, primer match en
   orden de diccionario (`:177-181`): `route('modelar furniture de madera')` → **pelo** ("fur" en "furniture"),
   `route('un woodpecker')` → material_procedural, `route('la carapace del escarabajo')` → quelonio.
   Además la normalización (`:198`) sólo cambia `-` y espacios por `_`, así que `shell_offset` pasa mientras
   `offset shell` lanza: dos escrituras de la misma técnica descartada, veredictos opuestos.
   **Dato que importa para el plan**: probé los sujetos del plan de cableado de `ANALISIS_INTEGRAL:91`
   (slime, king_slime, golem) — los tres routean a `None`. Cablear el router mañana a esos tres generadores
   produce tres gates que no pueden dispararse nunca, con la suite en verde.
2. **asset_spec.** `:155` — `empty = [c for c in REQUIRED_COLUMNS if not row[c]]`. Sólo el string vacío cuenta
   como sin responder. Probado: un spec con `| humerus_L | ? | ? | ? |` y `| head | TBD | n/a | - |` da
   `PASS`, `is_complete = True`, sin `SystemExit`. Y `:183-187` **imprime la plantilla de remediación
   `"  | %s | ? | ? | ? |"`**: el gate reparte la fila que lo derrota. Como hay 0 specs reales, el primero que
   se escriba bajo presión va a ser ese.
3. **Color/bake.** `_glb_color_check.py:83` aprueba por *presencia* de `COLOR_0`; `_bake_vcol.py:115`
   `flatten_to_base_colour` existe explícitamente para que un bake rechazado no falle el gate y escribe un gris
   fijo `(0.55,0.55,0.58)`, indistinguible de un tono plano deliberado; y un bake que corre pero no captura
   nada imprime `"<-- PLANO"` (`:162-164`) y **retorna normal**. Decodifiqué los accessors: `bird_vcol.glb`
   pasa "5/5 primitivas pintadas" con tres primitivas de spread de luma **0.0000**; `turtle_vcol` prim1/prim2
   dan 0.0407 / 0.0381, a 2x de la propia línea "PLANO" del módulo. `_glb_color_check` además falla abierto en
   ilegible (`:73-75` "no se juzga"), cero mallas (`:90-91`) y path inexistente (`:106`).
4. **Código de salida.** Todo `SystemExit` in-build es advisory salvo que Blender arranque con
   `--python-exit-code 1`. Ese flag aparece en **código** sólo en `build_mob.py:77` y `:99`; en los otros 33
   archivos vive en comentarios y docstrings, incluida la Run line de `build_river_segment.py:40-42`.
   Y `village_gen.py:5009-5014` traga toda la capa de mood, `mood_valheim.apply_mood:906-933` traga sus siete
   pasos uno por uno, `mood_valheim.py:268` tiene un `except Exception: pass` pelado — un render que perdió
   iluminación, niebla o compositor sale con exit 0.

**Consecuencia**: cada uno de estos convierte un gate en un sello. El del router es el más caro porque es el
próximo paso del plan; el de la plantilla `?` es el más barato de cerrar y el más probable de ocurrir.

**Arreglo**: `require_technique` lanza (o devuelve un `Report` que el llamador debe `require_complete()`)
cuando no matchea, salvo `unknown_ok='<razón>'`; anclar aliases a palabra completa; normalizar las claves
descartadas a conjunto de tokens. `asset_spec` rechaza celdas que plieguen a `?`/`tbd`/`n/a`/`-`/`todo`/
`pendiente` y exige dígito u orientación en ANGULO; la plantilla de error muestra una fila real.
`_bake_vcol` etiqueta el material de fallback (`_FALLBACK_FLAT`) y `_glb_color_check` lo reporta FAIL;
"PLANO" pasa a valor de retorno; ilegible/sin mallas/faltante = FAIL. Un launcher único
(`tools/motor_run.py`) que siempre agregue `--background --factory-startup --python-exit-code 1`, y esa
la única Run line documentada. **Costo: S cada uno, M el launcher.**

---

### D11 — Las cifras retractadas siguen emitiéndose como "Medido" por los dos únicos archivos que se cargan solos
**Gravedad: MEDIA.** Ids 16, 42, 51, 66, 20. **YA DICHO** por los cuatro revisores (`ESTADO_ACTUAL.md:83-95`),
**corregido sólo en el documento que no se carga**.

`DungeonParty-A/CLAUDE.md:90-92` (capa 0, inyectado cada sesión): "Medido el 2026-08-23: … sólo el **2,5 %**
se carga solo … las 4 piezas que se cargaban solas funcionaron y **las 5 que había que ir a buscar fallaron**".
`LECCIONES.md:16-18` repite lo mismo bajo "Medido:". `ESTADO_ACTUAL.md:85-91` retracta ambas
("no es una medición de activación … n=9, elegido retrospectivamente … clasificado por el propio sistema
auditado").

La tesis del motor es que PUSH gana porque PULL depende de que alguien se acuerde. La corrección se aplicó al
documento PULL y se salteó en los dos PUSH: **el motor le garantizó circulación máxima a la cifra que ya no
sostiene**. En el mismo bloque, `CLAUDE.md:105` describe `LECCIONES.md` como "las 11 formas de equivocarse"
cuando tiene 14, y `CLAUDE.md:83-85` hace lo mismo a escala menor ("Cinco de cinco", n=5, un solo calificador,
generalizado a regla dura).

**Arreglo**: bajar el caveat de ESTADO a los dos archivos PUSH ("indicio, n=9, autoclasificado") o borrar las
cifras y quedarse con la afirmación cualitativa, que no necesita denominador. Derivar el conteo de lecciones
al construir el bundle (`make_review_bundle.py:38` ya dice "Las 14 lecciones completas"). **Costo: S.**

---

### D12 — Deuda estructural de código: acoplamiento por nombre, RNG compartido, índice de recetas incompleto, y punteros de línea podridos dentro del único gate que bloquea
**Gravedad: MEDIA-BAJA.** Ids 28, 31, 33, 25, 29, 44, 45, 17, 18, 70, 13, 21, 68, 43, 41, 55.
Parcialmente **YA DICHO** por `CREATION_PROTOCOL` (anti-patrones) y `README` (próximos pasos).

Lo que cambia decisiones, en orden:

- **`RECETAS.md` es el índice de retrieval ("leerlo entero antes de escribir bpy nuevo: si existe receta, SE USA")
  y omite 12 de 27 archivos de `recetas/`**, incluidos `use_size.py` (que `ESTADO_ACTUAL:30` lista como gate
  implementado), `village_gen.py`, `glb_export.py` y los cinco `biome_*`. El fallo que el índice existe para
  prevenir ya ocurrió N=5 para `export_glb` (`gen_golem:528`, `gen_golem_chunks:647`, `gen_crystal:185`,
  `_deploy:102`, `gen_golem_dressing:278` junto a `recetas/glb_export.py:30`) y N=3 para `finalize_mesh`.
  **Arreglo**: generar la tabla desde los docstrings (`tools/gen_recetas_index.py`) + fixture que falle si un
  `recetas/*.py` no está en la tabla. **Costo: S.** Esta es la mejor relación impacto/costo del bloque.
- **`mood_valheim` promete idempotencia y no la tiene**: `:903-904` dice "every step is idempotent by
  construction", pero `:329` multiplica `o.data.energy` y `:354` la fuerza de emisión sobre el valor actual en
  cada llamada. Como `village_gen.py:5088` **guarda el .blend con el mood ya horneado**, reabrir y re-aplicar
  duplica energías. Además el acoplamiento con `village_gen` es por substring de nombre de material y de luz
  (`:516-541`, `:326-328`) en un módulo cuyo encabezado se declara "generator-agnostic". **Costo: S**
  (guarda `mood_applied` + propiedad custom `motor_family`).
- **Punteros de línea podridos dentro del gate que bloquea**: `motor-showcase-gate.ps1:7,159` cita
  "CREATION_PROTOCOL.md:126-131, blender-asset-smith:175". Hoy `:124-133` es el bloque de assert del codo de la
  tortuga y `SKILL.md:175` es "## Reproducibility harness" — la regla real vive en `CREATION_PROTOCOL §5`
  (`:198-200`). Mismo puntero en `motor-bash-blender-reminder.ps1:34`. `CREATION_PROTOCOL` invierte igual:
  presenta como CONFIRMADO-abierto el bug de `mood_valheim._seed` que se arregló el 2026-07-21
  (`mood_valheim.py:74-93`, `zlib.crc32`) mientras sus otros dos anti-patrones estrella siguen vivos
  (`build_goat` en `village_gen.py:3630` sigue siendo cuerpo propio; `USE_REAL_TEXTURES` en `:902` sigue sin
  CLI) y sus números de línea están corridos 700-2900 líneas. **Arreglo**: citar por sección, no por línea, y
  etiquetar cada ejemplo `FIXED <fecha>` / `OPEN`. **Costo: S.**
- **Acoplamiento por stream de RNG compartido en `village_gen`**: para no correr el orden de draws
  (`:342-354`) se mantienen vivas una copia pre-v18 de la empalizada en `build_destacamento` (`:4810-4827`,
  todavía con `primitive_cone_add`, sin `add_stake_top`) y un loop en `build_coop` (`:3753-3761`) que sólo
  quema draws de un `build_chicken` borrado. Cada feature nueva forkea el código o agrega no-ops. El arreglo
  correcto (stream por builder con `crc32((SEED, módulo, i))`, el mismo truco que `mood_valheim._seed:74-93`
  ya usa) **reordena el layout de la semilla 7**, que es justo lo que `detail_rng` compró. **Costo: M, con
  riesgo visual**; no es prioridad hoy.
- **Cosas ciertas y de bajo retorno**: `village_gen.py` es un script-dios de 5.097 líneas que ejecuta al
  importar (imposible de testear o de usar desde un gate); `clown_gen.py` duplica `mat`/`shot`/maniquí;
  hay tres formas distintas de la "referencia de 1,80 m"; `biome_facet.add_stone_aggregate` devuelve el conteo
  de piedras mal apoyadas (60-80 %) sin aserción — pero **no tiene un solo llamador** fuera de su test, así que
  no envía nada (lo que sí falta es una línea en anti-recetas); `engordar_anatomico.py` hardcodea el rig de
  Filomeno dentro del motor genérico; el proyecto engram `motor-blender` **no existe** en el store aunque
  `README.md:91` lo declara desde el 2026-09-02.

---

**Cobertura de severidad**: 15 hallazgos ALTA (D1-D9), 28 MEDIA (D10-D12 y dispersos), 20 BAJA.
0 hallazgos sin verificación adversarial.

---

## 3. Auditoría de la tesis central

**Tesis**: *"casi ningún fallo es de conocimiento sino de verificación — instrumento equivocado, momento
equivocado, pregunta equivocada"*.

### El mejor caso EN CONTRA

**(a) La taxonomía está sesgada por el observador.** Las 14 lecciones fueron escritas por el sistema que
fallaba, después del fallo, y la categoría "verificación" es la única que tiene remedio barato y ejecutable
por un agente LLM. Un fallo de conocimiento se remedia investigando; uno de alcance, recortando; uno de
criterio estético, decidiendo. Ninguno de los tres produce un `.py` commiteable en la misma sesión. La tesis
podría ser un artefacto de *qué tipo de remedio es escribible*, no de qué tipo de fallo ocurre.

**(b) Hay al menos tres clases del historial que no son de verificación.**
- *Reversiones no registradas como reversiones*: v12 (2026-07-20, `fa30ed1`) declara las texturas CC0 reales
  como el arreglo de "todo se lee como color sólido"; `3f5a91d` (2026-09-01) las borra sin generador de
  reemplazo. Ambas están escritas como decisiones positivas y nada las une. Ningún instrumento habría
  detectado eso: es una decisión que se dio vuelta, y el costo es que el próximo render plano se lee como
  regresión en vez de consecuencia.
- *Deriva de alcance silenciosa*: el norte declarado en julio (instrucción/boceto → escena 3D coherente,
  dispatch en lenguaje natural, capa de contexto) no se reformuló nunca; el motor se volvió una biblioteca de
  scripts por asset. No hubo un instrumento equivocado: hubo un objetivo abandonado sin acta.
- *Ausencia de criterio estético explícito*: el arco v14→v16 (tres rondas de "sigue pálido" que el muestreo de
  píxeles desmintió) y las cinco decisiones bespoke-vs-pack bloqueadas desde el 2026-08-25 no se resuelven con
  mejor métrica. Se resuelven con un criterio escrito o con un veredicto humano, y el segundo tiene cola.

**(c) La tesis se auto-inmuniza.** Si todo fallo es de verificación, la respuesta siempre es "otro gate", y el
motor ya demostró que agregar gates sin cablearlos no cambia nada (D2). Peor: la tesis convive con su propia
refutación en el archivo. `asset_spec.py:16-19` dice de la tortuga "no fue una falla de verificación: no había
nada que verificar. La especificación estaba incompleta" — o sea, un fallo de conocimiento, admitido, en el
encabezado del gate escrito para la tesis contraria.

**(d) El único fallo real de conocimiento del último mes es el que más costó y no está en la taxonomía**:
nadie sabía que el PNG de 8 bits de Blender pone un piso de cuantización arriba de la banda de calibración de
`material_swatch` (D5). No fue el instrumento equivocado ni el momento equivocado: fue no saber cómo funciona
el instrumento elegido.

### Veredicto

**La tesis es sustancialmente correcta y está mal enunciada.** Sobrevive porque los casos que la sostienen son
verificables y caros: cuatro mobs blancos un mes con la prueba fotográfica en disco (D6); la desviación
estándar sobre cubos midiendo sombreado de caras y no textura; el gate de showcase midiendo existencia de PNG
en vez de propiedad del artefacto. Eso es un patrón real, medido y pagado.

Pero el enunciado correcto no es "los fallos son de verificación": es **"los fallos son de activación, y la
verificación es la única capa de activación que el motor sabe construir"**. La lección 1 ya dice esto
("si una regla necesita que yo me acuerde de ir a buscarla, ya falló") y es la más fuerte del set. La tesis de
la verificación es su corolario, no su generalización — y confundirlas produce exactamente el estado de hoy:
cinco gates escritos, cero cableados, 26/26 en verde, y la única aplicación que corre sin que nadie se acuerde
son dos hooks de PowerShell que la tabla "Implementado" ni menciona.

**Corrección concreta al enunciado**: agregar una decimoquinta lección, *"una reversión que no se registra como
reversión reaparece como regresión"*, con el caso `fa30ed1` → `3f5a91d` y la sección "Reversiones" en
`ESTADO_ACTUAL`. Es la clase de fallo que ningún gate puede atrapar y que ya costó once rondas una vez.

---

## 4. Contraste con las cuatro IAs externas

### Dónde coincido

1. **Números auto-reportados**: coincido con los cuatro. Y agrego el mecanismo que ninguno nombró: el problema
   del 0.00010 no es "n=1", es que la banda entera cabe en un paso de cuantización de 8 bits (D5). Es una
   crítica más barata de accionar que "recalibrá con más casos": es una línea.
2. **Grafo de procedencia por hashes en vez de marcas de tiempo**: coincido con los cuatro, y **corrijo el
   registro**: la mitad ya está construida desde el 2026-08-25 (paridad sha256 en `motor-showcase-gate.ps1:44-82`)
   y cubre 2 de 4 destinos. `ESTADO_ACTUAL.md:103-106` la lista como totalmente aplazada. El paso barato que
   falta no es el grafo: son dos filas de manifiesto (D9).
3. **Contrato de aceptación por asset** (ChatGPT): coincido, y señalo que la primitiva ya existe y no tiene
   productor. `verdict.Report` se construye en tres recetas y no lo emite ningún build. "Un reporte con
   NOT_TESTED no aprueba" no tiene dónde dispararse hoy.
4. **Ledger de feedback del cliente** (Perplexity): coincido, y su mitad interna es más urgente que la externa
   — no hay campo que registre **quién calificó** un artefacto (D6). `_deploy_manifest.json` guarda sha256 y
   tamaño, no calificador.

### Dónde discrepo

1. **Discrepo con la refutación del motor a dos revisores.** `LECCIONES.md:229-233` tiene razón en la sustancia
   (`build_mob.py` sí es fail-closed) y se equivoca en dar el asunto por cerrado: la evidencia no está en el
   repo público al que el prompt manda al revisor (D8), y el ciclo apunta a un artefacto obsoleto para tortuga
   y a ninguno para halcón (D4). La afirmación de `ESTADO_ACTUAL.md:29` que se les opuso es falsa en su
   cláusula portante.
2. **Discrepo con la razón dada para aplazar las cuatro obras grandes.** `ESTADO_ACTUAL.md:111-112`: "los tres
   cambios baratos que sí se hicieron verifican primero si el diagnóstico compartido es cierto". No pueden
   verificar nada: los tres tienen cero call sites (D2). El aplazamiento puede ser correcto por costo, pero el
   argumento que lo sostiene está vacío hasta que un build llame a un gate.
3. **Discrepo con el análisis interno de hoy** (`ANALISIS_INTEGRAL_2026-09-08.md:91`, acción #1: cablear
   `require_structure()` y `require_technique()` a `build_slime.py` + `build_king_slime.py` + `build_golem.py`).
   Tal como está, esa acción produce **tres gates inertes**: `route('slime')`, `route('king_slime')` y
   `route('golem')` devuelven `None`, y `require_technique` sobre un sujeto no ruteado retorna en silencio
   (D10.1). Y `require_structure` sobre cualquiera de los tres hace `SystemExit` porque hay 0 specs (D2/D7).
   El orden correcto está en el plan de la sección 6.
4. **Discrepo con el rechazo del SSIM** (registrado sólo en engram: `cv2.compare_ssim` no existe, `skimage`
   ausente). El código de ejemplo estaba mal; la métrica no. La ruta real es `cv2.quality.QualitySSIM_compute`.
   Que la refutación viva sólo en memoria y no en disco deja la pregunta 4 del brief **sin respuesta registrada**,
   y va a volver a preguntarse.

### Qué se les pasó a los cuatro

- **Que los gates que bloquean miden una población de cero** (D1). Ninguno lo podía ver: los hooks no viajan en
  el bundle. Es el hallazgo con mejor relación gravedad/costo de toda esta revisión.
- **El piso de cuantización bajo el umbral calibrado** (D5). Los cuatro atacaron el n=1; ninguno miró la
  profundidad de bits del instrumento.
- **Que el censo que justifica `asset_spec.py` es un artefacto de nombre de archivo** (D7). Los cuatro
  aceptaron el "0 specs estructurales" como dato.
- **Que el truth render de los mobs blancos existía un mes antes del diagnóstico** (D6). Nadie preguntó quién
  miró.
- **Que la mitad de su recomendación #1 ya estaba construida** (D9) — culpa del paquete, no de ellos.
- **Que la parte 1 del bundle de la ronda 2 sigue describiendo el preflight de 8 puntos y 13 patrones** (D8),
  o sea que la ronda 2 arranca sembrando la misma medición vieja que `ESTADO_ACTUAL` existe para impedir.

---

## 5. Dónde el motor se engaña

Todo lo de esta sección sale de la dimensión de validez de medición y está verificado ejecutando, no leyendo.

1. **"El gate de color está registrado como hook" → verde que no significa nada.** Cinco puntos de salida
   silenciosa, candidatos filtrados a git-dirty, población medida hoy = 0. Un hook silenciosamente roto produce
   señal idéntica a un hook sano. Nadie mide el conteo de candidatos (D1).
2. **"26/26 ok (6 controles positivos)" citado como capa de verificación.** Los 6 negativos cubren `verdict`,
   `asset_spec` y **una** técnica descartada del router. El clasificador del router no tiene ningún fixture de
   falso positivo, y probado en vivo confunde "furniture" con pelo y "woodpecker" con material procedural. La
   suite mide que el router reproduce su propia tabla de aliases (D10.1, id 52).
3. **"Medido, no estimado" sobre la tabla de calibración.** Los cinco puntos caben en un paso de código de
   8 bits. La banda parece medida y es un artefacto de redondeo (D5).
4. **"specs estructurales: 0" leído como "nadie investigó estructura".** Mide conformidad de formato. La
   investigación estructural de la tortuga existe desde el 2026-08-24 con fuente en *J. Exp. Biol.* y el gate
   no puede verla por tres cegueras apiladas (D7).
5. **"Truth render obligatorio".** Obligatorio significa "el archivo se produce". No hay campo para quién lo
   juzgó, y el reporte se sobrescribe, así que la afirmación no es auditable después (D6).
6. **`require_use_size`: "sin la evidencia en el tamaño real de uso, el build falla"** (`ESTADO_ACTUAL:30`).
   `use_size.py:43-46` lanza sólo `FileNotFoundError`/`ValueError`: falla si **no hay render**, no mide nada de
   la imagen, y los tamaños son argumento del llamador. La parte medida elige la medición. Los tres call sites
   reales pasan `[1280, 640, 320]`; el caso fundacional (la mascota slime invisible) apareció a 72 px (id 55).
7. **`_glb_color_check`: "30 de 34 GLB OK" leído como "30 assets pintados".** Significa "30 declaran una fuente
   de color". Y existe una ruta documentada (`flatten_to_base_colour`) que fabrica esa declaración cuando el
   pipeline se rindió con el patrón. Decodifiqué los accessors: tres primitivas de `bird_vcol.glb` tienen spread
   0.0000 y el gate las cuenta como pintadas (id 49).
8. **Paridad sha256: "OK" es un enunciado sobre dos archivos leído como enunciado sobre el arte del juego**
   (D9). Cobertura 2/4 declarados; nadie la imprime.
9. **Gate de showcase: dos mtimes y un regex de nombre como proxy de "alguien miró este asset desde varios
   ángulos"** — un proxy sin variable para "este asset" (D1, id 57).
10. **El censo del corpus cuenta nombres de archivo exactos.** Mi primera sonda (`ls */_motion_spec.md`) dio 0
    porque los specs viven un nivel más abajo; sólo la recursiva recuperó los 3. Hay además 2 `_motion.md` que
    el censo no cuenta y que `SPEC_BASENAMES` tampoco ve. Cualquier cifra "N de 84" en estos documentos hay que
    asumirla como medición de conformidad de nombre hasta que un control diga lo contrario (id 58).
11. **Las cifras retractadas siguen circulando por los dos archivos PUSH y la retracción vive en el PULL**
    (D11). El motor le dio circulación máxima al número que ya no sostiene.

---

## 6. Priorización

Ordenado por impacto/costo. "Tiempo a efecto" = cuándo se puede *observar* el cambio, no cuándo se termina.

| # | Intervención | Impacto | Costo | Tiempo a efecto | Prioridad |
|---|---|---|---|---|---|
| 1 | Imprimir conteo de candidatos en ambos Stop hooks | Alto | S (1 línea c/u) | Inmediato | **P0** |
| 2 | Backfill de color sobre `git ls-files '*.glb'` + borrar/reemplazar los 4 blancos | Alto | S | 1 sesión | **P0** |
| 3 | `find_glb` lee `_deploy.DEPLOY`; reescribir `ESTADO_ACTUAL:29` | Alto | S | 1 sesión | **P0** |
| 4 | `mat()` pasa `fallback_color=color` + assert de biomas + render de hielo mirado | Alto | S | 1 sesión | **P0** |
| 5 | `material_swatch`: `color_depth='16'`, re-medir, publicar banda nueva | Alto | S | 1 sesión | **P0** |
| 6 | Cerrar los fail-open de borde (router, placeholders, PLANO, ilegible) | Alto | S×4 | 1-2 sesiones | **P1** |
| 7 | Escribir el primer `_structure_spec.md` (tortuga, 7 partes de `preflight_router:80-81`) | Alto | S | 1 sesión | **P1** |
| 8 | Arreglar `find_spec`/`parse_structure` (o migrar) + censo publicado como control | Alto | M | 1 sesión | **P1** |
| 9 | Cablear los 3 gates en `build_mob.py` (un solo call site) + fixture anti-descableo | Alto | M | 2 sesiones | **P1** |
| 10 | Manifiesto de sha256 chequeados (sustituye "committed = reviewed") | Alto | M | 2 sesiones | **P1** |
| 11 | `_truth_report.txt` en append + campo `graded_by` | Medio-alto | S | Inmediato | **P1** |
| 12 | Poblar manifest de deploy para slime/king_slime; entrada faltante = bloqueo | Medio-alto | S | 1 sesión | **P1** |
| 13 | Vendorizar los 5 archivos de enforcement al repo público + assert de conteos en el bundle | Medio-alto | S | Antes de ronda 3 | **P1** |
| 14 | Evidencia del showcase gate atada al basename del GLB + `game/tools/blender` en `$glbRoots` | Medio | S | 1 sesión | **P2** |
| 15 | Bajar el caveat de las cifras a `CLAUDE.md` y `LECCIONES.md`; "11 formas" → generado | Medio | S | Inmediato | **P2** |
| 16 | Fixtures sin Blender de `assert_materials_vary` (mover `import bpy`) | Medio | S | 1 sesión | **P2** |
| 17 | `RECETAS.md` generado + fixture que falle ante recetas ausentes | Medio | S | 1 sesión | **P2** |
| 18 | Guarda `mood_applied` + propiedad `motor_family` en vez de substrings | Medio | S | 1 sesión | **P2** |
| 19 | Launcher único con `--python-exit-code 1` como única Run line documentada | Medio | M | 2 sesiones | **P2** |
| 20 | Citar por sección (no por línea) en hooks y `CREATION_PROTOCOL` + tags FIXED/OPEN | Bajo-medio | S | Inmediato | **P3** |
| 21 | Sección "Reversiones" en `ESTADO_ACTUAL` + lección 15 | Bajo-medio | S | Inmediato | **P3** |
| 22 | Anti-receta escrita para `add_stone_aggregate` (60-80 % mal apoyadas) | Bajo | S | Inmediato | **P3** |
| 23 | Abrir una sesión parada en `~/motor-blender` para que exista el proyecto engram | Bajo | S | Inmediato | **P3** |

### Lo que NO haría

- **No refactorizar `village_gen.py`** (5.097 líneas, script-dios). Costo L, generador dormido desde el
  2026-07-26, y el argumento que lo justificaría ("las 11 rondas de tuneo se pagaron a precio de render
  completo") no sobrevive al log: v12-v18 fueron rondas de juicio visual que necesitaban render igual. El único
  beneficio concreto —importar `mat()` para assertear que los biomas difieren— ya se consigue con el assert de
  módulo que el archivo usa en `:5090-5095`.
- **No extraer `primitives.py` todavía.** Es M de costo mecánico y no cambia ningún outcome de asset. La parte
  valiosa de ese hallazgo es el índice generado (#17), que es S.
- **No re-keyear los streams de RNG por builder.** Es correcto arquitectónicamente y **reordena el layout de la
  semilla 7**, que es exactamente lo que `detail_rng` compró. Pagar ese costo cuando village vuelva a estar
  activo, no antes.
- **No cablear `material_swatch` antes de recalibrar el umbral.** Cablear un gate cuyo límite está por debajo
  del piso del instrumento convierte un problema latente en bloqueos aleatorios.
- **No construir el grafo de procedencia completo** mientras el manifiesto que ya existe tenga 2 de 4 filas.
- **No hacer un gate de renders por mtime.** El hook de showcase ya registra un falso bloqueo por esa vía
  (`slime_dp_01.glb`, commiteado y limpio, bloqueó un turno el 2026-07-30 porque Godot le reescribió el mtime).
  Si se cierra el agujero de assets-cuyo-producto-es-un-render, que sea por hash + calificador, no por reloj.
- **No consolidar los tres maniquíes de 1,80 m** ni parametrizar `build_sheep`/`build_goat`. Cero efecto visible.

### Lo que conviene DEJAR de hacer

1. **Dejar de citar "26/26" como evidencia de que existe una capa de verificación.** Es evidencia de que tres
   funciones sin llamador se comportan como dicen. Citarlo con esa precisión, o no citarlo.
2. **Dejar de publicar "2,5 %" y "4/4 vs 5/5" bajo la palabra "Medido"** en los archivos que se cargan solos.
3. **Dejar de escribir docstrings que certifican un estado como "a supported state, not a bug"** sin un render
   abierto que lo respalde. `village_gen.py:689-695` es el caso: certifica como intencional una regresión que
   nadie miró.
4. **Dejar de sobrescribir `_truth_report.txt`.** Destruye la única evidencia auditable de qué se juzgó.
5. **Dejar de citar por número de línea** dentro de gates, hooks y protocolos. Ya hay tres punteros podridos y
   uno vive en el texto de bloqueo del único gate que frena.
6. **Dejar de responder a un fallo escribiendo otro documento.** Desde el 2026-08-10 el motor lleva 7 commits
   de docs contra 3 de código en su propio repo. `AUDIT_ACTIVACION:234-236` lo dice mejor que yo: "cada vez que
   la respuesta sea escribamos esto en un doc, el doc va a ser bueno y el fallo va a volver".

---

## PLAN DE IMPLEMENTACIÓN INMEDIATA

Cinco intervenciones, en orden de ejecución, con criterio de aceptación ejecutable. Están escritas para que un
agente las tome tal cual. Cada una es autónoma: ninguna depende de la siguiente.

---

### 1. Hacer visible y honesta la población que los gates miden — y vaciarla de verdad
**Cierra**: D1 (ids 0, 12, 50, 63, 57).

**Cambios de archivo**
- `~/.claude/hooks/motor-glb-color-gate.ps1`: agregar `Write-Host "[color-gate] candidatos: $($glbs.Count) (trackeados: $trackedCount)"` antes del filtro de dirty y antes de cada salida temprana (`:45,53,82,85,88`). Para la raíz `motor-blender/_out`, reemplazar el filtro de git por mtime (esa raíz está gitignoreada y no puede producir candidatos nunca).
- `~/.claude/hooks/motor-showcase-gate.ps1`: mismo print; agregar `game/tools/blender` a `$glbRoots` (`:15-18`); en `:128-138`, exigir que el PNG de evidencia contenga el basename del GLB candidato.
- Repo del juego: correr `python game/tools/blender/_glb_color_check.py $(git ls-files '*.glb')`; para cada uno de los 4 que salen SIN COLOR — `bird_prey/bird.glb`, `snake/snake.glb`, `wasp/wasp.glb`, `king_slime/king_slime.glb` — o promover el `_vcol.glb` hermano al nombre canónico, o borrar el archivo blanco. `bird_vcol.glb` (5/5) y `wasp_vcol.glb` (3/3) ya pasan.
- Nuevo `game/tools/blender/_checked_manifest.json`: `{ "<ruta>": {"sha256": ..., "checked": "<fecha>", "rc": 0} }`, escrito por `_glb_color_check` cuando corre con `--record`.

**Criterio de aceptación**
- `python _glb_color_check.py $(git ls-files '*.glb')` sale **rc=0**.
- Los dos hooks imprimen el conteo de candidatos en **todas** sus rutas de salida (verificable corriendo cada hook a mano con el árbol limpio: debe decir "candidatos: 0", no salir mudo).
- Un `.glb` blanco escrito a mano en `motor-blender/_out/` **bloquea** el cierre de turno (hoy no puede).
- Un PNG llamado `grass_pack_showcase.png` regenerado **no** desbloquea un `turtle_dp_01.glb` sucio.

---

### 2. Que el ciclo atómico juzgue el archivo que el juego carga
**Cierra**: D4 (ids 69, 1, 15, 37).

**Cambios de archivo**
- `game/tools/blender/build_mob.py:52-57` — `find_glb` consulta primero `_deploy.DEPLOY`: si el mob tiene destino declarado, devolver `asset_path(destino)`; si no, caer al glob de carpeta. Si existen ambos con sha256 distinto → `SystemExit` con los dos paths.
- `build_mob.py:109` — además del `MIRALO:`, escribir la fila en `_truth_report.txt` en modo append (ver #5) .
- `ESTADO_ACTUAL.md:29` — reescribir la fila: *"Ciclo atómico fail-closed **cuando se invoca** (`build_mob.py`). El respaldo que no se puede olvidar es el Stop hook `motor-glb-color-gate.ps1`."* Agregar una fila nueva a la tabla "Implementado" para los dos hooks, con su filtro de dirty y sus archivos de bypass declarados como deuda.
- `game/docs/art/_mob_pipeline.md` fase 4 — nombrar `build_mob.py` como la única forma sancionada de construir un mob.

**Criterio de aceptación**
- `python game/tools/blender/build_mob.py turtle --skip-build` corre el check y el truth render sobre `game/assets/art/piso1_pradera/enemies/small/turtle_dp_01.glb` (16.2 MB, 25-ago), **no** sobre `turtle/turtle_vcol.glb` (890 KB, 22-ago).
- `python build_mob.py hawk --skip-build` **no** lanza "el build no dejó ningún .glb"; genera `_truth/hawk_TRUTH.png`, que hoy no existe.
- `rg build_mob game/docs/art/_mob_pipeline.md` devuelve ≥1 hit (hoy 0, con control: "gate" da 9).

---

### 3. Devolverle el color a los biomas y poner el assert que lo habría atrapado
**Cierra**: D3 (ids 24, 39, 9).

**Cambios de archivo**
- `recetas/village_gen.py:920-932` — agregar `fallback_color=color` a las cinco ramas (`ground`, `roof_thatch`, `roof_thatch_dark`, `wood`, `wood_dark`). Idem en los call sites de casona/sendero/plaza (`:2420, :3356, :3404, :3406, :3438`).
- Alternativa equivalente y más robusta en `mat_textured:746`: `bsdf.inputs["Base Color"].default_value = (*(tint if tint is not None else fallback_color), 1.0)`.
- `:893-898` — borrar la cláusula que afirma que `jitter_tone` mantiene la variación por casa; es falsa mientras no haya textura.
- `:689-695` — reescribir el docstring: el estado plano es soportado, el **color** plano único no.
- Nueva función `audit_biome_colors()` llamada al final del build, junto a los asserts que ya viven en `:5090-5095`: falla si `_mats['ground_hielo']` y `_mats['ground_pradera']` tienen el mismo Base Color, o si `len(set(base_colors)) == 1`.
- `game/tools/blender/tree_pack/build_tree_pack.py:101` — si `POLYHAVEN_DIR` no existe y no hay caché, `SystemExit` con mensaje, en vez de un error crudo de `bpy.data.images.load` en tiempo de import.

**Criterio de aceptación**
- El assert nuevo **falla hoy** contra el código actual (control positivo: si no falla, el arreglo no era necesario o el assert no mide).
- Después del fix, `blender -b --python recetas/village_gen.py -- hielo _out/hielo_check` sale rc=0 y el assert pasa.
- **Un humano abre el render de hielo y confirma que el suelo no es tan.** Este paso no es opcional ni sustituible por la métrica: es la lección "Look Before You Report" en el commit que la violó.

---

### 4. Cablear los gates en UN punto — después de arreglar sus tres entradas
**Cierra**: D2, D7 y D10.1 (ids 3, 27, 35, 60, 47, 2, 5, 46, 52, 67). **Orden obligatorio**: si se cablea antes,
revienta sobre la tortuga y el gate se termina borrando.

**Cambios de archivo, en este orden**
1. `recetas/asset_spec.py:61` — sacar `_motion_spec.md` de `SPEC_BASENAMES`; agregar fallback a cualquier `*.md` con encabezado `STRUCTURE`/`ESTRUCTURA`. `:111-112` — escanear hasta el siguiente encabezado de nivel igual o mayor, no hasta el primer `#`. `:107-108` — aceptar filas de 3 columnas (`Parámetro | Valor | Fuente`) además de 4.
2. `recetas/asset_spec.py:155` — rechazar celdas que plieguen a `?`, `tbd`, `n/a`, `-`, `todo`, `pendiente`, o de menos de 4 caracteres; exigir dígito u orientación reconocida en ANGULO. `:183-187` — la plantilla de error muestra una fila **real**, no `| parte | ? | ? | ? |`.
3. `recetas/preflight_router.py:194-195` — `require_technique` lanza `SystemExit` cuando `not rules.matched`, salvo `unknown_ok='<razón>'`. `:177-181` — anclar aliases a palabra completa. `:198` — normalizar la clave descartada a conjunto de tokens para que `shell_offset` y `offset shell` colisionen. `:46-50` — borrar la afirmación falsa de que `_references/hair_polygon_shells/` "TODAVÍA la recomienda": lleva el encabezado de descarte desde el 2026-08-23.
4. Escribir `game/docs/art/_references/turtle/_structure_spec.md` con las 7 partes móviles de `preflight_router.py:80-81`, tomando los valores que ya están en `turtle/_synthesis.md:197-243`.
5. Correr el censo sobre las 84 carpetas y publicar la distribución en `ESTADO_ACTUAL` (ése es el control positivo del gate).
6. `build_mob.py`, antes del BUILD: `preflight_router.require_technique(mob, tecnica_declarada)` y `asset_spec.require_structure(ref_dir(mob), partes)`; después del TRUTH: `verdict.require_complete(report)`.
7. `tools/test_gates.py`: fixtures nuevos — celda placeholder debe FALLAR; sujeto no ruteado en `require_technique` debe lanzar; `route('furniture de roble')` **no** debe dar `pelo`; `route('woodpecker')` **no** debe dar `material_procedural`; y un fixture que grepee `build_mob.py` por las tres llamadas.

**Criterio de aceptación**
- `python -c "from recetas import asset_spec; asset_spec.require_structure('<ref>/turtle', ['humerus_L','neck','head'])"` → **PASS** (hoy: `SystemExit "3 propiedad(es) SIN EVIDENCIA"`).
- `require_technique('un lobo', 'lo que sea')` → `SystemExit` (hoy: PASS silencioso).
- Un spec con `| humerus_L | ? | ? | ? |` → `SystemExit` (hoy: PASS, `is_complete=True`).
- `python tools/test_gates.py` → ≥32/32 con ≥11 entradas malas conocidas.
- `python build_mob.py turtle` corre end-to-end en verde; `python build_mob.py slime` **falla** con un mensaje que dice qué falta (no hay spec de slime) — eso es la señal correcta, no un problema.

---

### 5. Sacar `material_swatch` del piso de cuantización y darle su primer fixture
**Cierra**: D5 (ids 48, 10, 22, 61) y la mitad medible de D6.

**Cambios de archivo**
- `recetas/material_swatch.py:124` — agregar `scene.render.image_settings.color_depth = '16'` y `scene.render.dither_intensity = 0.0`. Alternativa mejor: saltear el round-trip a archivo y leer los floats de `bpy.data.images['Render Result']` en `_measure`.
- `:50` — mover `import bpy` adentro de `_cube`, `render_swatches` y `_measure`, para que `assert_materials_vary` sea importable sin Blender (no usa bpy).
- `:235` — avisar (o fallar) cuando una clave de `exempt` no matchea ningún nombre de stat.
- Re-correr la cosecha de calibración y **reemplazar** la tabla en `:199-203` y en `ESTADO_ACTUAL.md:66-72`, declarando explícitamente la profundidad de bits usada.
- `tools/test_gates.py` — fixtures sin Blender: `detail=0.00000` debe FALLAR; el material real más débil de la banda nueva debe PASAR; un valor a caballo del umbral; `exempt` como lista o string debe lanzar.
- `game/tools/blender/_glb_truth_render.py:239-240` — abrir `_truth_report.txt` en `'a'` y agregar dos columnas: `graded_by`, `verdict`. Sin calificador → fila `NOT_TESTED`.

**Criterio de aceptación**
- `python -c "from recetas.material_swatch import assert_materials_vary"` funciona **sin Blender** (hoy falla en `import bpy`).
- `python tools/test_gates.py` incluye ≥4 casos de `assert_materials_vary` y sigue en verde.
- La banda re-medida a 16 bits está publicada, y o bien los materiales se separan ≥1 orden de magnitud (el umbral era correcto por accidente) o colapsan (el gate nunca tuvo resolución). **Cualquiera de los dos resultados es un resultado**; lo que no es aceptable es dejar la banda vieja.
- `_truth_report.txt` conserva las filas de corridas anteriores y toda fila sin `graded_by` se reporta como `NOT_TESTED`.

---

## 7. Predicciones falsables

1. **Si se cablea `require_structure()` a `build_mob.py` sin tocar antes `SPEC_BASENAMES`/`parse_structure` ni
   escribir el primer spec**, el primer build (tortuga) va a salir con `SystemExit "3 propiedad(es) SIN
   EVIDENCIA"` y en menos de 2 semanas el gate va a estar comentado, bypasseado o borrado. *Si en cambio pasa
   en verde, mi lectura de `asset_spec.py:61-77` y `:107-112` es incorrecta y D7 se cae.*

2. **Si se pone `color_depth='16'` y se re-mide la cosecha**, los cinco materiales se van a separar al menos un
   orden de magnitud respecto de la tabla actual (control sigue en 0.00000; `column` sube por encima de 0.01).
   *Si vuelven a caer todos dentro de un factor 2 de 0.0003, la cuantización no era el mecanismo dominante y D5
   estaba mal diagnosticado.*

3. **Si se imprime el conteo de candidatos en los dos Stop hooks**, en las próximas 20 sesiones la mayoría de
   los cierres de turno va a reportar 0 candidatos. *Si reportan >0 habitualmente, mi afirmación de que los
   gates miden una población vacía es falsa y D1 pierde su mitad más fuerte.*

4. **Si se corre `village_gen.py` sobre hielo, pradera y bosque tal como está hoy**, los tres suelos, la madera
   y la paja van a salir del mismo tan `(0.45,0.40,0.32)`. *Si salen distintos, leí mal el flujo
   `tint`/`fallback_color` y D3 es falso.*

5. **Si el bundle v3 sale sin vendorizar `build_mob.py`, `_glb_color_check.py`, `_glb_truth_render.py` y los
   dos `.ps1`**, al menos un revisor de la ronda 2 va a volver a afirmar que el truth render no está en ningún
   gate, o que no hay enforcement automático. *Si ninguno de los cuatro lo dice, la verificabilidad del repo
   público no era el mecanismo del falso positivo de la ronda 1 y D8 pierde su justificación.*

---

## 8. Hallazgos refutados

Ocho candidatos murieron en verificación. Se listan para que nadie los vuelva a levantar.

1. **"`biome_facet` embarca 60-80 % de piedras mal apoyadas en river_segment"** — REFUTADO en el impacto.
   `add_stone_aggregate` no tiene llamador fuera de `_test_biome_facet.py:84`; `river_segment` importa
   `add_faceted_rock` y `flat_shade`. El defecto visual es real (abrí `renders_facet/facet_playereye.png`: enjambre
   flotante y una chimenea), pero no envía nada. Lo que corresponde es una línea en anti-recetas, no un gate.
2. **"Rutas hardcodeadas: `build_tree_pack` embarca árboles sin bark maps en silencio"** — REFUTADO.
   `_cache_resized:167-173` devuelve el caché antes de tocar `POLYHAVEN_DIR`, y el caché existe. En un clone
   limpio **crashea ruidosamente**, no en silencio. Queda como sub-ítem de D3.
3. **"El contrato de 1,80 m no se asserta"** — REFUTADO. `village_gen.py:1845` es un clamp duro
   (`door_h = max(1.90, min(wall_h - 0.30, 1.98))`): más fuerte que un assert, porque no puede violarse.
   Y la sonda que decía "0 archivos con referencia de escala en el repo del juego" era ciega: hay 9 archivos con
   `_add_scale_reference()` construyendo un `BoxMesh(0.35, 1.8, 0.35)`.
4. **"~40 % de `village_gen` es changelog en docstrings"** — REFUTADO por valor. El docstring dañino es el de
   `mat_textured`, que ya lo retira D3. El resto es costo de mantenimiento en un script dormido; el fixture
   propuesto (grepear prosa por frases) sería un detector de novedad textual, no un gate de comportamiento.
5. **"Los hooks saltean commiteados → los 4 blancos se envían de nuevo"** — REFUTADO en la ruta de fallo.
   `_deploy.export_glb` escribe directo en `game/assets/art`, que es raíz #1 de ambos hooks, y el archivo recién
   escrito está sucio. La mitad verdadera ya está contada una vez en D1.
6. **"El costo por iteración lo domina leer la propia prosa; el último mes agregó prosa más rápido que código"**
   — REFUTADO por instrumento ciego. Midió sólo `motor-blender`. En `DungeonParty-A` desde el 2026-08-10 hay
   72 commits (27 feat, 9 fix vs 25 docs) y 27.650 líneas de código contra 6.542 de markdown. La carga de
   lectura es real; el "más prosa que código" no.
7. **"El único gate con número calibrado nunca juzgó nada fuera de su escena de calibración, y ESTADO no lo
   advierte"** — REFUTADO en su mitad distintiva. `ESTADO_ACTUAL.md:92-94` lo advierte casi textualmente.
   Lo que sobrevive (cero llamadores) ya está en D2.
8. **"El criterio de éxito de la revisión —3-5 predicciones falsables por revisor— se exigió y no se registró"**
   — REFUTADO por inversión temporal. `PROMPT_REVISION_EXTERNA.md` es el prompt de la ronda **2**
   (`63cedfe`, 2026-09-02, escrito después de que volvieran las respuestas de la ronda 1); su propia línea 102
   dice "en la primera ronda esto no estaba aclarado". No falta nada de una ronda que no se corrió con ese prompt.

---

## 9. Confianza por sección

| Sección | Confianza | Por qué |
|---|---|---|
| 1. Veredicto | Media-alta | El diagnóstico técnico está verificado; el percentil de rigor y el modo de muerte son juicio comparativo, no medición. |
| 2. Defectos (D1-D9, alta gravedad) | **Alta** | Cada uno reproducido ejecutando código, decodificando GLB o abriendo renders, con sonda de control positiva; dos verificadores independientes por hallazgo. |
| 2. Defectos (D10-D12, media-baja) | Media-alta | Los hechos están verificados; el orden entre ellos es juicio de impacto y varios son deuda preventiva sin fallo pagado. |
| 3. Tesis central | Media | El caso en contra es sólido y verificable; el veredicto ("es un corolario de la lección 1, no una generalización") es una lectura, no un dato. |
| 4. Contraste con las 4 IAs | Media-baja | Las respuestas completas de los cuatro revisores **no están en disco ni en engram**; trabajé sobre el destilado de `ESTADO_ACTUAL` y de la observación #2677. Las preguntas 3 y 6 del brief no tienen respuesta registrada en ningún lado. |
| 5. Dónde el motor se engaña | **Alta** | Es la sección con más medición directa: aritmética de cuantización recalculada, accessors decodificados, renders abiertos, sondas con control. |
| 6. Priorización + plan | Media-alta | Los criterios de aceptación son ejecutables y falsables; las estimaciones S/M/L son juicio. El orden obligatorio del punto 4 sí está verificado (probé que cablear hoy revienta). |
| 7. Predicciones | Media | Diseñadas para ser falsables, cada una con su condición de refutación explícita. |
| 8. Refutados | Alta | Cada refutación se apoya en una medición que contradice el hallazgo, no en una opinión. |

**Qué me faltó para responder mejor**: las cuatro respuestas completas de la ronda 1 (sólo hay destilado);
saber quién calificó cada render marcado "render-verified" en los commits `30329b3` y `31bc14c`; y poder correr
Blender para re-medir la banda de `material_swatch` a 16 bits en vez de predecirla.
