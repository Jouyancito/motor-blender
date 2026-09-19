# Addendum de reconciliación — 2026-09-08

**Corrige**: `REVIEW_FABLE_2026-09-08.md` (918 líneas, revisor Fable / Opus 5).
**Alcance de esta pasada**: los subsistemas que la review nunca abrió — `gate/`, `lookdev/`,
`tools/gen_texture_manifest.py`, y las 15 recetas que no aparecen citadas ni una vez.
**Método**: toda medición negativa lleva sonda de control positiva. Todo número que reporto lo medí
yo en este árbol; donde repito un número de la review lo digo.

**Sonda de cobertura (control positivo primero)**:
`grep -c "gate" REVIEW_FABLE_2026-09-08.md` → **90** (el instrumento lee el archivo).
`grep -n "gate360|gate_regions|g360|_run_preflight|lookdev|showcase_ficha|gen_texture_manifest|BYTE_COLOR|FLOAT_COLOR|biome_ao|biome_vcol|biome_stem|biome_mass|bvh_glue"` → **1 hit**, línea 70,
que es el literal `showcase|board|ficha|g360|contact_sheet` dentro de un regex de PowerShell que la
review está auditando — no este subsistema. Es decir: **cero**.

Misma ceguera aguas arriba: `ESTADO_ACTUAL.md` tiene 8 hits de "gate" y **0** de estos archivos;
`ANALISIS_INTEGRAL_2026-09-08.md` tiene 9 y **0**. `README.md:24-31` sí los nombra — es el único
documento del repo que sabe que existen, y su número está mal (§6).

---

## 1. Qué leyó esta pasada y qué no leyó la review

| Archivo | Líneas | Estado de cableado | Por qué importa |
|---|---|---|---|
| `gate/gate_regions.py` | 416 | **huérfano** (único llamador es `gate360.py:248`, que a su vez tiene cero llamadores) | Gate de PROPIEDAD real: puntúa 13 regiones semánticas del render contra el 2D **sin whitelist**, CIEDE2000 por región, detectores de herida/mancha/tinta-faltante, morfología de trazo, rugosidad de contorno. Es el contraejemplo vivo de la §5 de la review. |
| `gate/gate360.py` | 515 | **huérfano y además no ejecutable acá** (rutas rotas, §4) | Extiende lo anterior a 13 vistas fijas: simetría espejo, etapa 0 bloqueante por silueta, reglas baratas (agujeros, fragmentos flotantes, off-palette, recorte de cuadro), ledger ACK, `history.jsonl` append-only. `return total_fail` en `:511`. |
| `gate/g360_capture.py` | 400 | **cli_only**, con su driver documentado (`corporeo_step.py`) inexistente en esta máquina | La mitad Blender: 13 vistas fijas con ajuste de distancia por vista, más auditorías geométricas SIN render (normales de mundo vs clase de pintura, islas de malla por union-find, origen de escena) que **fallan cerradas** (`sys.exit(2)`). |
| `gate/_run_preflight_on_blend.py` | 18 | cli_only, una corrida registrada (README, 2026-07-17) | Corre `recetas/preflight_destructivo` contra cualquier `.blend` headless, sin código nuevo por proyecto. |
| `lookdev/showcase_ficha.py` | 126 | llamado por **1** de los 6 packs que su propio docstring reclama | Rig compartido de showcase/ficha. Declara una garantía de limpieza de GLB que no tiene mecanismo para hacer cumplir. |
| `lookdev/mood_valheim.py` | 933 | llamado por `village_gen.py:5010-5011` | La review lo tocó de refilón (6 menciones) vía `village_gen`; nunca como subsistema. Se le escapó la peor no-idempotencia y una desincronización de RNG. |
| `lookdev/cel_banded.py` / `render_flat_freestyle.py` / `render_invhull_flat.py` | 164 / 185 / 191 | **huérfanos** los tres | Presets CLI del proyecto Lawen vendorizados acá. Dos de ellos registran mediciones contradictorias del mismo build de Blender. |
| `tools/gen_texture_manifest.py` | 148 | **huérfano y roto** | Herramienta de integridad/procedencia de `_textures/`. Su docstring sigue certificando la decisión que la purga del 2026-09-01 dio vuelta. |
| `recetas/biome_ao.py` | 102 | **vivo, cross-repo**: 5 builders del juego | La review lo trató como parte de una familia "de test". No lo es. |
| `recetas/biome_vcol.py` / `biome_stem.py` / `biome_mass.py` | 151 / 134 / 24 | **vivos**: `build_grass_pack.py:45-47` con call sites reales | `biome_vcol` es donde vive el contrato FLOAT_COLOR del motor, en código. La review no menciona FLOAT_COLOR ni BYTE_COLOR una sola vez. |
| `recetas/bvh_glue.py`, `contorno_2d.py`, `corporeo_glance.py`, `elipsoide_apex.py`, `nails_asentados.py`, `paint_por_geometria.py`, `pose_swing.py`, `ribbon_tinta.py`, `sample_base.py`, `warp_perfil.py`, `_gen_base_reference.py` | 24-99 c/u | huérfanos | Huérfanos de dos clases distintas, que piden remedios distintos (§4). `bvh_glue` no es huérfano de verdad: se consume por copia-pega. |

---

## 2. Veredictos de la review que quedan corregidos

### 2.1 — El censo de gates está corto por cuatro gates y ~1.350 líneas

> REVIEW:570 — *"cinco gates escritos, cero cableados, 26/26 en verde, y la única aplicación que
> corre sin que nadie se acuerde son dos hooks de PowerShell"*

**Lo que hace el código**: hay como mínimo nueve. `gate/` contiene 1.349 líneas de los gates **más
orientados a propiedad de todo el repo**, y la review nunca abrió el directorio.

**Veredicto: exagerado en la magnitud, equivocado en el carácter.** La dirección de la conclusión
("escritos, no cableados") sobrevive y de hecho se refuerza. Pero la queja central de la review es
que el motor construye gates de existencia-de-evidencia, y `gate/` es un estante de gates de
propiedad terminados, con las correcciones de instrumento ganadas a mano adentro
(`gate_regions.py:110` picos de oreja que caían en fondo; `:178-179` componentes que cruzan el borde
inflaban el aspecto a 7000+; `g360_capture.py:275-277` "the missing `.T` was THE front/back-flip bug";
`:121-123` un multiplicador fijo recortaba la figura en 8 de 13 vistas). El fallo de activación no es
hipotético: ocurrió adentro de la propia review.

### 2.2 — El "proxy de dos mtimes y un regex" ya tiene su no-proxy construido

> REVIEW:663-664 (§5.9) — *"dos mtimes y un regex de nombre como proxy de 'alguien miró este asset
> desde varios ángulos'"*, y prioridad #14 (`:693`): atar la evidencia al basename del GLB, S/P2.

**Lo que hace el código**: `g360_capture.py:64-77` define una tabla de **12** vistas fijas más un
close-up de cara (`:163`), con ajuste de distancia por vista proyectando las 8 esquinas del bbox;
`gate360.py:66-132` califica las 13 (IoU de silueta contra el 2D, simetría espejo, agujeros
encerrados, fragmentos flotantes, off-palette, recorte de cuadro) y `:310-336` escribe un contact
sheet con bordes PASS/WARN/FAIL. El arreglo correcto no es un proxy mejor para "alguien miró desde
varios ángulos": es cablear la captura que ya produce esos ángulos y el gate que ya los califica.

**Veredicto: necesita matiz, y la prioridad #14 queda muerta como está escrita.** Atar un PNG a un
basename sigue siendo un gate de existencia de evidencia — exactamente lo que
`LECCIONES.md:131` prohíbe ("un gate debe testear una PROPIEDAD DEL ARTEFACTO, no la existencia de
evidencia sobre él"). Ver §5, ítem 5.

### 2.3 — "Hash y no reloj" y el ledger append-only ya están construidos

> REVIEW:721 — *"No hacer un gate de renders por mtime … que sea por hash + calificador, no por reloj"*,
> presentado como guía de diseño para obra futura. Y D6 (`:288-290`): el arreglo es un ledger en modo
> append más un campo que nadie pueda autocompletar.

**Lo que hace el código**: la mitad del hash está construida **dos veces**.
`gate_regions.py:313-324` calcula sha256 del render y grita textualmente en `:321`
*"RENDER IDENTICAL TO PREVIOUS RUN — your edit did NOT reach the render. 'Identical' is NOT 'no
regression'."*. `gate360.py:349-361` lo hace por vista sobre las 13 y agrega la mitad difícil: el
archivo de estado se escribe **sólo** en `:481`, después de que los veredictos salieron, así que una
corrida abortada no puede rebasar la línea base en silencio. Y `gate360.py:483-490` **appendea**
(modo `'a'`) una fila JSON por corrida a `history.jsonl` con timestamp, `n_fail`, veredictos por
vista y razones de fallo, rotulado como insumo del tripwire de escalación.

**Veredicto: exagerado.** El mecanismo de D6 está shippeado desde julio. Lo que falta de verdad es
sólo el campo humano `graded_by` — ahí la review tiene razón. Ojo con el matiz de §4: en el único
camino que llama a `gate_regions`, el tripwire está **desactivado de hecho**.

### 2.4 — `use_size` sí es un gate de evidencia; la generalización no se sostiene

> REVIEW:653-656 (§5.6) — *"`use_size.py:43-46` lanza sólo `FileNotFoundError`/`ValueError`: falla si
> no hay render, no mide nada de la imagen"*, usado como evidencia del patrón general.

**Lo que hace el código**: el hallazgo puntual es **correcto y no lo disputo**. La generalización no:
`gate_regions.py:208-234` mide la imagen y nada más que la imagen (Lab medio y CIEDE2000 por región,
fracciones de área roja/oscura/pálida, áreas de componentes conexos y aspecto por PCA,
perímetro²/área de contorno). Es el contraejemplo del propio patrón §5 de la review.

**Veredicto: necesita matiz.**

### 2.5 — Los punteros podridos son más de tres, y los peores son archivos enteros

> REVIEW:733-734 — *"Ya hay tres punteros podridos y uno vive en el texto de bloqueo del único gate
> que frena."*

**Lo que hace el código**: hay al menos tres más en `gate/`, y no son números de línea sino
**archivos completos citados como autoridad o como camino canónico de ejecución**:
`gate_regions.py:4` cita `_MANIFEST.md §2` como el documento que lo coronó "THE canonical verdict
tool" — no existe ningún `_MANIFEST.md`; `g360_capture.py:16` nombra `corporeo_step.py` como "the
canonical way" de correrlo — no existe en esta máquina; `gate360.py:41-42` apunta a `region_gate/` y
`../../_refs/` — verifiqué ambos con `ls`, ENOENT, contra control positivo (`gate/gate_regions.py`
existe, 19.564 bytes).

**Veredicto: subconteo.** La barrida de la review no cubría este directorio.

### 2.6 — Cablear los gates es M de costo para los tres del 2026-09-02, **no** para `gate/`

> REVIEW:135-138 y prioridad #9 (`:688`) — *"Cablear los 3 gates en `build_mob.py` (un solo call site)
> + fixture anti-descableo | Alto | M | 2 sesiones | P1"*

**Lo que hace el código**: para los tres del 2026-09-02 el costo es justo. Para `gate/` no, y la
review no podía saberlo. `gate_regions.py:51-57` `segment()` define el mundo como un oso
verde/tan/tinta/rojo, y la regla off-palette de `gate360.py:88-95` FALLA cualquier figura con más de
6% de píxeles fuera de `{green, tan, ink, red, pale}`. Un lobo, un golem, un bandido o un pájaro
fallan esa regla al 100% por construcción. El detector de landmarks (`:80-153`) asume un bípedo con
hocico. `gate360.py:368` hardcodea `filomeno_nude_apose.png` / `filomeno_apose_back.png`.

Cablear `gate/` tal cual a `build_mob.py` produce exactamente los "bloqueos aleatorios" que la review
rechaza con razón en `:716-717` para `material_swatch` — el mismo modo de falla, un directorio al lado.

**Veredicto: necesita matiz, con un límite duro nuevo** (§5, ítem 3).

### 2.7 — `mood_valheim` no es idempotente en **tres** lugares, y la review citó los dos más benignos

> REVIEW:485-489 (D12) — *"`:329` multiplica `o.data.energy` y `:354` la fuerza de emisión sobre el
> valor actual en cada llamada"*

**Lo que hace el código**: las dos citas son correctas y el mecanismo (`village_gen.py:5088` guarda
el `.blend` con el mood ya horneado) es real. Pero falta la tercera y peor:
`mood_valheim.py:271-272` lee el socket Strength del World Background y lo multiplica por 0.14-0.22
**en cada llamada**. Ese socket nunca se linkea, así que compone siempre: 1.0 → ~0.18 → ~0.032 →
~0.006. Dos re-aplicaciones y el ambiente de la cúpula de cielo desaparece. El autor sabía el patrón
correcto: el sol clave en `:146` y el de relleno en `:164-165` derivan absolutamente de `base_energy`.

**Veredicto: exagerado por debajo (subconteo).** El arreglo que propone la review (`mood_applied`)
cubre las tres, pero el diagnóstico cita las dos de menor daño.

### 2.8 — La aritmética de commits está mal

Ver §6. **Veredicto: equivocado.**

### 2.9 — El "renderiza plano" de D3 es la mitad equivocada

> REVIEW:162, :175 — *"el próximo render de village vuelve plano y con el color equivocado"*, listando
> suelo, paja, madera, piedra, sendero y plaza.

**Lo que hace el código**: la mitad del "mismo tan" sobrevive intacta. La mitad "plano" no.
`mat_textured` deja Base Color **sin linkear**, y esa es exactamente la condición que testean las
guardas de idempotencia de `mood_valheim`: `:446` `if color_in is None or color_in.is_linked: return`
y `:398` para Normal. Mientras había texturas reales, Base Color estaba linkeado y ambas pasadas se
retiraban — `village_gen.py:651-656` lo documenta como deliberado. Con las texturas borradas nada
está linkeado, así que ambas pasadas ahora **disparan** sobre materiales que antes salteaban:
`tex_ground_*` y `tex_path_*` caen en la rama ground/dirt/soil/path/patch, `tex_thatch*` en thatch,
`tex_wood*` en wood, `tex_stone_casona_*` en stone/rock. Sólo la plaza sale plana de verdad, porque
`tex_plaza_<bioma>_top` no matchea ninguna rama de ninguno de los dos inyectores.

**Veredicto: necesita matiz, y afecta el criterio de aceptación de la review.** Su criterio `:795`
("un humano abre el render de hielo y confirma que el suelo no es tan") le va a mostrar al humano una
superficie con ruido y bump — muy fácil de leer como "la ruta de textura funciona" cuando es el
fallback más una pasada procedural que nunca debía correr ahí.

### 2.10 — Donde la review tiene razón y no la discuto

- **D3, causa raíz**: el nodo de tint vive adentro de `if diff_img is not None` (`:764`) → `if tint is
  not None` (`:772`), así que todo `tint` se descarta en la ruta de fallback. Correcto, verificado.
- **D3, enumeración**: los 10 call sites de `mat_textured` (924, 926, 928, 930, 932, 2420, 3356, 3404,
  3406, 3438) y que ninguno pasa `fallback_color`. Correcto, re-derivado.
- **D3, caché**: `tint` entra en la clave de caché (`:741`), así que `jitter_tone` aloca N datablocks
  byte-idénticos. Correcto.
- **build_tree_pack**: la crítica es correcta en sustancia (el generador es inconstruible desde un
  clone limpio). Imprecisa en mecanismo: `:101` es sólo una constante string; la falla real está en
  `:343-344`, que llaman `_cache_resized` a nivel de módulo. Y el path desnudo `build_tree_pack.py:101`
  en D3 se lee como archivo de `motor-blender` y no lo es; la §Arreglo (`:790`) sí lo escribe completo.
- **D2, la tesis**: los tres gates del 2026-09-02 tienen cero call sites de producción. Verificado con
  control positivo: `require_use_size` sí aparece cableado en `build_river_segment.py:67/1744`,
  `_v3.py:66/1427`, `_v4.py:66/1589`; `require_technique`/`require_structure` sólo en
  `tools/test_gates.py`. El patrón de cableado está probado en producción y se aplicó una vez.
- **La corrección al enunciado de la tesis** (`:566-571`, "los fallos son de activación") es correcta,
  y `gate/` es su exhibit más fuerte.
- **El arreglo alternativo de `:786`** (`(*(tint if tint is not None else fallback_color), 1.0)`) es
  mejor que su propia propuesta primaria, y por una razón extra que la review no vio: restaura un
  `base_rgba` por familia, que es el valor que `mood_valheim:512` multiplica para derivar sus tonos.

---

## 3. Capacidades que ya existían y la review pedía como obra nueva

Todo lo de esta sección está en `gate/`, escrito en julio 2026, y la review lo pide como trabajo futuro.

| Capacidad que la review pide | Dónde ya vive | Qué búsqueda la habría encontrado |
|---|---|---|
| Puntuación **sin whitelist** contra la referencia 2D | `gate_regions.py:238-272` — todos los umbrales de `judge()` son ratios o deltas contra la medición del propio target: `t['red_frac']*3+0.02`, `t['dark_frac']*2.5+0.06`, `ts['mean_area_frac']*2.2`, `t['roughness']*0.55`, `t['pale_frac']*0.25` | `rg -n "NO whitelist" gate/` |
| Tripwire de cambio por **hash, no por reloj** (review `:721`) | `gate_regions.py:313-324` (sha256 del render, grito literal en `:321`) y `gate360.py:349-361` por vista, con el estado commiteado sólo después de los veredictos (`:481`) | `rg -n "sha256" gate/` |
| **Ledger append-only** de veredictos (review D6, `:288-290`) | `gate360.py:483-490`, `open(..., "a")` sobre `history.jsonl` con ts, `n_fail`, veredictos y razones | `rg -n "history.jsonl" .` |
| Board que impide **medir la caja equivocada** | `gate_regions.py:276-299` (`regions_board.png`, pares target\|render por región); `gate360.py:310-336` (`G360_BOARD.png` con bordes de color); `:238` (`SQUINT.png`) | `rg -n "board" gate/` |
| "Una feature desaparecida no puede leerse como mejora" (la disciplina de `verdict.py`, NOT_TESTED ≠ PASS) | `gate360.py:287-290` — un SKIP de región cuenta como FAIL, aplicado a nivel de imagen en julio, **dos meses antes** de que se escribiera `verdict.py` | `rg -n "SKIP" gate/gate360.py` |
| Detectar una feature pintada **en el lugar equivocado** | `gate_regions.py:382-394` exporta centros de caja normalizados por figura; `gate360.py:291-302` los consume y falla el hocico/nariz/boca de la vista frontal con deriva > 0.10 | `rg -n "box_centers" gate/` |
| **Fallar cerrado sobre el sujeto equivocado** | `g360_capture.py:363-368` `sys.exit(2)` con la razón inline: *"A gate that measures 'whatever mesh is biggest' produces confident PASSes on the wrong object (2026-07-16 audit)"*; `:369-384` `sys.exit(2)` por deriva de conteo de vértices contra `motor.config.json` | `rg -n "sys.exit\(2\)" gate/` |
| **Cero checks corridos nunca es un PASS** | `g360_capture.py:347-348`; `gate360.py:462-464` trata un `orientation.json` faltante como FAIL "audit never ran" | `rg -n "never a free pass" gate/` |
| **La evidencia rancia no puede resucitar** | `gate360.py:245-247` borra el `gate_report.json` previo antes del subprocess; `g360_capture.py:390-394` borra vistas de feature viejas | `rg -n "stale" gate/` |
| Ledger de **FAIL reconocido** (anti fatiga de alertas) | `gate360.py:256-263` + `:279-284`: un FAIL con decisión de método ya tomada reporta ACK y no cuenta | `rg -n "ack" gate/` |
| **Etapa 0 bloqueante**: silueta antes que superficie | `gate360.py:184-239`, IoU de silueta contra el 2D < 0.90 ⇒ "only silhouette/mass rounds are legitimate now". Razón en `:187`: *"weeks went into nails while the mane didn't exist"* | `rg -n "blocking" gate/` |
| **Simetría robusta a iluminación** | `gate360.py:136-180`: falla por IoU de silueta (geometría, invariante a luz) pero sólo advierte por celdas de clase de tono, porque la luz clave es asimétrica | `rg -n "symmetry" gate/` |
| **Recorte de cuadro como defecto de primera clase** | `gate360.py:74-81` falla la vista cuya figura toca el borde; `g360_capture.py:120-142` ajusta la cámara por vista para que no ocurra. Detector y preventor, ambos construidos, citándose entre sí | `rg -n "clip" gate/` |
| Contrato **FLOAT_COLOR** en código y no en prosa (la review no menciona FLOAT_COLOR ni una vez) | `recetas/biome_vcol.py:45-47`: `new_float_color_layer` es la única fábrica de capa, y sólo puede llamar `bm.loops.layers.float_color.new` | `rg -n "FLOAT_COLOR" recetas/` |
| Neutralidad de stream de RNG (lo que haría que el acoplamiento de `village_gen` no pueda repetirse) | `biome_stem.py:32` y `:110`, `biome_mass.py:17`: *"Consumes NO rng draws — every value arrives pre-sampled from the caller"* | `rg -n "rng draws" recetas/` |

**Por qué se le pasó a la review**: buscó `gate` (90 hits) y nunca buscó `gate/`, `gate360`, `g360`,
`gate_regions`, ni listó el directorio. Es el modo de falla que `CLAUDE.md` describe como "sonda ciega
a la hipótesis": el instrumento funcionaba, la consulta no podía ver el subsistema.

---

## 4. Defectos nuevos hallados en los subsistemas no leídos

### 4.1 — CRÍTICO: `gate_regions.py:412` devuelve 0 aunque falle 13 de 13

`main()` termina en `return 0` incondicional (`:412`), invocado como `sys.exit(main())` (`:416`).
`n_fail` se calcula (`:369-374`), se imprime (`:402`) y se escribe al JSON (`:397`), pero **nunca
llega al exit status**. Cualquier shell, hook, Makefile o CI que lo corra y mire `$?` recibe éxito
sobre un fallo total. Contraste con su hermano: `gate360.py:511` `return total_fail`, y su docstring
`:25` declara "Exit code = number of FAILs" — el contrato intencionado, implementado en un archivo y
no en el otro. Efecto de segundo orden: `run_region_gate` (`:251`) rama sobre `r.returncode != 0`
para decidir si el subprocess falló, así que un FAIL legítimo de 13 regiones y un PASS limpio son
indistinguibles a nivel de proceso.

Es exactamente la clase de defecto sobre la que la review construye su tesis — un gate que no puede
frenar — dentro del archivo que la review no abrió.

**Arreglo**: `return n_fail` (un token). **Costo: S.**

### 4.2 — CRÍTICO: `gate360.py` no puede correr en este repo, y un acierto de `sys.path` camufla la rotura

`gate360.py:41` → `REFS = <repo>/../../_refs` = `C:\Users\the_j\_refs`.
`gate360.py:42` → `GATE_REGIONS = <repo>/region_gate/gate_regions.py`.
Ambos verificados ENOENT con `ls`, contra control positivo (`gate/gate_regions.py` existe).

Cadena de consecuencias: `run_region_gate` (`:248`) lanza un script inexistente → `returncode != 0` →
devuelve `{'n_fail': 1, 'error': ...}` → `judge_region_view` (`:303-305`) → **front y back quedan FAIL
permanente sin importar el render**. Independiente: `:374` arma `REFS/filomeno_nude_apose.png` y `:426`
lo carga para `blocking_check`, que revienta con `FileNotFoundError` antes de llegar a ningún veredicto.

**Lo camuflado**: `:38` inserta ese mismo `region_gate` inexistente en `sys.path`, y sin embargo el
`from gate_regions import ...` de `:39` **funciona igual**, porque Python pone el directorio del
script (`gate/`) en `sys.path[0]`. El módulo importa, el archivo parece sano en inspección, y sólo
la ruta del subprocess está muerta. Es la lección "cero y roto son indistinguibles" encarnada.

**Arreglo**: derivar ambas constantes de `HERE` sin saltos `..` fuera del paquete
(`GATE_REGIONS = os.path.join(HERE, 'gate_regions.py')`), borrar el `sys.path.insert` de `:38`, mover
`REFS` a `motor.config.json` (que `g360_capture.py:31` ya establece como fuente única) con override
por CLI, y assert al inicio de `main()` que `GATE_REGIONS` y los dos PNG de referencia existen, con
`sys.exit(2)` nombrando el path faltante — el mismo estilo fail-closed que `g360_capture.py:363-368`
ya usa. **Costo: S.**

### 4.3 — ALTO: el tripwire de `gate_regions` está desactivado en el único camino que lo llama

`state_path` es un archivo fijo al lado del script (`:314`), con un solo `render_hash` y **sin clave
de a qué render pertenece**. `gate360` llama a `gate_regions` dos veces por corrida — front y back
(`:368-374`) — así que el hash del back pisa el del front cada vez. En la corrida siguiente el hash
del front nunca puede coincidir, y `prev.get('render_hash') == h` (`:320`) es siempre falso.

Desactivado por partida doble: `run_region_gate` (`:248-250`) arma el argv sin `--expect-change`, así
que ni siquiera imprimiría el grito; y `judge_region_view` (`:266-306`) lee `rep['regions']`,
`rep['box_centers']` y `rep['error']` pero **nunca** `rep['tripwire']` (`:396`), que se escribe al JSON
y se tira. Una de las tres capacidades por las que existe este subsistema es inerte en su único
camino cableado. El tripwire por vista de `gate360:349-361` sigue funcionando y enmascara la pérdida.

**Arreglo**: clavear el estado por path de render (dict `{render_path: sha256}`), o escribir el estado
al lado de `--out` y no del script; pasar `--expect-change` desde `gate360` (ya parsea el flag en
`:344`); y que `judge_region_view` exponga `rep['tripwire']` como razón de la vista. **Costo: S.**

### 4.4 — ALTO: `gate360` whitelistea 9 de 13 regiones en la vista trasera y lo reporta como PASS

`gate360.py:269-274`: `skip_regions = {muzzle, nose, mouth, ear_L, ear_R, belly, feet, torso_fur_L,
torso_fur_R}` cuando `name == 'back'` — 9 de las 13 regiones. La razón está documentada y es honesta
(`:269-272`: la referencia trasera es el oso **vestido**, así que panza/pies/torso son overol y botas;
"caught 2026-07-12: belly dE 24 was fur-vs-fabric, not a defect") y hay un TODO en `:275`.

Pero el efecto es que la vista trasera se califica sobre 4 regiones y la consola y el board reportan un
único `back: PASS`. Un defecto real en hocico, orejas, panza, pies o cualquiera de los dos costados es
estructuralmente no reportable desde atrás. Es la misma forma del fallo que `gate_regions.py:6-7`
existe para terminar ("measure_harness whitelisted the mouth and passed a wound-gash 7/7"): un
workaround local defendible que se lee como veredicto completo.

**Arreglo**: (1) emitir la vista como `PARTIAL` con "graded 4/13 regions (9 excluded: dressed
reference)" en `results[name]` y en la etiqueta del board — la misma honestidad que `verdict.py`
codifica como `NOT_TESTED`; (2) sacar la lista del código a la config por sujeto. **Costo: S.**

### 4.5 — ALTO: el escape BYTE_COLOR sigue vivo en un asset que el juego carga en un nivel real

La review no menciona BYTE_COLOR ni FLOAT_COLOR una sola vez en 918 líneas (control: `village_gen`
= 16 hits en el mismo archivo). Medición mía en el repo del juego:

- `game/tools/blender/rat/build_rat.py:247` → `me.color_attributes.new(name="Col",
  type="BYTE_COLOR", domain="POINT")`.
- `gen_golem.py:435,455,522` y `gen_golem_chunks.py:234` → lo mismo con `domain="CORNER"`.
- El repo **ya sabe**: `game/tools/blender/_bake_vcol.py:18-21` — *"FLOAT_COLOR, never BYTE_COLOR: the
  byte layer applies an sRGB decode on read that the write does not encode, crushing hand-picked tones
  by roughly 12x (measured on golem_guardian). `rat.glb` still uses BYTE_COLOR and should be migrated."*
- Y no es código muerto: `rat.glb` está commiteado (399.260 bytes, 19-jul) con su `.import` (30-jul), y
  `game/scenes/levels/floor1_prairie.gd:416` hace `SCENE_RAT = load("res://scenes/enemy/rat.tscn")`.
  No es sólo el `mob_lab`: es un nivel.
- El único guard ejecutable contra esto — `recetas/preflight_router.py:92` regla `byte_color`, que
  `require_technique` convierte en `SystemExit` — tiene **cero llamadores de producción**
  (verificado; el control positivo es `require_use_size`, cableado en tres builders de río).

**Arreglo**: ver §5, ítem 4. **Costo: S para el gate, M si hay que rehornear los GLB.**

### 4.6 — ALTO: `mood_valheim` desincroniza su propio stream de RNG y rompe su garantía de determinismo

`apply_mood` siembra una vez en `:905` y pasa **ese único generador** por siete pasos
(`:907, 911, 915, 919, 923, 927, 931`), cada uno envuelto en su propio `try/except`. El determinismo
depende entonces de que cada paso consuma un número fijo de draws. Si `_tune_lights` revienta a la
mitad, la excepción se captura, se imprime — y el rng ya consumió una cantidad distinta de draws que
en una corrida limpia, así que **todos los pasos siguientes reciben valores distintos**. El encabezado
promete lo contrario en `:38-41`: *"Two runs on the same scene name + same biome style always produce
byte-identical mood tuning."* El manejo de errores que existe para proteger el render es lo que
invalida la garantía, y lo hace en silencio: el print dice que un paso falló, nunca que el stream se
desincronizó.

Agravante: cuatro de los siete pasos ignoran el argumento `scene` e iteran los datablocks del archivo
entero (`:305`, `:339`, `:505`, `:551`), así que el conteo de draws también depende de datablocks que
no tienen nada que ver con la escena que se está moodeando.

**Arreglo**: un stream derivado por paso, `random.Random(zlib.crc32(repr((key, step_name)).encode()))`,
el mismo truco que `_seed` ya usa en `:87-93`. **Costo: S.**

### 4.7 — ALTO: `showcase_ficha` declara una garantía de GLB que no tiene mecanismo para hacer cumplir

`lookdev/showcase_ficha.py:3-5` afirma como hecho: *"Nothing here ends up in an exported GLB (labels
are removed and transforms reset before export), so the oracle for this module is the rendered PNG,
not the GLB bytes."* Ninguna de las dos mitades se hace cumplir desde este módulo. `remove_labels`
existe (`:105-110`) pero el módulo nunca lo llama: es una función que el **llamador** tiene que
acordarse de invocar. El reset de transforms ni siquiera vive acá (está en `recetas/glb_export.py`).
No hay ningún assert en las 126 líneas (control positivo: `def ` matchea 6 veces). El único adoptante
lo hace bien por disciplina, no por garantía. Un segundo adoptante que se olvide shippea curvas FONT
dentro de un GLB y el docstring seguiría leyéndose como verdadero.

**Arreglo**: `assert_clean_for_export(scene, prefix='label')` que reviente si queda algún objeto
etiquetado linkeado, con `add_labels` registrando sus objetos en una propiedad custom de la escena
para que el chequeo no necesite bookkeeping del llamador. **Costo: S.**

### 4.8 — MEDIO: el "WSL conda env `critic`" es un bloqueador fantasma — medido

`gate_regions.py:14` y `gate360.py:22` dicen *"Run (WSL conda env `critic`)"*. Medición directa en el
Python de Windows de esta máquina:

```
python -c "import numpy, cv2, skimage"   →  ModuleNotFoundError: No module named 'skimage'
```

numpy y cv2 **importan bien**; falta sólo `scikit-image`. Y `grep -c "import bpy"` sobre los tres
archivos de `gate/` da `gate_regions.py:0`, `gate360.py:0`, `g360_capture.py:1` — o sea que los dos
gates de imagen **no necesitan Blender**. El bloqueador real es `pip install scikit-image`, no WSL ni
conda. Una restricción de entorno falsa es un impuesto permanente e invisible sobre la activación, y
es plausiblemente la razón por la que nadie intentó cablearlos nunca.

**Arreglo**: reemplazar ambas líneas Run por la dependencia real y agregar `gate/requirements.txt`.
**Costo: S.**

### 4.9 — MEDIO: `tools/gen_texture_manifest.py` es un huérfano roto que certifica la decisión revertida

148 líneas, cero llamadores (control positivo: `make_review_bundle` sí aparece referenciado desde
`README.md:115`). El commit de la purga (`3f5a91d`) dice en su propio mensaje que "corrige dos
comentarios que prometían texturas que ya no existen — un docstring que describe un estado que dejó de
ser cierto es una medición vieja". Corrigió dos comentarios en `village_gen.py` y dejó un archivo
entero que **no es otra cosa que esa misma medición vieja**: `:3-12` sigue diciendo "track
`_textures/*.jpg` directly in git (27 files, ~20MB)", y `PROVENANCE_NOTE` (`:30-38`) sigue afirmando
que las texturas están commiteadas y que las consume `mat_textured()`. Además no funciona:
`--verify` imprime "MANIFEST.json not found" y sale 1; `build_manifest()` revienta con
`FileNotFoundError` sobre `os.listdir(TEX_DIR)`.

Y el generador que justificó la purga **no existe**: sonda sobre todo el repo por creación/bake de
imágenes → 1 hit (`use_size.py:53`, que arma una tira de contact sheet, no una textura), contra
control positivo de 3 `images.load` reales. La purga cambió un set de entrada de 20MB verificado por
hash por una promesa, y la promesa no tiene código atrás.

**Arreglo**: decidir en el mismo commit — borrar el archivo junto con la decisión que hacía cumplir,
o repuntarlo al directorio donde vayan a caer los mapas generados y reescribir docstring y
`PROVENANCE_NOTE`. **Costo: S.**

### 4.10 — MEDIO: la plaza es la única familia sin fallback procedural

`mat_textured` nombra sus materiales `"tex_%s_%s" % (key, projection)` (`village_gen.py:742`), así que
la plaza produce `tex_plaza_<bioma>_top`, que no matchea ninguna rama de `_inject_albedo_variation`
(thatch / tile-shingle / wood / stone-rock / ground-dirt-soil-path-patch) ni de `_inject_bump` (wood /
stone-rock / roof-thatch-shingle). Control positivo: `grep -c thatch` sobre `mood_valheim.py` = 5.
Resultado: mientras suelo, sendero, paja, madera y piedra de casona reciben ruido y bump, la losa de
plaza sale color base `(0.45,0.40,0.32)`, rugosidad 0.9, y nada más.

**Arreglo**: agregar `or "plaza" in name or "cobble" in name` a las ramas stone/rock de ambos
inyectores. **Costo: S.**

### 4.11 — MEDIO: `USE_REAL_TEXTURES = True` es hoy la ruta de MENOR fidelidad

`village_gen.py:902` documenta el flag como *"flip off for a fast geometry-only iteration pass"* — o
sea, `False` presentado como el atajo degradado. Eso se dio vuelta el 2026-09-01. Con las texturas
borradas, las ramas `True` rutean por `mat_textured` y todas aterrizan en el único `fallback_color`,
descartando el color que se les pasó. Las ramas `False` lo conservan: `mat()` en `:933-937` setea
`Base Color` desde el color del llamador. La casona es la demostración más limpia: `:2419-2423` es un
if/else donde `True` da tan y el `else` da `stone_tint = (0.44,0.43,0.39)`, el gris correcto.

**Arreglo**: arreglar el bug de verdad (la forma de `:786`); mientras tanto, `False` es una mitigación
de un carácter que produce un render estrictamente mejor coloreado, y el comentario de `:902` está al
revés en cualquier caso. **Costo: S.**

### 4.12 — MEDIO: `gate/` nunca se ejecutó en este repo

`git log -- gate/` devuelve **exactamente un commit**: `0a57cc0`, 20-jul-2026, *"checkpoint:
village_gen.py v11 — 11 iterations of village generator + shared recetas/lookdev/gate library"*. Los
cuatro archivos tienen mtime 2026-07-17 y no se tocaron en 50 días. Ninguno de los artefactos que el
código escribe existe: `gate/state.json`, `gate/state_g360.json`, `gate/history.jsonl`,
`gate/acknowledged.json`, `gate/views/`, `gate/out/` — todos ENOENT (verificado). El tripwire nunca
armó una línea base y el ledger de escalación tiene cero filas.

El estado honesto no es "escrito pero no cableado": es **"escrito en otro lado, copiado acá, nunca
ejecutado acá una sola vez"**.

**Arreglo**: decisión de propiedad, no de código. Ver §5, ítem 1.

### 4.13 — MEDIO: dos archivos de `lookdev/` registran mediciones contradictorias del mismo build

`render_invhull_flat.py:14` — *"Cycles headless (Eevee needs a GL context on 5.1.2 → not reliable in
-b)"*. `cel_banded.py:4` — *"EEVEE (BLENDER_EEVEE, renders headless on this 5.1.2 build)"*. Mismo
directorio, mismo build declarado, ambos con mtime 17-jul, conclusiones opuestas, y cada uno maneja un
motor distinto. Un tercero, `showcase_ficha.py:114-127`, asume que EEVEE anda headless y es el único
que corre en producción. Por la regla de la casa, un doc es una medición vieja: al menos uno de estos
está rancio y nada en el repo dice cuál.

**Arreglo**: una sonda, un lugar donde se registre con fecha y versión exacta, y los cuatro archivos
citando esa línea. Borrar la afirmación perdedora, no dejar las dos. **Costo: S.**

### 4.14 — MEDIO: umbrales sin procedencia en todo `gate/`

`gate360.py:205` falla con IoU de silueta < 0.90; `:153` simetría < 0.86; `gate_regions.py:245`
dE > 12; off-palette 0.06/0.03 (`:92-95`); agujeros 0.015/0.004 (`:116-119`); mancha 0.025/0.35
(`:126-129`). Ninguno lleva comentario de procedencia, corrida de calibración ni baseline de
auto-comparación, y no hay fixture en ningún lado que les meta un conocido-malo y un conocido-bueno.
Es la misma clase que el D5 de la review (el 0.00010 por debajo del piso de cuantización de su propio
instrumento): un número que parece medido y no lo es.

**Arreglo**: correr el control de auto-comparación una vez por umbral (render contra sí mismo debe
PASAR con IoU 1.0 / dE 0; una variante rota a propósito debe FALLAR), anotar los valores observados al
lado de cada constante, y congelar ese par de imágenes como el primer fixture de `gate/` en
`tools/test_gates.py`. **Costo: M.**

### 4.15 — BAJO: `bvh_glue` se consume por copia-pega, no por import

`gen_char_brows.py:101` nombra la receta en su docstring — *"Motor recipe bvh_glue"* — y después
`:107-113` reproduce `bvh_glue.py:16-22` verbatim. Segunda copia: `recetas/ribbon_tinta.py:19-27`,
**dentro del mismo directorio que el original**. Tres implementaciones, cero importadores, y las
gotchas registradas viven al lado de la copia que nadie lee.

**Arreglo**: que `ribbon_tinta.surface_bvh` llame a `bvh_glue` primero — un cambio de una línea dentro
de un solo directorio, sin la pregunta de path cross-repo. **Costo: S.**

### 4.16 — BAJO: `_gen_base_reference.py` y `corporeo_glance.py` son código de otro proyecto con paths muertos

`_gen_base_reference.py:22-23` resuelve `BASES = motor-blender/_motor/bases`; `ls -d _motor` falla
mientras `ls -d gate` funciona en el mismo comando (control positivo), así que es un directorio
ausente confirmado. `corporeo_glance.py:6-7` instruye ejecutar desde
`Desktop\Lawen\corporeo-3d\_motor\recetas\` — inexistente — y escribe a `../_gate/g360/`, el árbol de
gate del proyecto corpóreo, no el `gate/` de este repo. `RECETAS.md:28` lo lista como receta
disponible sin ninguna señal de que sus paths son ajenos.

**Arreglo**: marcarlos en `RECETAS.md` como recetas del proyecto corpóreo guardadas por referencia, o
parametrizar la raíz de salida. No "reparar" el path de `_gen_base_reference` a menos que alguien
piense correrlo. **Costo: S.**

---

## 5. PLAN CORREGIDO

Reescritura del plan inmediato de la review (`:741-836`). Cada ítem lleva un criterio que **puede
fallar**, expresado como comando y como la salida que significa FAIL.

**Lo que sale del top-5 y por qué**:
- **La mitad de evidencia-PNG del ítem 1 de la review** (y la prioridad #14, `:693` — atar el PNG al
  basename del GLB) queda **matada**. Viola `LECCIONES.md:131` frontalmente: sigue siendo un gate sobre
  la existencia de evidencia, sólo que con un regex más estricto. Y reconstruye a peor lo que
  `g360_capture.py` + `gate360.py` ya hacen. Reemplazada por el ítem 5.
- **El ítem 2 de la review** (ciclo atómico apunta al archivo que el juego carga) **sobrevive intacto**;
  esta pasada no lo tocó y no tengo nada que corregirle. Baja al 6º puesto sólo por desplazamiento.
- **El ítem 5 de la review** (`material_swatch` fuera del piso de cuantización) **sobrevive intacto**
  por la misma razón. 7º puesto.

---

### 1. Que `gate/` pueda frenar, o que salga del repo

**Cierra**: §4.1, §4.2, §4.3, §4.8, §4.12. **Costo: S. Desplaza al ítem 1 de la review.**

Es el ítem con mejor relación impacto/costo de todo el addendum: cuatro gates de propiedad terminados
a los que les faltan un token, dos constantes y un `pip install` para poder correr.

**Cambios**
- `gate/gate_regions.py:412` — `return n_fail` en vez de `return 0`.
- `gate/gate360.py:42` — `GATE_REGIONS = os.path.join(HERE, "gate_regions.py")`. Borrar el
  `sys.path.insert` de `:38`. Mover `REFS` (`:41`) a `motor.config.json` con override por CLI.
- `gate/gate360.py`, inicio de `main()` — assert fail-closed: si `GATE_REGIONS` o alguno de los dos
  PNG de referencia no existe, `sys.exit(2)` nombrando el path. Un gate al que le faltan sus propias
  entradas debe negarse a emitir veredicto, no emitir FAIL por la razón equivocada.
- `gate/gate_regions.py:314` — clavear `state.json` por path de render.
- `gate/requirements.txt` con `numpy, opencv-python, scikit-image`; borrar la línea
  "Run (WSL conda env `critic`)" de `gate_regions.py:14` y `gate360.py:22`.
- `ESTADO_ACTUAL.md` — una fila para `gate/` diciendo qué es y si el motor lo corre. Hoy menciona
  "gate" 8 veces y este subsistema cero, que es precisamente por qué una review externa de 918 líneas
  pudo auditar la capa de verificación del motor y no enterarse de que existe.

**Criterio de aceptación (puede fallar hoy, y falla)**
```
pip install scikit-image
python gate/gate_regions.py --render <ref>.png --target <ref>.png --out _out/g_self ; echo "rc=$?"
python gate/gate_regions.py --render <roto>.png --target <ref>.png --out _out/g_bad ; echo "rc=$?"
```
- **FAIL** si la segunda corrida imprime `rc=0`. Hoy imprime `rc=0` siempre, incluso con 13/13 FAIL en
  el reporte — ése es el control positivo de que el arreglo era necesario.
- **FAIL** si la primera corrida (imagen contra sí misma) no da `rc=0`: significaría que los umbrales
  de §4.14 no tienen resolución y el gate no sirve ni para el caso trivial.
```
python gate/gate360.py --views <dir> --out _out/g360 ; echo "rc=$?"
```
- **FAIL** si sale con `FileNotFoundError` o si front y back reportan FAIL con razón
  `gate_regions error`. Hoy es lo único que puede pasar.

**Si la decisión es la contraria** — que `gate/` es herramienta específica de Filomeno y pertenece al
repo corpóreo — el criterio es igual de falsable: **FAIL** si después del movimiento `ls gate/` sigue
devolviendo archivos y `README.md:29` sigue anunciando una capa de verificación que el motor no corre.
Lo que no es aceptable es el tercer estado actual.

---

### 2. Devolverle el color a los biomas, con el assert que mide y sabiendo qué va a ver el humano

**Cierra**: D3 de la review, §2.9, §4.10, §4.11. **Costo: S. Reescribe el ítem 3 de la review.**

El diagnóstico de la review es correcto; su criterio de aceptación `:795` es la parte a reescribir,
porque la interacción con `mood_valheim` que no vio hace que el humano abra un render **con ruido y
bump** — muy fácil de leer como "la textura anda".

**Cambios**
- `recetas/village_gen.py:746` — la forma de `:786` de la review:
  `bsdf.inputs["Base Color"].default_value = (*(tint if tint is not None else fallback_color), 1.0)`;
  más `fallback_color=color` en la rama de `ground` (`:924`), que no pasa tint.
- `:893-898` — borrar la cláusula sobre `jitter_tone`, falsa mientras no haya textura.
- `:689-695` — reescribir: el estado plano es soportado; el color plano **único** no.
- `:902` — corregir el comentario de `USE_REAL_TEXTURES`, que hoy dice lo contrario de lo que el flag
  hace (§4.11).
- `lookdev/mood_valheim.py:532` y `:558` — agregar `plaza`/`cobble` a las ramas stone/rock (§4.10).
- Nueva `audit_biome_colors()` al final del build, junto a los asserts de `:5090-5095`: falla si
  `len(set(base_colors)) == 1`, y falla si `ground_hielo == ground_pradera`.
- **`village_gen.py:651-656`** — el contrato documentado ahí ("mood se retira solo de los materiales
  texturados") dejó de ser cierto el 2026-09-01. O se declara que la capa procedural ahora es dueña de
  esas superficies, o los inyectores se gatean por prefijo `tex_*`. Decidir, no dejarlo implícito.

**Criterio de aceptación (puede fallar hoy, y falla)**
```
python -c "import ast,sys; s=open(r'recetas/village_gen.py',encoding='utf-8').read(); \
sys.exit(0 if 'tint if tint is not None else fallback_color' in s else 1)"
```
- Control estático mínimo; **FAIL** si sale 1.
```
blender -b --python recetas/village_gen.py --python-exit-code 1 -- hielo _out/hielo_check ; echo "rc=$?"
blender -b --python recetas/village_gen.py --python-exit-code 1 -- pradera _out/pradera_check ; echo "rc=$?"
```
- **FAIL** si `audit_biome_colors()` **no** revienta contra el código de HOY (control positivo: si el
  assert no falla antes del arreglo, el assert no mide nada y hay que reescribirlo, no celebrarlo).
- **FAIL** si después del arreglo cualquiera de las dos corridas sale `rc != 0`.
- **FAIL humano, y no es sustituible por métrica**: un humano abre `_out/hielo_check` y
  `_out/pradera_check` lado a lado. Si el suelo de hielo se lee tan, FAIL. Si se lee texturado pero del
  mismo tono que pradera, **también FAIL** — ése es el modo que la métrica de la review no habría
  atrapado y el ojo sí, porque el ruido de `mood_valheim` se multiplica sobre un `base_rgba` idéntico.

---

### 3. Cablear los tres gates del 2026-09-02 en UN punto — y NO cablear `gate/` todavía

**Cierra**: D2, D7, D10.1 de la review, más §2.6. **Costo: M. Reescribe el ítem 4 de la review.**

El orden y los siete pasos de la review (`:803-810`) son correctos y no los repito. Dos correcciones:

**(a) Límite duro nuevo**: no cablear `gate/gate_regions.py` ni `gate360.py` a `build_mob.py` en esta
tanda. `gate_regions.py:51-57` hardcodea la paleta a un oso verde/tan/tinta/rojo y `gate360.py:88-95`
falla cualquier figura con >6% fuera de esa paleta: un lobo, un golem o un pájaro fallan al 100% por
construcción. Cablearlo produciría exactamente los "bloqueos aleatorios" que la review rechaza con
razón en `:716-717` para `material_swatch`.
**Sí es cableable ya** la mitad genérica: las reglas baratas de `gate360.py:66-132` (agujeros
encerrados, fragmentos flotantes, recorte de cuadro) y la auditoría de orientación de
`g360_capture.py:250-330`, ninguna de las cuales depende del sujeto. Sacar la paleta, el orden de
regiones, las heurísticas de landmark y los nombres de referencia a un perfil por sujeto es lo que
convierte el resto en cableable, y es trabajo aparte.

**(b) Fixture anti-descableo por enumeración, no por lista a mano** — `LECCIONES.md:109`: *"enumerar el
conjunto completo y fallar si falta alguno, en vez de listar a mano los que uno recuerda"*. El fixture
que la review propone grepea `build_mob.py` por tres llamadas nombradas. Eso es una lista a mano. El
fixture correcto enumera todos los `build_*.py` de `game/tools/blender` y falla si alguno no pasa por
`build_mob.py` o no declara su exención con razón escrita.

**Criterio de aceptación (puede fallar hoy, y falla)**
```
python -c "from recetas import asset_spec; asset_spec.require_structure('<ref>/turtle', ['humerus_L','neck','head'])" ; echo "rc=$?"
python -c "from recetas import preflight_router as p; p.require_technique('un lobo','lo que sea')" ; echo "rc=$?"
python tools/test_gates.py ; echo "rc=$?"
```
- **FAIL** si la primera sale `rc != 0` después del arreglo (hoy: `SystemExit "3 propiedad(es) SIN
  EVIDENCIA"` — control positivo de que D7 es real).
- **FAIL** si la segunda sale `rc == 0` (hoy sale 0: PASS silencioso sobre un sujeto no ruteado).
- **FAIL** si `test_gates.py` reporta menos de 32 casos o si el fixture de enumeración pasa mientras
  existe algún `build_*.py` que no pasa por `build_mob.py` ni declara exención.
```
python game/tools/blender/build_mob.py slime ; echo "rc=$?"
```
- **FAIL** si sale `rc == 0`. Que falle diciendo qué falta es la señal correcta.

---

### 4. Cerrar el escape BYTE_COLOR, empezando por la víctima que el juego ya carga

**Cierra**: §4.5. **ÍTEM NUEVO — la review no menciona BYTE_COLOR ni FLOAT_COLOR una sola vez.**
**Costo: S para el gate; M si hay que rehornear los GLB.**

Hay un contrato de color escrito en código (`biome_vcol.py:45-47`), un guard ejecutable para él
(`preflight_router.py:92` + `require_technique`), cero llamadores de producción del guard, cinco
builders que lo bypassean, un asset con el bug shippeado y commiteado (`rat.glb`), cargado desde un
nivel real (`floor1_prairie.gd:416`), y el propio repo documentando la deuda en `_bake_vcol.py:20`.
Todo eso existía mientras la review medía otra cosa.

**Cambios**
- Cablear `require_technique` igual que está cableado `require_use_size`: un import y una llamada
  arriba de cada builder que pinte vértices, bajo `--python-exit-code 1`.
- Fixture de **enumeración completa** (`LECCIONES.md:109`) en `tools/test_gates.py`: enumerar todos los
  `*.color_attributes.new(` de `game/tools/blender` y fallar si alguno declara un tipo distinto de
  `FLOAT_COLOR` sin una entrada ACK con razón escrita. Una lista a mano de "los builders que me
  acuerdo" es el fallo que esa lección describe.
- Verificar **la propiedad del artefacto, no del código fuente** antes de rehornear nada: abrir
  `rat.glb` y los GLB de golem al lado de un asset `float_color` y medir la luminancia de color de
  vértice. Un grep del fuente marcaría también a los ocho builders cuyos comentarios explican
  correctamente por qué evitan BYTE_COLOR — un detector con falsos positivos garantizados sobre los
  archivos que se portan bien.

**Criterio de aceptación (puede fallar hoy, y falla)**
```
python tools/test_gates.py ; echo "rc=$?"
```
- **FAIL** si el fixture de enumeración pasa mientras `build_rat.py:247` sigue diciendo `BYTE_COLOR`
  sin ACK. Hoy el fixture no existe, así que este criterio falla por ausencia — eso es un FAIL válido.
```
python game/tools/blender/rat/build_rat.py   # bajo blender -b --python-exit-code 1
```
- **FAIL** si termina `rc=0`. Hoy termina 0 y produce un GLB con el bug de ~12x documentado.
- **FAIL** si la medición de luminancia sobre `rat.glb` sale dentro del rango de un hermano
  `float_color` **y aún así** se rehornea: significaría que el round-trip compensa y que el remedio se
  aplicó sin medir. Cualquiera de los dos resultados de la medición es un resultado; lo inaceptable es
  rehornear a ciegas.

---

### 5. Vaciar de verdad la población que los gates miden — sin construir otro proxy de evidencia

**Cierra**: la mitad **buena** de D1. **Costo: S. Recorta el ítem 1 de la review.**

Sobrevive completa la mitad de propiedad; se mata la mitad de evidencia.

**Cambios que sobreviven**
- Backfill: `python game/tools/blender/_glb_color_check.py $(git ls-files '*.glb')`; para cada uno de
  los cuatro SIN COLOR (`bird.glb`, `snake.glb`, `wasp.glb`, `king_slime.glb`), promover el hermano
  `_vcol.glb` al nombre canónico o borrar el archivo blanco.
- Imprimir el conteo de candidatos en las cinco salidas silenciosas de cada hook. Es una línea y
  convierte un cero mudo en un cero legible.
- Raíz `motor-blender/_out`: está gitignoreada (`.gitignore:1`), así que el filtro de git no puede
  producir un candidato jamás. Reemplazarlo o sacar la raíz de la lista.
- Manifiesto de sha256 chequeados, para que "ya revisado" sea una propiedad y no un estado de git.

**Cambio que se MATA**
- La prioridad #14 (`:693`, "evidencia del showcase gate atada al basename del GLB"). Un PNG cuyo
  nombre contiene el basename del GLB sigue sin decir nada sobre el asset: `LECCIONES.md:131`. Lo que
  cierra ese agujero de verdad ya está escrito y es el ítem 1 de este plan.

**Criterio de aceptación (puede fallar hoy, y falla)**
```
python game/tools/blender/_glb_color_check.py $(git ls-files '*.glb') ; echo "rc=$?"
```
- **FAIL** si `rc != 0`. Hoy `rc=1` con cuatro archivos nombrados — control positivo de que el gate ve.
```
# con el árbol limpio, correr cada hook a mano
```
- **FAIL** si alguno sale mudo. "candidatos: 0" impreso es PASS; salir sin decir nada es FAIL.
- **FAIL** si un `.glb` blanco escrito a mano en `motor-blender/_out/` **no** bloquea el cierre de
  turno. Hoy no puede bloquearlo.

---

## 6. Erratas numéricas de la review

| Afirmación | Ubicación | Medición | Veredicto |
|---|---|---|---|
| "7 commits de docs contra 3 de código desde el 2026-08-10" | `:735` | `git log --since=2026-08-10 --oneline \| wc -l` → **12**, no 10. Split por prefijo: **7 docs / 3 feat / 2 chore**. Los dos que faltan son `chore`, y uno de ellos es `3f5a91d` — **el commit que su propio D3 culpa de una regresión de código**. La review clasifica el mismo commit como código cuando reparte culpas y como no-código cuando cuenta. | **equivocado** |
| Ratio implícito ~2,3:1 docs sobre código | `:735` | Medido por contenido y no por prefijo: `git diff --stat 6c096c5..HEAD -- "*.py"` → **1.180 inserciones**; `-- "*.md"` → **1.199**. Es ~1:1. Dos commits con prefijo `docs:` traen Python sustancial (`85962ae` +24 y `371dbd7` +72 sobre `make_review_bundle.py`). Peor: la review **refuta esta misma tesis** para el repo del juego en su candidato matado #6 (`:888-891`) cambiando justamente a medición por contenido y llamando "instrumento ciego" a la versión por prefijo — y 150 líneas antes conserva el instrumento ciego para `motor-blender`. | **exagerado, y auto-inconsistente** |
| Frontera de la ventana de commits | `:735` | Anotado para que nadie lo re-litigue: `--since=2026-08-10` da 12 y **excluye** `6c096c5` (`feat(use_size)`, autorado 2026-08-10 13:41:47 -0400); `--since=2026-08-09` da 13. Con la lectura inclusiva el split es 7 docs / 6 no-docs. Una sola rama, así que `--all` no cambia nada. | **necesita matiz** |
| "cinco gates escritos" | `:570` | Nueve como mínimo. Faltan `gate_regions.py` (416), `gate360.py` (515), `g360_capture.py` (400), `_run_preflight_on_blend.py` (18) = **1.349 líneas**. | **subconteo** |
| "tres punteros podridos" | `:733` | Al menos seis. Los tres nuevos son archivos enteros, no líneas: `_MANIFEST.md`, `corporeo_step.py`, `region_gate/` + `../../_refs/`. | **subconteo** |
| "tres formas distintas de la referencia de 1,80 m" | `:509`, `:722` | Al menos **cuatro**: `village_gen.py:360` + `:4787-4793` (maniquí), `clown_gen.py:163-165` (maniquí), `_test_biome_facet.py:124` (cilindro, color distinto: `(0.92,0.20,0.16)` contra `(0.80,0.20,0.18)`), `build_grass_pack.py:335-338` (cilindro `player_ref_post_1m80`). Y el conteo no es el punto: el rig compartido de showcase, el único módulo que existe para que los packs no re-implementen andamiaje, **no tiene helper de referencia de escala** (verificado sobre las 126 líneas, control positivo `def ` = 6). Filarlo bajo "cosas ciertas y de bajo retorno" invierte la prioridad. | **exagerado / mal priorizado** |
| "`mood_valheim` … `:329` y `:354`" | `:485-489` | Son dos de **tres**. Falta `:271-272`, la peor. | **subconteo** |
| `README.md:29`: "captura **16 ángulos**" | `README.md:29` | El código captura **13**. `g360_capture.py:64-77` define exactamente **12** entradas en `VIEWS` (conté con parser, no a ojo) más el close-up de cara en `:163`; el techo es 15 y sólo en una corrida `--zone`. Los dos docstrings dicen 13 (`gate360.py:2`, `g360_capture.py:12`). Nadie midió el 16, y es el único número publicado sobre este subsistema. La §5 de la review es un catálogo de exactamente este modo de falla, en el documento que ella no leyó. | **número inventado** |
| `gate_regions.py:4`: "THE canonical verdict tool (see `_MANIFEST.md §2`)" | `gate/gate_regions.py:4` | No existe ningún `_MANIFEST.md` en la máquina (`find` con control positivo en la misma barrida). La coronación cita un documento fantasma. | **procedencia colgada** |
| `showcase_ficha.py:6-10`: reclama la convención para seis packs | `lookdev/showcase_ficha.py:6-10` | Lo importa **uno** (`build_grass_pack.py:49`). `flower_pack/build_flower_pack.py:533-540` reimplementa `area_light` inline con el cuerpo idéntico; `rock_pack/build_rock_pack.py` no importa nada del motor. Es la forma más cara de doc rancio: hace que el módulo parezca adoptado. | **equivocado** |
| `tools/gen_texture_manifest.py:3-12` y `:30-38` | — | Certifican que `_textures/*.jpg` está trackeado en git y que lo consume `mat_textured()`. Ambas cosas dejaron de ser ciertas el 2026-09-01. | **medición vieja** |

---

## 7. Qué sigue sin leer

Después de esta pasada, sigue sin citar ni por la review ni por acá:

| Archivo | Líneas | Por qué importa que nadie lo haya abierto |
|---|---|---|
| `recetas/biome_facet.py` | 575 | El archivo más grande de `recetas/` después de `village_gen`. La review lo toca sólo en `:509-510` para decir que `add_stone_aggregate` devuelve 60-80% de piedras mal apoyadas sin aserción y que "no tiene un solo llamador fuera de su test". Esa segunda mitad es de la misma familia de afirmaciones que se le cayeron con `biome_ao`: `build_river_segment_v4.py:63` importa de acá. Nadie leyó las 575 líneas. |
| `recetas/engordar_anatomico.py` + `_SPEC.md` | 203 + 17.538 bytes | La review lo menciona en una cláusula (`:511`, "hardcodea el rig de Filomeno dentro del motor genérico"). El SPEC de 17KB no lo abrió nadie. Es el otro candidato, junto con `gate/`, a "código del proyecto corpóreo vendorizado acá". |
| `recetas/preflight_destructivo.py` | 51 | Es el objetivo de import de `gate/_run_preflight_on_blend.py`, o sea la única receta con una corrida cross-repo registrada (README, 46 mallas, 1 NOT SAFE). Nadie verificó qué mide. |
| `recetas/clown_gen.py` | 214 | Citado sólo como "duplica `mat`/`shot`/maniquí" (`:508`). |
| `recetas/glb_export.py` | 59 | Citado por el N=5 de duplicación de `export_glb` (`:481-482`), no leído. Es donde vive el `reset_transforms` del que depende la garantía no-aplicada de `showcase_ficha` (§4.7). |
| `recetas/verdict.py` | 128 | La review lo cita en `:592` ("`verdict.Report` se construye en tres recetas y no lo emite ningún build"). Vale reconciliarlo con `gate360.py:287-290`, que aplica la misma disciplina cuatro estados a nivel de imagen desde julio. |
| `tools/make_review_bundle.py` | 161 | La review cita `:27-31` y `:50-66`. Su lista de 13 archivos **no incluye** `gate/`, `lookdev/` ni `tools/gen_texture_manifest.py`, que es la razón mecánica por la que los cuatro revisores de la ronda 1 tampoco los vieron. Esa lista merece leerse entera. |
| `_out/` | — | Contenido no inventariado por nadie. La review cita un solo render (`village_v18a_test`, 2026-07-26) para fechar la última mirada humana. Nadie listó qué más hay. |
| Repo del juego, fuera de los ~12 archivos citados | — | Esta pasada tocó `build_grass_pack`, los cuatro de `river_segment`, `paint_char_skin`, `build_rat`, `gen_golem*`, `gen_char_brows`, `_bake_vcol`, `_motor.py` y `GATE_PROTOCOL.md`. `game/tools/blender` tiene 90 archivos con `import bpy`. |
| `game/tools/visual_gate/GATE_PROTOCOL.md` (181 líneas) | 181 | Leído por esta pasada pero fuera del alcance del addendum: su comando central (`:101-108`) invoca `--crop`, `--contract` y `--json` sobre `compare_render.py`, que define seis flags y ninguno de esos tres (control positivo: `add_argument` = 6 hits). El comando muere en argparse. Es material para un addendum del repo del juego, no de éste. |
