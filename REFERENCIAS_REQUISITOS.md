# Referencias para modelar — qué fotos mandar y cómo las leo

Nace de la rana (2026-10-14). Con una sola foto de frente se modelaron tres versiones con la
profundidad mal (0,97 contra 0,67 real), una espalda inventada y la base equivocada: la base son
dos bulbos, no un plano. Las seis fotos de órbita lo resolvieron en una sola mirada. Las fotos
son el input más barato del pipeline; cada vista que falta cuesta iteraciones.

## Para Joan — las fotos

**Mínimo: 6 vistas, cada una con el objeto centrado y entero en el cuadro.**

| # | Vista | Para qué la uso |
|---|---|---|
| 1 | Frente | silueta principal, cara y gráficos |
| 2 | Atrás | espalda (lo que más invento si falta) |
| 3 | Costado izquierdo | **profundidad**, el número que más se equivoca |
| 4 | Costado derecho | asimetrías (todo lo hecho a mano las tiene) |
| 5 | Arriba (cenital) | planta: qué tan redondo o cuadrado es |
| 6 | Abajo | la base: si apoya plano, en patas o en lóbulos |

Para que se puedan medir:
- **Cámara a la altura del objeto** (no desde arriba) y **siempre a la misma distancia**. Así las
  proporciones entre vistas se pueden comparar.
- **Lejos y con zoom** mejor que pegado: de cerca, la perspectiva deforma (lo cercano sale más
  grande).
- **Fondo liso y de un color que el objeto no tenga.** Con eso recorto la silueta solo, sin
  dibujarla a mano.
- **Algo de escala** (regla, moneda) en al menos una foto, o decirme la medida real.
- Si hay gráficos (dibujos, estampados), **una foto de cerca y de frente a cada uno**.
- Opcional, y muy útil: unas líneas encima marcando "esto es el brazo / el anca", como en
  `rana/_references/rana_ref_anatomia_anotada.png`.

## Para mí — cómo se leen (antes de escribir bpy)

1. Copiar las fotos a `<asset>/_references/<asset>_ref_orbita_<n>.jpg` y armar una hoja de contacto.
2. **Medir, no estimar:** para cada vista, sacar el bbox de la silueta por color
   (sin numpy: PIL alcanza) → ancho/alto de frente, profundidad/alto de costado.
   Esos números entran a la ficha **antes** de construir.
3. Escribir la ficha `<asset>/_references/<asset>_synthesis.md`: qué es · partes · proporciones
   medidas · qué se ve en cada vista · gráficos · métrica de éxito.
4. **Métrica = las siluetas.** Se renderiza la silueta del modelo en las mismas vistas, se
   normaliza por bbox y se compara contra la de la foto (IoU por vista + ratios). Así es un número
   el que dice si la forma está bien, no mi ojo sobre un render.
   **El IoU solo no alcanza** (medido en la rana): normalizado por bbox no ve la proporción (la
   v3 sacó 0,90 de costado con profundidad 1,00 contra 0,67 real) y tampoco castiga bultos chicos
   en el contorno (la v4 lo pasaba leyéndose como "4 bolas" desde atrás). Hacen falta las tres
   medidas juntas: **ratio + IoU + suavidad del contorno**, y cada una con su control positivo
   (una versión mala conocida que la métrica TIENE que reprobar).
5. **Leer la superficie, no solo la forma:** liso, facetado, rugoso o tallado son cosas
   distintas. En la rana, "cortes de cuchillo" se leyó como low-poly, y en realidad era una talla
   lisa con planos casi imperceptibles. Mirar un primer plano de la foto antes de elegir la técnica.
6. Recién ahí se modela, y el veredicto final se da mirando el render lado a lado con la foto
   desde todas las vistas.
