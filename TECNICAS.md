# TECNICAS.md — trucos observados en referencias, traducidos a conocimiento del motor

> Fuente: batch de referencias 2026-07-18 (`game/docs/art/_references/` en DungeonParty-A,
> síntesis por tema con la palabra de Joan). Este archivo es la traducción TÉCNICA:
> cómo se hace cada truco, si es automatizable headless con bpy, y dónde encaja en
> una escena. Leerlo junto a `recetas/RECETAS.md` antes de generar escenas nuevas.

## Norte (Joan, 2026-07-18): ESCENAS COMPLETAS, no cosas aisladas

El motor compone escenas razonando como diseñador. Regla de presupuesto que emerge
de estas referencias: **cada elemento gasta según su distancia al foco**.

| Capa | Técnica | Costo |
|---|---|---|
| Fondo lejano | planos-imagen + parallax (§1) | casi cero |
| Estructura media | kit-bash modular (§2) | un módulo, N instancias |
| Relleno/densidad | scatter por capas (§4) | procedural |
| Foco (personaje/prop hero) | geometría real, sculpt/pack | todo el presupuesto |
| Elementos 2D incrustados | billboard alpha (§3) | casi cero |
| Estilo global | lookdev preset sobre TODA la escena | uniforme |
| Presentación | preset showcase/ficha (§9) | render aparte |

## Capa ESCENA

### §1 parallax_flat_bg — fondo de imagen plana con profundidad falsa
- **Logra**: vista exterior/fondo en movimiento sin geometría (ventana de tren).
- **Cómo**: 2-4 capas PNG con alpha a distintas distancias de cámara, material
  unlit/emission, cámara con paneo sutil → el movimiento relativo entre capas vende
  la profundidad. DOF leve ayuda.
- **bpy**: PARCIAL. Planos + materiales + cámara animada = 100% scripteable. El corte
  de la imagen en capas de profundidad no (necesita depth estimation o capas del artista).
- **Ojo**: para fondos in-game esto rinde más implementado en Godot runtime (sprites a
  distinta velocidad) que pre-renderizado en Blender. En el motor sirve para ESCENAS DE
  RENDER (presentaciones, escenas tipo "Filomeno en catedral": la catedral lejana = planos).
- **Fuente real**: el clip era DaVinci Resolve Fusion, no Blender — la técnica es idéntica.
  Ref: `camera_flat_bg_trick`.

### §2 kitbash_modular — estructura por módulo repetido
- **Logra**: pasajes/arquitectura completa desde UN módulo (arco → túnel).
- **Cómo**: módulo con origin en punto de snap → Array+Curve modifier (clásico) o
  GN `Curve to Points` + `Instance on Points` con jitter (variante orgánica). Prop hero
  colocado a mano ROMPIENDO la repetición.
- **bpy**: COMPLETA. Modifiers vía `obj.modifiers.new`; node group GN construible entero
  por API. Gotcha: los `bl_idname` de nodos GN cambian entre versiones — verificar en 5.1.2.
- **Lección del post original**: el terreno estaba sobre-modelado para lo que el follaje
  terminó tapando — no detallar lo que se va a cubrir.
- Ref: `blender_workflow_arcos`.

### §3 billboard_alpha — imagen 2D incrustada en 3D
- **Logra**: pixel art / imagen plana dentro del mundo sin marco visible.
- **Cómo**: quad + Image Texture con alpha, blend CLIP, sin sombra, Track-To cámara
  si billboard. (El clip original era el truco de Minecraft de item frames invisibles —
  mismo principio: matar el borde, dejar solo la imagen.)
- **bpy**: COMPLETA.
- **Complemento (pedido de Joan)**: la inversa — renderizar un asset 3D COMO sprite
  pixel art (íconos de minimapa/bestiario): render 32-64px flat-lit (Workbench/Eevee)
  + posterize/paleta reducida. La cuantización de paleta se hace en Pillow post-render,
  no en el compositor (no hay nodo nativo).
- Ref: `pixelart_ui`.

### §4 scatter_biome — densidad realista por capas
- **Logra**: bosque/bioma denso que se siente lugar real.
- **Cómo**: terreno por heightmap → capas de cobertura apiladas (pasto → plantas →
  rocas/troncos → árboles hero), cada una con reglas de densidad propias (pendiente,
  altitud, noise) → niebla volumétrica + HDRI + focal larga para escala. Un elemento
  móvil (auto, animal) da vida y escala.
- **bpy**: PARCIAL-ALTA. El addon de los videos virales (Geo-Scatter) es pago/cerrado,
  pero el mecanismo es replicable en GN vanilla: `Distribute Points on Faces` con máscara
  de densidad + `Instance on Points` multi-colección + `Random Value`. Ya es el patrón
  de blender-asset-smith.
- **Expectativa honesta**: el realismo viral depende de assets Megascans; con
  Kenney/Quaternius la ESTRUCTURA de densidad se logra, la fidelidad no llega a eso.
- Ref: `biome_landscape`.

## Capa FORMA

### §5 sketch_to_mesh — trazo 2D → geometría
- **Qué era en verdad**: addon pago **Deep Paint** (Gaku Tada): Grease Pencil strokes →
  mesh (GP to Mesh) + Quick Modifier (Solidify/Subsurf/Shrinkwrap). Textura con
  **Ucupaint** (gratis, capas estilo Photoshop sobre un node group).
- **bpy**: PARCIAL. Sin el addon: curvas paramétricas generadas por código como "trazo"
  + `bpy.ops.gpencil.convert` o `bmesh` para engrosar/rellenar. Ucupaint = node groups
  100% scripteables; la pintura a mano no tiene sentido headless.
- **Para el motor**: entrada = curvas generadas por código, no replicar el addon.
- Ref: `mouse_autoline_model`.

### §6 personaje_pipeline — lo que el video "fácil" realmente muestra
- **Corrección**: el clip ("POV you finally understood Blender") NO es primitivas simples —
  es sculpt-heavy normal (Multires/Dyntopo, modeló hasta los dientes) + retopo + bake.
  La etiqueta "fácil" del reel es marketing.
- **Lo que SÍ es atajo real**: ropa por Solidify sobre geometría cortada de la base
  (shrinkwrap + solidify) — scripteable. Retopo Quadriflow y bake de normales:
  headless-safe.
- **Para el motor**: anatomía orgánica sigue siendo manual/pack (regla ya establecida);
  automatizar SOLO ropa + retopo + bake, como el patrón golem.
- Ref: `character_creation_easy`.

## Capa ESTILO (lookdev)

### §7 painterly_eevee — estilo a_iwaac (limón/cebolla/calabaza/frasco)
- **Logra**: 3D expresivo realtime que lee como ilustración ("more expressive 3D art,
  less UE5 hyperrealism").
- **Cómo (los posts traen el desglose ANOTADO)**: Eevee realtime, Solidify para contorno,
  base texture pintada + roughness + normal map, transmission para vidrio, compositing
  final, acentos con Grease Pencil. Las refs `ref_06`/`ref_07` de `organic_modeling_style`
  tienen los breakdowns legibles — son recetas directas.
- **bpy**: shader COMPLETO por API; la textura pintada es el paso manual.
- **Candidato**: preset lookdev nuevo `painterly_eevee.py` junto a `cel_banded.py`.

### §8 clay_look — plasticina digital
- **Qué era en verdad**: escultura FÍSICA real (arcilla, guantes) — referencia de look,
  no de técnica.
- **Traducción Blender**: Principled + SSS radio bajo + fingerprints procedurales
  (Noise/Voronoi vía Bump) + roughness con micro-detalle + luces área grandes suaves.
  Feel stop-motion: animar on-2s + jitter de vértices con seed fija.
- **bpy**: shader y timing COMPLETOS por API (procedural, determinista). La escultura no.
- **Anti-nota hermana**: la manta roja fluida era Cinema4D + ComfyUI, no Blender.
  Equivalente: cloth sim + wind + loop por cache MDD, con heurística RMS de vértices
  para sugerir el punto de loop (juicio visual final humano).

## Capa PRESENTACIÓN

### §9 showcase_ficha — cómo se MUESTRA un modelo (pedido explícito de Joan)
- **Logra**: formato para (a) mostrar avances a Joan, (b) fichas del bestiario in-game
  (canon: "El bestiario de Axlin").
- **Plantilla (estilo a_iwaac)**: objeto grande centrado, fondo plano de un color,
  iluminación pareja, anotaciones alrededor (nombre, rasgos, desglose si aplica).
- **bpy**: COMPLETA — es un preset de cámara+luz+fondo, primo del gate 360 pero con
  1 ángulo hero + composición de ficha. El texto/anotación se compone en Pillow
  post-render.
- **Siguiente paso concreto**: `lookdev/showcase_ficha.py` que tome cualquier GLB y
  saque su ficha. Sirve YA para presentar slime/golem/King Slime a Joan.

## Animación por-miembro

### §10 gait_brokenness — zombificación paramétrica de caminatas
- **Del análisis de la cabra zombie** (ojo: el frame no muestra el walk cycle; los
  fundamentos vienen de investigación, no del clip): un ciclo de marcha cuadrúpedo
  normal (seno por pata, fases 0/90/180/270) se "zombifica" con 5 quiebres:
  asimetría de fase entre lados, timing irregular por ciclo, pie que nunca despega
  del todo (arrastre), contra-rotación de columna ≈ 0, lean adelante del centro de masa.
- **Codificable como UN parámetro** `gait_brokenness: 0.0-1.0` (ruido determinista con
  seed) aplicable a CUALQUIER ciclo base — sirve para todo el bestiario corrupto/no-muerto
  del juego, no una criatura puntual. Encaja con el patrón golem (animación por-miembro
  en código).

## Lecciones de verificación (2026-07-18)

De 9 clips técnicos investigados, **4 no eran lo que parecían**: el parallax era Fusion
(no Blender), la manta era Cinema4D+ComfyUI, la plasticina era escultura física, y la
criatura con cuernos posiblemente sea asset generado por IA (sin walk cycle visible en
el frame). Regla: **un reel no es evidencia de técnica Blender hasta leer su caption y
UI** — la traducción al equivalente Blender hay que hacerla explícita, como acá.
