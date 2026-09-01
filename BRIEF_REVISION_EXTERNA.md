# Brief para revisión externa

**Para qué es esto**: pegarlo en otra IA (o dárselo a otra persona) y pedir una mirada de afuera.
Está escrito para leerse sin acceso al repo. La fuente completa es `LECCIONES.md`; acá va el
resumen y, sobre todo, **las preguntas**.

Si vas a responder: interesa el desacuerdo más que la confirmación. La sección 5 es el punto.

---

## 1. Qué es el motor

No es un programa: es un método de trabajo entre una persona (arquitecto/diseñador) y un agente
LLM con acceso a shell, para producir assets 3D y renders **sin abrir la interfaz de Blender**.

- Blender headless (`--background --factory-startup --python-exit-code 1`)
- Generadores en Python (`bpy` + `bmesh`), paramétricos y con semilla fija
- Salida: `.glb` para Godot, o `.png` para arquitectura
- **El agente nunca ve la escena.** Sólo renders que él mismo dispara y después lee como imagen
- Memoria persistente entre sesiones + biblioteca de recetas versionada

Principio rector: el agente no puede confiar en su impresión visual. Todo veredicto se apoya en
una medición o en una imagen mirada explícitamente. Internamente: *"sin número, no hay
veredicto"*.

**Ciclo:** preflight escrito → construir → sonda de control → medir contra objetivo → veredicto
por ítem (PASS/PARCIAL/FAIL con evidencia, y declarar lo que falta).

El preflight tiene 8 puntos; los dos que más rinden y más se saltean son el **0** (*qué es la
cosa, cómo funciona, cómo es normalmente* — de ahí sale el criterio de éxito antes de renderizar)
y el **7** (*¿encaja y se fusiona?* — no *¿está puesto?*).

---

## 2. Los 13 patrones de fallo ya documentados

Cada uno se pagó con un caso real. Varios se repitieron en proyectos distintos.

| # | Patrón | Caso que lo pagó |
|---|---|---|
| 1 | **El motor sabe más de lo que ejecuta.** Medido: 2,5 % del conocimiento se carga solo; el resto depende de que alguien vaya a buscarlo. En 48 h medidas, las 4 piezas que se cargaban solas funcionaron y las 5 que había que ir a buscar fallaron | pelo agujereado: referencias, lección y herramienta existían, no se invocó ninguna |
| 2 | **Un valor correcto en los datos e invisible en pantalla NO está hecho** | atributo de escudos pintado y nunca cableado al material |
| 3 | **Métricas ciegas**: miden algo real que no es la pregunta | *"¿algo del archivo tiene color?"* aprobó una avispa blanca porque sus ojos tenían tinte |
| 4 | **Prosa correcta que nunca baja a geometría** | *"patas palmeadas, cuello extensible"* → cuatro conos iguales y una esfera |
| 5 | **Parámetros de MEDIDA vs de ESTRUCTURA**: los escalares salen de una ficha y siempre se escriben; los que deciden si la cosa lee (qué plano ocupa cada parte, qué ángulo, qué la limita) siempre se saltean | tortuga con todos los números en banda que no leía como tortuga |
| 6 | **Pintar estructura sobre una superficie continua no da esa estructura** | cáscara offset de un cráneo es, geométricamente, un gorro |
| 7 | **Un arreglo a medias es un bug** | se agregaron los ojos al rango y quedaron fuera cejas y narinas |
| 8 | **Una constante obsoleta dentro de un gate es peor que no tener gate** | el gate pasaba, así que el defecto parecía decisión de diseño |
| 9 | **El motor de destino es ground truth** | 6 criaturas aprobadas por el render del generador salieron blancas en Godot: los nodos de shader no sobreviven la exportación, y el exportador no falla |
| 10 | **Un término técnico compuesto puede aplicarse a medias** | se implementó la primera mitad de *"lateral-sequence diagonal-couplet"* |
| 11 | **Si el sujeto existe en la realidad, la estructura faltante es un fallo de investigación** | la postura esparrancada de una tortuga estaba a una búsqueda de distancia |
| 12 | **El banco de pruebas también puede ser ciego** | la sonda para aislar un material usaba planos; la textura estaba bandeada sobre el eje que un plano tiene constante. Devolvió "liso" sin error y **confirmó una conclusión falsa** |
| 13 | **El ojo del agente falla en las DOS direcciones** | declaró que el piso "leía plástico" cuando ya medía mejor que la referencia; el defecto real estaba en otra parte y no se había mirado |

Además hay un catálogo aparte de **errores silenciosos de API**: formato de color con conversión
de espacio asimétrica (colores 12× más oscuros), índices de vértice obsoletos al crearse, claves
de forma que heredan la suma de las anteriores, emisión que colapsa a constante al exportar,
escala de textura mal elegida indistinguible de material roto. **Ninguno lanza excepción.**

---

## 3. La tesis

Casi ningún fallo de la lista es de conocimiento: el agente sabía la técnica en casi todos los
casos. Los fallos son de **verificación** — instrumento equivocado, momento equivocado, o
pregunta equivocada.

Y hay una asimetría que lo agrava: en este flujo **el error silencioso es el modo normal, no la
excepción**. Blender no avisa cuando una textura no varía. El exportador no avisa cuando descarta
un material. Un `grep` roto y un `grep` vacío son idénticos. Un script de parcheo que no encuentra
su patrón sigue adelante contento.

En un entorno así, el agente que "mira el resultado y opina" está garantizado a aprobar defectos.

---

## 4. Remedios implementados y su estado honesto

| Remedio | Estado real |
|---|---|
| Preflight escrito antes de construir | Funciona cuando se ejecuta; el problema es que se saltea |
| Métrica definida antes del build | Funciona. Definida después, uno elige la que aprueba lo que ya hizo |
| Poste de referencia de 1,8 m en toda lámina | En los generadores nuevos |
| Gate que falla el build si no hay evidencia en el **tamaño de uso** | El build es su propio control; nada externo puede olvidarlo |
| Render de verdad desde el archivo exportado | Implementado tras el caso de las 6 criaturas blancas |
| Gate que verifica que un material **varía** sobre la geometría | Nuevo (lección 12). Cubos, no planos; métrica de alta frecuencia, no desviación estándar |
| Gate que bloquea el cierre de turno si el asset es más nuevo que su lámina | **Tiene un agujero conocido**: un asset cuyo producto es un render y no un archivo 3D escapa por completo |
| Biblioteca de recetas + lecciones versionadas | Crecen bien. El problema es la activación, no el contenido |

Un dato que vale por sí solo: la herramienta escrita para atrapar la lección 3 **cayó en la
lección 3** — usaba desviación estándar, que sobre un cubo mide el sombreado entre caras y no la
textura. Un control uniforme puntuaba 0,058 y el material realmente texturado 0,008: el
instrumento estaba invertido y habría aprobado todo material plano. Sólo se detectó porque se
pasó por el gate un caso que se sabía malo.

---

## 5. Preguntas

1. **Activación (patrón 1).** Es el que no sabemos atacar: el conocimiento está, no se invoca, y
   agregar documentación lo empeora. ¿Qué mecanismos conocés que fuercen la consulta del
   conocimiento existente en el momento correcto, sin depender de que el agente se acuerde?

2. **Cobertura de gates.** Nuestro control se dispara comparando marcas de tiempo entre el asset
   y su lámina de revisión, y ya encontramos un agujero. ¿Qué otros agujeros ves en un control
   basado en marcas de tiempo? ¿Qué diseño usarías en su lugar?

3. **Juicio vs métrica.** Tenemos evidencia de que el juicio a ojo falla en las dos direcciones.
   ¿Hasta dónde te parece razonable reemplazar juicio por métrica, y **en qué casos la métrica es
   peor que el ojo**?

4. **Elección de métrica.** Comparamos media y desviación estándar de luminancia por región contra
   la referencia. Es burdo: no captura estructura, ni frecuencia espacial, ni si el defecto está
   donde importa. ¿Qué métricas de comparación de imagen recomendarías que sigan siendo baratas
   de calcular y fáciles de interpretar?

5. **Detección de fallos silenciosos.** ¿Hay forma sistemática de detectar, antes de renderizar,
   que una textura procedural no varía sobre la geometría a la que está aplicada? Nos interesa
   cualquier verificación automatizable — nuestra solución actual es empírica (renderizar cubos y
   medir alta frecuencia) y nos gustaría algo analítico sobre el grafo de nodos.

6. **Lo que no estamos viendo.** Mirando el método completo, ¿cuál te parece el defecto
   estructural más grande que este documento **no** menciona? Ese es el que más sirve.

---

*Fuente completa: `LECCIONES.md` (13 lecciones con los casos), `CREATION_PROTOCOL.md` (el
protocolo), `recetas/RECETAS.md` (biblioteca de recetas verificadas).*
