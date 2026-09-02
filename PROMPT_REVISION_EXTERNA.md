# Prompt para acompañar `MOTOR_BUNDLE.md`

Pegá el texto de abajo junto con el archivo. Es idéntico para los cuatro modelos
a propósito: si el prompt cambia, las respuestas no se pueden comparar.

---

Te adjunto el documento interno de un método de trabajo llamado "el motor": un
sistema donde una persona y un agente LLM generan assets 3D y renders con
Blender en modo headless, sin abrir la interfaz gráfica. El agente nunca ve la
escena: sólo renders que él mismo dispara y después lee como imagen.

Quiero la revisión más exhaustiva que puedas dar. La estoy pidiendo en paralelo
a varios modelos para contrastar, así que necesito que respetes la estructura de
salida al final de este mensaje.

## Qué necesito de vos

Una crítica del **método de trabajo**, no del resultado artístico. Me interesa
específicamente lo que el documento no ve de sí mismo.

## Reglas de la respuesta

Estas reglas importan más que la cortesía. Si las rompés, la respuesta no me
sirve:

1. **No resumas el documento.** Lo escribí yo. Cada párrafo que dedicás a
   contarme lo que ya sé es un párrafo que no dedicaste a lo que no sé.
2. **No elogies.** Nada de "es un método sólido y maduro". Si algo está bien,
   decilo en una línea y pasá a los límites de eso que está bien.
3. **Anclá cada afirmación** a una cita, un número o un caso concreto del
   documento. Una crítica que podría aplicarle a cualquier equipo no me dice
   nada sobre el mío.
4. **Distinguí lo que sabés de lo que suponés.** Marcá explícitamente cuándo
   estás extrapolando desde práctica general en vez de desde el documento.
5. **No asumas buena fe sobre mis mediciones.** Varios números del documento
   (porcentajes de activación, desviaciones estándar, umbrales de gates) son
   auto-reportados por el propio sistema que se está evaluando. Cuestionalos.
6. **Si creés que una de mis conclusiones es incorrecta, decilo directo** y
   explicá qué evidencia te haría cambiar de opinión.
7. **Longitud: no hay límite.** Prefiero 5.000 palabras exhaustivas a 800
   pulidas. No cierres secciones antes de agotarlas. Si tenés que elegir entre
   profundidad y cobertura, elegí profundidad y decime qué dejaste afuera.

## Estructura de salida (respetala en orden)

**1. Veredicto (máximo 8 líneas).**
Qué es esto realmente, en qué percentil de rigor lo ubicás comparado con equipos
que hayas visto, y cuál es su modo de muerte más probable.

**2. Los defectos estructurales que el documento NO menciona.**
La sección más importante. Mínimo tres, ordenados por gravedad. Para cada uno:
qué es, por qué es invisible desde adentro, qué evidencia del documento lo
delata, y qué pasa si no se corrige.

**3. Auditoría de la tesis central.**
El documento sostiene que casi ningún fallo es de conocimiento sino de
verificación — instrumento equivocado, momento equivocado, pregunta equivocada.
¿Es cierto? ¿O es una tesis cómoda, que le echa la culpa a los instrumentos
cuando el problema es otro (el modelo de trabajo, la relación humano-agente, la
ambición del alcance, la ausencia de un criterio estético explícito)? Argumentá
en contra de la tesis lo mejor que puedas, aunque termines aceptándola.

**4. Las seis preguntas.**
El documento cierra con seis preguntas numeradas. Respondelas una por una, con
subtítulo propio. Nada de respuestas de manual: quiero mecanismos concretos,
nombres de técnicas, y el costo de implementar cada uno. Si una pregunta está
mal planteada, reformulala antes de responderla y decí por qué.

**5. Dónde me estoy engañando.**
Momentos del documento donde detectes auto-indulgencia, una métrica elegida
porque aprueba, una lección declarada aprendida que la evidencia no sostiene, o
un remedio marcado como "implementado" que probablemente no funcione. Sé
específico y citá.

**6. Priorización.**
Tabla de todo lo que recomendás: intervención · impacto esperado · costo ·
cuánto tarda en verse el efecto. Ordenada por relación impacto/costo. Marcá
explícitamente qué NO haría en tu lugar, y qué del sistema actual conviene
dejar de hacer.

**7. Predicciones falsables.**
Tres a cinco, con esta forma: *"si implementan X, en N semanas deberían observar
Y; si en cambio observan Z, mi diagnóstico era incorrecto"*. Sin esto no puedo
saber después si tu revisión sirvió.

**8. Qué te falta para responder mejor.**
Qué información pedirías, qué medirías, qué artefacto querrías ver.

**9. Confianza.**
Por sección, alto / medio / bajo, con una línea de por qué.

## Contexto adicional que puede importarte

- El repo real es privado; el archivo adjunto es su núcleo conceptual, sin el
  código de los generadores (~550 KB excluidos). Si una crítica requiere ver
  código que no está, decilo en la sección 8.
- Los documentos están en español salvo el protocolo de creación y el código,
  que están en inglés.
- El equipo son dos: una persona con formación en arquitectura y diseño, y un
  agente LLM. No hay más gente para repartir revisión cruzada.
- Es trabajo real en producción, no un experimento académico. Las restricciones
  de tiempo y de tokens son reales.
