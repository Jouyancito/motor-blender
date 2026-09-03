# Estado actual del motor — qué está implementado HOY

**Fecha de corte: 2026-09-02.** Este documento existe por un error concreto que se pagó en la
primera ronda de revisión externa.

## Por qué existe

El 2026-09-02 se pidió revisión del método a cuatro modelos, mandándoles las lecciones y las
auditorías. **Dos de las tres recomendaciones más repetidas ya estaban implementadas** desde el
2026-08-23, y dos de los cuatro revisores afirmaron como hecho presente algo que era falso hacía
diez días.

No fue culpa de ellos. El paquete llevaba las auditorías que *proponían* los arreglos y no los
archivos que los *implementaron*. **Una auditoría vieja se lee como el presente si no hay un
documento de estado al lado.** Dos revisores pidieron exactamente este archivo en su sección de
"qué me falta para responder mejor".

Es, además, la lección 3 del propio motor aplicada a la revisión: *un doc que dice "no
implementado" es una medición vieja, no un hecho.*

---

## Implementado y verificado

| Mecanismo | Dónde | Cómo se comprueba |
|---|---|---|
| **Preflight de 10 puntos, en capa 0** | `DungeonParty-A/CLAUDE.md` | Incluye `0b CON QUÉ TRUCO` (técnicas descartadas) y `4d PARÁMETROS` con las dos mitades MEDIDA + ESTRUCTURA. Ya no hay versión de 8 y de 10: se unificó el 2026-08-23 |
| **Índice de canon en capa 0** | `DungeonParty-A/CLAUDE.md` | Tabla "qué documento manda sobre qué / abrir SIEMPRE que…". El punto 1 del preflight exige citar de ahí por archivo y sección |
| **Truth render obligatorio para mobs** | `game/tools/blender/build_mob.py` | Ciclo atómico build → check de color → truth render. Corre `_glb_truth_render.py` con `--python-exit-code 1` y hace `return rc` hacia `sys.exit`. **Es fail-closed**, no una herramienta invocable a mano |
| **Gate de tamaño de uso** | `recetas/use_size.py` | `require_use_size()` como última llamada del build; sin la evidencia en el tamaño real de uso, el build falla |
| **Gate de variación de material** | `recetas/material_swatch.py` | Cubos (no planos) + métrica de alta frecuencia (no desviación estándar). `exempt` es `{nombre: razón}`: una exención sin razón es un error |
| **Veredicto de cuatro estados** | `recetas/verdict.py` | `PASS` · `FAIL` · `NOT_TESTED` · `NOT_APPLICABLE`. Un reporte con `NOT_TESTED` **no aprueba**. `NOT_APPLICABLE` exige razón escrita |
| **Preflight 4d como gate** | `recetas/asset_spec.py` | El generador declara sus partes móviles; una parte sin renglón ESTRUCTURA (plano/ángulo/límite) → `SystemExit` antes del primer `bpy` |
| **Router de reglas por sujeto** | `recetas/preflight_router.py` | Decís qué construís, devuelve reglas + técnica establecida + descartadas. Declarar una descartada → `SystemExit` |
| **Fixtures adversariales** | `tools/test_gates.py` | 26 casos, **6 de ellos entradas malas conocidas que cada gate DEBE rechazar**. Corre sin Blender: `python tools/test_gates.py` |
| **Bake de shading a FLOAT_COLOR** | `_bake_vcol.py` (repo del juego) | Con gate de cantidad de vértices |

---

## Escrito pero NO gateado

Esta es la lista que importa. Todo lo de acá abajo depende de que alguien se acuerde.

| Regla | Dónde está escrita | Qué falta |
|---|---|---|
| Citar el doc del índice por archivo y sección (preflight punto 1) | CLAUDE.md | Nada verifica que la cita exista ni que corresponda |
| `0b CON QUÉ TRUCO` para familias sin entrada en el router | CLAUDE.md | El router cubre 4 categorías (pelo, quelonio, material procedural, export). El resto no está cosechado |
| La rampa de variantes la elige Joan (punto 5) | CLAUDE.md | Nada impide elegir un valor solo |
| Vistas ingratas: nuca, cenital (punto 6) | CLAUDE.md | `preview_object.py` existe; no es obligatorio |
| `require_structure()` / `require_technique()` | `recetas/` | **Escritos y probados, todavía no cableados a ningún generador del juego** |

---

## Medido, no estimado

Números de la sesión del 2026-09-02, contra el repo real:

```
carpetas de referencia .......... 84
_synthesis.md ................... 83
_motion_spec.md .................  3
specs estructurales .............  0     <- por eso asset_spec.py existe
```

```
material_swatch.py, calibración del umbral (detail, luminancia 0-1)
  CONTROL_flat (uniforme, sin textura) .... 0.00000
  slab (la textura real más débil) ........ 0.00028
  floor ................................... 0.00083
  wood .................................... 0.00112
  column (la más fuerte) .................. 0.00364
  umbral por defecto ...................... 0.00010
```

```
tools/test_gates.py ............. 26/26 ok (6 controles positivos)
```

---

## Advertencias sobre los números que este motor auto-reporta

Los cuatro revisores señalaron lo mismo y tienen razón:

- **El "2,5 % de activación" no es una medición de activación.** El denominador suma líneas de
  markdown, scripts, skills, carpetas y observaciones de memoria como si fueran la misma unidad.
  Una receta de 500 líneas no contiene 500 veces más conocimiento que una regla de 5. Léase como
  indicio descriptivo, nunca como KPI.
- **El "4/4 PUSH funcionó, 5/5 PULL falló" es n=9**, elegido retrospectivamente, en una ventana
  de 48 h, y clasificado por el propio sistema auditado. Es evidencia suficiente para formular
  una hipótesis, no para afirmar una tasa.
- **El umbral 0.00010 está calibrado contra un solo caso de cosecha.** Los fixtures de
  `test_gates.py` cubren la lógica del gate, no la robustez del umbral frente a otra resolución,
  otra cámara, otro denoiser o otro tamaño de feature.

---

## Lo que se decidió NO hacer todavía

Recomendado por los revisores, correcto, y aplazado por costo:

- **Contrato de aceptación único por asset** que componga todas las propiedades (ChatGPT).
- **Grafo de procedencia por hashes** en lugar del gate por marcas de tiempo (los cuatro).
  El agujero conocido —un asset cuyo producto es un render y no un `.glb` escapa al gate— sigue
  abierto. **Un agujero conocido que sigue en producción no es un remedio implementado: es deuda
  aceptada.**
- **Análisis estático del grafo de nodos** antes del render de swatches (los cuatro).
- **Ledger de feedback del cliente** que traduzca "no lee como tortuga" a un parámetro
  y lo devuelva a los docs (Perplexity).

La razón de aplazarlos: los tres cambios baratos que sí se hicieron verifican primero si el
diagnóstico compartido es cierto, antes de pagar la obra grande.
