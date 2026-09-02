# Lecciones del motor — consolidado

**Qué es esto**: los patrones que se repitieron a lo largo de varias sesiones, destilados. No es
un registro de qué se hizo — eso vive en engram y en los `_synthesis.md`. Es la lista de las
formas de equivocarse que este motor ya demostró tener, cada una con el caso que la pagó.

Se lee entero antes de una sesión de modelado. Es corto a propósito.

Primera consolidación: 2026-08-24, tras las sesiones del pelo del guerrero, la auditoría del
motor y la tortuga.

---

## 1. El motor sabe más de lo que ejecuta

Medido: **el 2,5 % del conocimiento del motor se carga solo**; el 97,5 % depende de que alguien
decida ir a buscarlo. En 48 horas de trabajo medido, **las 4 piezas que se cargaban solas
funcionaron y las 5 que había que ir a buscar fallaron**.

> **Si una regla necesita que yo me acuerde de ir a buscarla, ya falló.**
> Ponela donde llega sola (capa 0) o ponela donde frene (un gate).

Corolario para cuando aparezca conocimiento nuevo: la pregunta no es *dónde documentarlo* sino
**por qué mecanismo se va a activar**. Cada vez que la respuesta a un fallo sea "escribamos esto
en un doc", el doc va a ser bueno y el fallo va a volver.

---

## 2. Un valor correcto en los datos e invisible en pantalla NO está hecho

La forma de fallo más frecuente de todas, y la más difícil de ver porque el código está bien.

| Caso | El dato estaba | Y en pantalla |
|---|---|---|
| Escudos de la tortuga | atributo `Scute` pintado | nunca cableado al material — se horneó el voronoi |
| Húmero horizontal | sprawl implementado correcto | tapado bajo el caparazón |
| Solapamiento del pelo | 50-74 % medido | un gorro liso |
| Color de 4 mobs | showcase con escamas y rayas | blancos en Godot |

**Remedio**: por cada parámetro estructural, escribir la **condición geométrica que lo hace
visible** y hacer fallar el build. Cuesta una comparación y un `SystemExit`.

---

## 3. Las métricas ciegas: cuatro casos, la misma forma

Todas medían **algo real que no era lo que se estaba preguntando**.

- *"solapamiento de dominio 50-74 %"* → medía si las cáscaras se pisan, no si eso se ve.
- *"120 verts en costura"* → medía que el atributo existiera, no que se viera.
- *"relieve 157,5 mm"* → medía el radio de la esfera, no el desplazamiento.
- *"¿algo del archivo tiene color?"* → aprobó una avispa blanca porque sus OJOS tenían tinte.

**Antes de aceptar una métrica: ¿puede esta medición VER el defecto que busco?** Y correr un
control positivo — un caso que se sabe malo tiene que dar mal.

---

## 4. La prosa correcta que nunca baja a geometría

Se escribe la observación justa y después se construye otra cosa. Cuatro casos:

- *"el pelo se peina en una dirección"* → offset uniforme en todas.
- *"patas palmeadas, cuello extensible"* → cuatro conos iguales y una esfera.
- *"6 pares de escudos en el plastrón"* → un disco liso.
- *"`SHELL_DEFORM = 0`, es hueso"* → el caparazón respiraba.

**Remedio (regla de traducción, ya en la capa 0)**: cada frase del "qué es" termina en un
**número** o una **orientación**. *"Patas palmeadas"* no es un punto cumplido; *"húmero
horizontal, antebrazo vertical, yaw ±40° por cuadrante"* sí.

---

## 5. Parámetros de MEDIDA vs de ESTRUCTURA

La investigación produce fácil los escalares —cuánto mide, cuántos hay, a qué velocidad— porque
salen de una ficha y se verifican con un script. Por eso son los que siempre se escriben.

Los que deciden si la cosa **lee** son los otros: **qué plano ocupa cada parte móvil, qué ángulo
tiene respecto del cuerpo, y qué la limita.**

La tortuga cumplía TODOS los de medida —ratio en banda, 5 escudos, marcha correcta— y no leía,
porque no había ni uno estructural. **Una parte sin renglón estructural no se modela: se
investiga primero.**

---

## 6. Pintar estructura sobre una superficie continua no da esa estructura

Dos veces, el mismo techo:

- **Pelo**: una cáscara offset del cráneo es, geométricamente, un gorro. Lo que produce la
  lectura de pelo es el solapamiento con separación visible. Se resolvió construyendo **desde
  los mechones** (cards con alpha).
- **Caparazón**: una esfera UV con escudos calculados y pintados encima tiene el edge flow de
  una esfera — los bordes de placa cortan polígonos por la mitad y los anillos comparten el
  centro de la esfera. Se resuelve construyendo **desde los escudos**.

> Cuando el detalle no lee después de dos o tres pases de parámetro, el problema no es el
> parámetro: es **la estructura sobre la que se está pintando**.

---

## 7. Un arreglo a medias es un bug

Los ojos no seguían a la cabeza; se agregaron los ojos al rango y **quedaron fuera las cejas y
las narinas**, que siguieron flotando. Se ve igual de roto y cuesta el doble de encontrar.

**Remedio**: enumerar el conjunto completo y **fallar si falta alguno**, en vez de listar a mano
los que uno recuerda.

---

## 8. Una constante obsoleta dentro de un gate es peor que no tener gate

El assert del codo comparaba contra el ancho del caparazón. Después el caparazón se ovaló al
78 % y el assert siguió exigiendo el ancho viejo — para "pasarlo" se alargó el húmero hasta
dejar patas de araña. **El gate pasaba, así que el defecto parecía decisión de diseño.**

**Remedio**: los umbrales de un assert se **derivan de la geometría viva**, no se copian.

---

## 9. Godot es ground truth; Blender no puede sustituirlo

Tres bugs de la tortuga eran **invisibles en Blender por construcción**: el pivote (Blender no
tiene piso), la segunda tortuga fantasma (el `.tscn` no existe allá), el nombre del clip (es
código de Godot). Y antes: cuatro mobs blancos durante un mes con showcases que se veían bien,
porque el showcase renderiza CON el grafo de nodos que el `.glb` no puede llevar.

**Un gate debe testear una PROPIEDAD DEL ARTEFACTO, no la existencia de evidencia sobre él.**

---

## 10. El ojo del cliente sobre el movimiento pesa más que la lectura de un abstract

Joan, viendo la marcha: *"son dos patas que se mueven en conjunto"*. La fuente le dio la razón:
*"the four footfalls are clearly NOT evenly distributed at 25 % intervals"*. Yo había leído
*"lateral-sequence diagonal-couplet"* e implementado **sólo la primera mitad del término**.

**Un término técnico compuesto puede tener dos mitades y aplicarse una sola.** Y cuando el
cliente describe un movimiento que no coincide con lo implementado, se verifica la fuente antes
de defender el código — a veces la fuente ya decía lo que él está viendo.

---

## 11. Cuando el sujeto existe en la realidad, la estructura faltante es un fallo de investigación

Joan: *"si te digo que inventes algo que no hay en la realidad, ahí sí hay que explicarte cada
movimiento. Pero todo lo que estamos haciendo está en la realidad. Están las referencias."*

La postura esparrancada de una tortuga es un hecho documentado. La asimetría de su ciclo de
marcha también. Los anillos de crecimiento también. Nada de eso requería que lo explicara el
cliente — estaba **a una búsqueda de distancia**.

---

## 12. El banco de pruebas también necesita su control positivo

Extensión de la lección 3, un nivel más abajo. No alcanza con que la métrica apunte a lo
correcto: **la geometría de prueba tiene que poder expresar el defecto.**

Un material de hormigón renderizaba liso. Se armó un banco para aislarlo — **con planos**. Un
plano parado en XZ tiene la Y constante, y la textura estaba bandeada justo en Y. El banco era
geométricamente incapaz de mostrar lo que buscaba, y devolvió "liso" sin error. *La sonda
confirmó una conclusión falsa, que es peor que no tener sonda.* Por eso los swatches son
**cubos**: ninguna dirección de textura puede esconderse de la medición.

Y después, el mismo error una capa más adentro: el gate escrito para atrapar esto usaba
**desviación estándar**, que sobre un cubo mide el sombreado entre caras, no la textura. Medido:
un control uniforme daba `sd=0.058` y el hormigón realmente texturado `sd=0.008` — **el
instrumento estaba invertido** y habría aprobado todo material plano que le pasaran. Se arregló
midiendo alta frecuencia (mediana de la diferencia entre píxeles vecinos): control `0.00000`,
materiales reales `0.0003`–`0.0036`.

> Las dos veces lo que salvó fue lo mismo: **meter un caso que se sabe malo por el instrumento.**
> Un gate que nunca vio fallar un control positivo es una decoración.

Cierre del ciclo: el test del gate también tuvo su falso positivo, por buscar el nombre del
material como substring en el mensaje de error — y el texto de ayuda del propio gate menciona
"slab" y "column" como ejemplos. Tres capas, el mismo error. **Nada mide bien hasta que lo probás
contra algo que tiene que fallar.**

Herramienta: `recetas/material_swatch.py`.

---

## 13. El ojo del agente falla en las DOS direcciones

Está muy documentado que el agente aprueba defectos. Lo nuevo es que también **inventa defectos
que no existen**, y eso cuesta pases igual.

Mirando un render de estacionamiento, el agente declaró que el piso "leía plástico" y arrancó a
corregirlo. La medición contra la referencia decía `sd=8.23` contra `7.56` — **ya estaba mejor
que el objetivo.** El defecto real era otro: el techo estaba a la mitad de brillo (`118` contra
`233`), y no se había mirado.

> Cuando hay referencia, se mide ANTES de decidir qué arreglar. El ojo elige el defecto
> equivocado con la misma confianza con la que aprueba el correcto.

Corolario sobre las ventanas de medición: hay que verificar que las dos muestras miran lo mismo.
En este caso la ventana "columna" caía sobre un cartel de color en la referencia y sobre hormigón
desnudo en el render — la diferencia era de contenido, no de calidad, y casi se saca una
conclusión de ahí.

---

## 14. "No medido" no es "aprobado" — y lo escrito no es lo gateado

Las dos mitades salieron de una revisión externa (2026-09-02): cuatro modelos leyeron el
método por separado y **los cuatro** llegaron al mismo par de conclusiones.

**Primera: un veredicto binario no tiene dónde poner "no se midió".** Un check que no corrió
y un check que pasó valen lo mismo, así que el que falta se suma callado a los que pasaron. Ya
se pagó: el gate de showcase preguntaba *"¿hay un PNG más nuevo que el .glb?"* y cuatro mobs
salieron blancos un mes — el check de color nunca corrió y nada lo dijo. Ahora hay cuatro
estados (`PASS` · `FAIL` · `NOT_TESTED` · `NOT_APPLICABLE`), y **un reporte con `NOT_TESTED`
no aprueba**. `NOT_APPLICABLE` exige razón escrita: sin ella es un `NOT_TESTED` con modales, que
es exactamente cómo una lista de exenciones se pudre hasta ser la lección 8.

**Segunda: el preflight ya decía lo correcto y no lo hacía cumplir.** El punto 4d dice, en capa
0, *"parte sin renglón estructural = NO se modela, se investiga primero"*. Nada lo verificaba.
Medido el mismo día: **84 carpetas de referencia, 83 `_synthesis.md`, 3 specs de movimiento,
0 specs estructurales.**

> **Una regla escrita en el checklist que el agente redacta en su propia respuesta no es un
> control: es una intención.** El que decide es el `SystemExit`.

Detalle que importa para leer críticas externas: dos de los cuatro modelos afirmaron que
`_glb_truth_render.py` *"no está en ningún gate"*. Es falso desde el 2026-08-23 —
`build_mob.py` lo corre fail-closed. Lo sacaron de una auditoría de ese día sin notar que el
arreglo es del mismo día. **Un revisor externo sólo puede ver la foto que le mandás**, y una
auditoría vieja se lee como el presente.

Herramientas: `recetas/verdict.py`, `recetas/asset_spec.py`, `recetas/preflight_router.py`,
`tools/test_gates.py`.

---

## Herramientas que salieron de estas lecciones

| Herramienta | Qué resuelve |
|---|---|
| `build_mob.py` | ciclo atómico build → check de color → truth render. "Ver" deja de ser un paso olvidable |
| `_glb_color_check.py` | ¿cada primitiva tiene fuente de color? Gate de propiedad, registrado como hook |
| `_bake_vcol.py` | hornea shading procedural a FLOAT_COLOR, con gate de vértices |
| `preview_object.py` | encuadra CUALQUIER malla por bbox, con cenital — la vista que todo juicio a ojo saltea |
| `capture_gait.py` | tira densa de frames de un clip; el movimiento no se juzga en un still |
| `mob_lab.tscn` | banco en vivo: piso plano, luz neutra, IA congelada, animaciones por tecla |
| `_carapace.py` | construye un carapacho DESDE sus escudos (lección 6) |
| `material_swatch.py` | cubos + métrica de alta frecuencia: prueba que un material VARÍA sobre la geometría; falla el build si no (lección 12) |
| `verdict.py` | cuatro estados: `NOT_TESTED` deja de confundirse con `PASS`; `NOT_APPLICABLE` exige razón (lección 14) |
| `asset_spec.py` | convierte el preflight 4d en gate: parte móvil sin renglón estructural → `SystemExit` (lección 14) |
| `preflight_router.py` | resuelve QUÉ reglas aplican desde QUÉ se construye; una técnica descartada frena el build (lección 1) |
| `tools/test_gates.py` | fixtures adversariales: cada gate contra un caso que DEBE fallar (lección 12) |
