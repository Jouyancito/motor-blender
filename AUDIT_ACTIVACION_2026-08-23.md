# Auditoría de ACTIVACIÓN del motor

**Fecha**: 2026-08-23 · **Pedido de Joan**: *"prefiero completar una auditoría más extensa sobre
la activación del conocimiento del motor, porque ya hemos trabajado muchas cosas que se te
olvida volver a activar"*.

La auditoría anterior (`AUDIT_2026-08-23.md`) preguntó *qué se contradice*. Esta pregunta algo
distinto y más incómodo: **de todo lo que el motor sabe, ¿qué proporción llega a ejecutarse, y
por qué mecanismo?**

Método: censo cuantitativo de las piezas, clasificación por mecanismo de carga, y **evidencia
histórica** de engram — casos donde el conocimiento existía, estaba escrito, y no se activó.
No opiniones: cada caso lleva fecha, doc y consecuencia.

---

## 1. El censo — cuánto sabe el motor y cómo se carga

| Capa | Contenido | Volumen | **Mecanismo** |
|---|---|---|---|
| 0 | `~/.claude/CLAUDE.md` + `DungeonParty-A/CLAUDE.md` | **943 líneas** | **PUSH** — llega solo |
| 1 | `CREATION_PROTOCOL` + `RECETAS` + `TECNICAS` | 377 líneas | PULL |
| 1 | `recetas/` + `lookdev/` + `gate/` | 32 scripts | PULL |
| 2 | `game/docs/**/*.md` | **36.965 líneas** en 180 archivos | PULL |
| 2 | `_references/` | **74 carpetas**, 73 con síntesis | PULL |
| 3 | skills | 38 | TRIGGER (probabilístico) |
| 4 | hooks | 10 (**6 bloquean**, 4 recuerdan) | PUSH duro |
| 5 | engram | ~2.540 observaciones | PULL |

### El número que importa

```
PUSH automático:     943 líneas
PULL bajo demanda:  ~37.500 líneas + 32 scripts + 2.540 memorias
─────────────────────────────────────────────────────────────
Se carga solo:       ~2,5 % del conocimiento del motor
```

**El 97,5% del motor depende de que yo decida ir a buscarlo.**

Esa es toda la auditoría en una línea. El resto es demostrar que ese diseño falla de manera
predecible, y que ya se sabía.

### Un dato lateral que confirma lo mismo
De 74 carpetas de referencia, **73 tienen `_synthesis.md` y sólo 3 tienen spec de movimiento**
(golem, tortuga desde hoy, y una más). El conocimiento de forma se registró; el de movimiento
casi no. No por decisión: porque nada lo pedía.

---

## 2. Taxonomía de mecanismos, y su tasa real

Los tres mecanismos no son equivalentes. Medidos por lo que efectivamente pasó:

| Mecanismo | Cómo llega | Falla cuando | Tasa observada |
|---|---|---|---|
| **PUSH (capa 0)** | inyectado en cada sesión | nunca, si está escrito ahí | **alta** |
| **PUSH duro (hook fail-closed)** | bloquea la acción | el hook no cubre el caso | **la más alta** |
| **TRIGGER (skill)** | se dispara por contexto | el disparador no reconoce el caso | media |
| **PULL (doc / receta / engram)** | yo decido abrirlo | **yo no sé que existe, o no me acuerdo** | **la más baja** |

La diferencia entre PUSH y PULL no es de calidad del contenido. Es de **quién tiene la carga de
acordarse**. En PULL, la tengo yo — y esa es exactamente la parte del sistema que no es
confiable.

---

## 3. Caso de control natural — esta misma sesión

Las últimas 48 horas funcionan como experimento, porque hubo piezas de los dos tipos en juego
sobre el mismo trabajo.

### Lo que se activó (y por qué)

| Pieza | Mecanismo | Qué logró |
|---|---|---|
| `engram-session-guard.py` | hook Stop, **bloquea** | me impidió cerrar sin guardar memoria. Funcionó a la fuerza |
| `art-ref-critic-trigger.ps1` | hook UserPromptSubmit | disparó la Naturalness Audit cuando Joan mandó renders. **Sin él, habría opinado sin rúbrica** |
| `motor-bash-blender-reminder.ps1` | hook PostToolUse | inyectó las reglas del motor en cada corrida de Blender |
| `DungeonParty-A/CLAUDE.md` | push capa 0 | el preflight de 8 se escribió — porque está ahí |

### Lo que NO se activó (y qué costó)

| Pieza | Mecanismo | Consecuencia medida |
|---|---|---|
| `_asset_creation_contract.md` §3b/§402 | PULL | **dos técnicas de pelo equivocadas seguidas**. El doc marca una como descartada y nombra la correcta |
| `_modeling_knowledge_base.md` §Hair | PULL | el método de 3 capas estaba escrito, se redescubrió a mano |
| `_bestiary_visual_bible.md` §5 | PULL | se leyó tarde, y sólo porque fui a buscarlo |
| `_glb_truth_render.py` | PULL | **4 mobs blancos durante un mes**, con el bug documentado en la cabecera del propio script |
| `_motor_tiers.md` | PULL | (2026-08-07) usé la extensión del archivo como criterio; el doc existía desde el 29 de julio |

**4 de 4 piezas push funcionaron. 5 de 5 piezas pull fallaron.**

No es que los docs estén mal escritos — el contrato es excelente, y cuando finalmente lo abrí
resolvió el problema en un paso. **Es que nada me obligó a abrirlo.**

---

## 4. El timeline — cinco intentos en tres meses

Esto es lo que hace la auditoría necesaria: no es la primera vez.

| Fecha | Intento | Mecanismo elegido | Resultado |
|---|---|---|---|
| **2026-06-08** | Análisis 360 de colaboración (#1441) | diagnóstico + 5 mejoras | identificó *"gaps NO de competencia sino de SISTEMATIZACIÓN"* |
| **2026-06-18** | *"art-ref-critic debe auto-activarse"* (#1817) | **hook** | ✅ **el único que sigue funcionando hoy** |
| **2026-07-07** | KB unificado + skills routers (#2067) | doc + skills (**PULL**) | conocimiento mejor organizado; activación igual |
| **2026-07-12** | Joan re-flaggea ver-antes-y-después (#2085) | — | *"recurrente **pese a** gate_regions v1.4 y reglas en SKILL.md"* |
| **2026-08-15** | Preflight de 8 puntos (#2446) | **push capa 0** | ✅ se ejecuta… pero le faltan 3 puntos (ver abajo) |
| **2026-08-22** | — | — | fallé igual con el pelo |

### El patrón del timeline

De los cinco intentos, **los dos que funcionaron eligieron push o hook** (art-ref-critic,
preflight en CLAUDE.md). **Los que eligieron doc o skill no cambiaron nada** — mejoraron el
contenido, no el mecanismo.

Y el intento del 2026-07-07 es el más instructivo. La pregunta de Joan fue literalmente:

> *"cuál recopilación es más eficiente **sin activar cosas aisladas** y sin repetir mil veces
> buscá en otra"*

La respuesta que se dio fue: *"conocimiento unificado + enlazado, **activación fragmentada**"*.
Se unificó el conocimiento — correcto y sigue siendo correcto. Pero la mitad de "activación
fragmentada" quedó como estaba, y era la mitad que Joan estaba preguntando.

---

## 5. Las dos frases que ya tenían la respuesta

Ambas están en engram desde hace meses.

### #1441, 2026-06-08 — la distinción técnica

> **"CLAUDE.md es push, engram es pull."**

Y el cierre de ese mismo análisis:

> *"gaps NO de competencia sino de SISTEMATIZACIÓN. Sabe qué hacer, lo dice cada vez, **no
> siempre lo convierte en algo que se ejecute solo**."*

Se escribió describiendo cómo trabaja Joan. Describe con precisión idéntica cómo falla el motor.

### #2085, 2026-07-12 — el principio de diseño

> *"el fix no es más explicación sino **estructura**: hacer **atómico** el ciclo
> editar→render→gate (un solo comando/wrapper que aplica el cambio Y renderiza Y corre el gate),
> **para que 'ver' no sea un paso separado olvidable**."*

Ese es el principio general, y sigue sin aplicarse fuera del corpóreo:

> **Un paso olvidable se elimina fusionándolo dentro de un paso obligatorio.**

No se elimina explicándolo mejor.

---

## 6. Las cuatro formas de fallar la activación

Clasificando los fallos reales, son cuatro modos distintos y cada uno pide un remedio distinto.

### A. No sé que el documento existe
`_motor_tiers.md` (2026-08-07): existía hacía 9 días, nunca lo había leído.
**Remedio**: índice en capa 0. No el contenido — el índice, que es barato.

### B. Sé que existe pero no se me ocurre que aplica
El contrato en el pelo: sabía que había un contrato de creación de assets; no lo asocié con
"peinado". **Remedio**: el preflight tiene que **nombrar el doc**, no la categoría. "Punto 1:
refs cargadas" es evasivo; "Punto 1: cité `_asset_creation_contract.md` §<n>" no lo es.

### C. La regla existe pero depende de mi disciplina
Ver-antes-y-después (#2085). **Remedio**: atomicidad — fusionarla en un wrapper.

### D. El gate existe pero mide lo que no importa
`motor-showcase-gate` verifica que exista un PNG nuevo; los mobs blancos tenían PNG.
**Remedio**: gates sobre **propiedades del artefacto**, no sobre existencia de evidencia.

---

## 7. El inventario de deuda de activación

Conocimiento valioso que hoy está en PULL y no debería estarlo:

| Conocimiento | Dónde vive | Debería ser | Prioridad |
|---|---|---|---|
| Preflight completo de 10 puntos (con `0b. CON QUÉ TRUCO`) | contrato §4 (pull) | **push capa 0** | 🔴 alta — es el que falló ayer |
| Techo de fidelidad Skyrim por familia | contrato §3b (pull) | índice en capa 0 | 🔴 alta |
| Técnicas DESCARTADAS | contrato §402 (pull) | **encabezado de cada `_references/<X>/`** | 🔴 alta |
| El GLB debe llevar color/textura | `_glb_truth_render.py` (pull) | **hook fail-closed** | 🔴 alta |
| Método de pelo en 3 capas | KB §Hair (pull) | índice en capa 0 | 🟡 media |
| Anti-recetas (callejones probados) | `RECETAS.md` (pull) | índice en capa 0 | 🟡 media |
| Motor tiers M1/M2/M3 | `_motor_tiers.md` (pull) | índice en capa 0 | 🟡 media |
| Build-method por criatura | bestiario §5 (pull, y desactualizado) | resolver + índice | 🟡 media |
| Specs de movimiento | 3 de 74 refs | exigido por el preflight | 🟢 baja |

---

## 8. Qué hacer, en orden de rendimiento por esfuerzo

### 1. Un ÍNDICE de la capa 2 dentro de la capa 0 — *la de mayor retorno*
No mover 37.000 líneas: mover **una tabla de 20 renglones** que diga qué doc gobierna qué, y
cuándo abrirlo obligatoriamente. Ataca el modo de fallo A (no sé que existe) y el B (no se me
ocurre que aplica), que juntos explican la mayoría de los casos.

### 2. Unificar el preflight en la capa 0, con los 10 puntos
Copy-paste de tres líneas. El punto `0b. CON QUÉ TRUCO — técnica establecida de la familia; si
no se sabe, DECIRLO` es literalmente el que habría evitado el fallo del pelo.

### 3. Gate de propiedad del artefacto
Que `motor-showcase-gate` verifique, además de la existencia del PNG, que el `.glb` más nuevo
tenga `COLOR_0` o textura. `_glb_stats.py` ya devuelve el dato. Convierte un mes de mobs
blancos en un bloqueo inmediato.

### 4. El descarte se escribe en la referencia
Cuando una técnica se descarta, el aviso va **arriba de todo en su carpeta de referencia**. El
lector natural de una referencia es el que está por construir con ella.

### 5. Atomizar generar→verdad→mirar
El principio de #2085, aplicado a mobs: un wrapper que construye, exporta, corre el truth
render y falla si no hay color. Que "verificar" no sea un paso separado olvidable.

---

## 9. Conclusión

El motor no tiene un problema de conocimiento. Tiene **exceso** de conocimiento en el
mecanismo equivocado: 97,5% en PULL, que es el mecanismo cuya tasa de fallo es la más alta y
cuya carga recae sobre lo menos confiable del sistema, que soy yo acordándome.

Los tres fallos de estas 48 horas tenían el documento que los impedía escrito **antes** del
fallo. Y el diagnóstico correcto está en engram desde junio y julio, con las dos frases exactas:
*push vs pull*, y *estructura, no disciplina*.

La única corrección que sirve es la que **cambia el mecanismo, no el contenido**. Cada vez que
la respuesta a un fallo sea "escribamos esto en un doc", el doc va a ser bueno y el fallo va a
volver.

> Si una regla necesita que yo me acuerde de ir a buscarla, ya falló.
> Ponela donde me llega sola, o ponela donde me frene.

---

**Evidencia**: engram #1441, #1817, #2067, #2085, #2323, #2446, #2536-#2544 · censo del
2026-08-23 sobre `~/.claude/`, `~/motor-blender/`, `DungeonParty-A/game/docs/`.
