# Receta `engordar_anatomico` — spec de implementación

**Estado**: DISEÑO (pre-verificación). Por regla de admisión de `RECETAS.md`, NO entra al índice
hasta pasar gate+ojo en un caso real sobre Filomeno. Este doc es el spec para implementarla.
**Origen**: 2 fallos del mismo tipo (2026-07-13 warp de perfil "muy delgado"; 2026-07-16 escalado
por filas "muslo ultra grande"). Patrón raíz: adjetivos de tamaño implementados como operaciones
de eje/escala sin semántica anatómica.
**Alcance**: dos medios — (a) malla riggeada en Blender/bpy (Filomeno base_v2 ~12.6k verts,
Filomeno_rig 20 huesos), (b) PNG de referencia fondo blanco.

---

## 1. PRINCIPIOS — qué ES engordar

Engordar NUNCA es una operación de eje mundial ni de escala. Es **agregar tejido blando SOBRE un
andamiaje que no cambia**: el desplazamiento va **radial al eje del hueso** (blend con la normal
suavizada), la magnitud es **proporcional al grosor local** (mismo "más gordo" = +mucho en torso,
+casi nada en muñeca), modulada por un **mapa de masa por región anatómica** (la grasa se deposita
sobre músculo/víscera, casi nada sobre hueso), con **sesgo de gravedad** (panza/papada/pecho
cuelgan), **cero en landmarks de identidad** (cráneo, orejas, hocico, paws) y **articulaciones que
se ENTIERRAN** (codo/rodilla pasan de bulto óseo a hoyuelo — valen menos que sus vecinos, jamás
más). Los largos de hueso y la silueta-identidad se conservan siempre: es el modelo de toda la
industria (MakeHuman targets, SMPL shape PCs, Sea of Thieves compass, BodySlide) — deformación
esculpida/aprendida con esta distribución, nunca scale de eje.

Fuentes: [fat bodies tutorial](https://ebonrune.home.blog/2017/12/22/fat-bodies-tutorial/) ·
[Game Developer — fat characters in games](https://www.gamedeveloper.com/game-platforms/better-ways-to-design-fat-characters-in-games) ·
[MakeHuman targets](https://static.makehumancommunity.org/mpfb/docs/assets/targets.html) ·
[SMPL (patente)](https://patents.google.com/patent/US10395411B2/en) ·
[MetaHuman body params](https://dev.epicgames.com/documentation/metahuman/metahuman-creator-body-params-tool-in-unreal-engine) ·
[Zhou et al. SIGGRAPH 2010 — Parametric Reshaping](https://hongbofu.people.ust.hk/projects/ParametricBodyReshaping/index.html)

### Mapa de distribución de masa — oso bípedo toon (gain 0..1)

⚠️ **Sin fuente directa para oso toon** — es síntesis de reglas humanas/animales (grasa sobre
músculo/víscera, gravedad, articulaciones enterradas). Punto de partida: **calibrar contra el
prototipo de Joan**, no dato medido.

| Región                          | gain | gravity_sag | Nota |
|---------------------------------|------|-------------|------|
| panza/abdomen (frente)          | 1.00 | alto (down+out) | overhang; máximo absoluto |
| ancas/glúteos                   | 0.85 | medio (down) | |
| muslo interno                   | 0.80 | — | cierra el gap: los muslos se tocan |
| papada/cuello                   | 0.70 | alto (down) | doble mentón |
| flancos/love-handles            | 0.65 | medio | rolls |
| pecho                           | 0.60 | medio (down) | cae, no apunta al frente |
| muslo externo                   | 0.60 | — | |
| pubis/bajo-vientre              | 0.55 | — | recibe el "derrame" de la panza |
| lower back                      | 0.55 | — | |
| brazo superior                  | 0.50 | leve | |
| mejillas/base hocico            | 0.50 | leve | la estructura ósea se esconde |
| pantorrilla                     | 0.30 | — | |
| antebrazo                       | 0.25 | — | |
| cráneo                          | 0.05 | — | tamaño ~constante |
| manos/paws, pies                | 0.05 | — | casi sin grasa |
| orejas/punta hocico/nariz/ojos  | 0.00 | — | landmark de identidad = FIJO |
| articulaciones (codo/rodilla/muñeca/tobillo) | 0.00 | — | se hunden: hoyuelo, no bulto |

Regla dura transversal: **axial_lock** — la masa crece radial, NUNCA alarga huesos.

---

## 2. RECETA 3D (bpy, malla riggeada)

**Insight central**: los vertex groups del skinning de Filomeno_rig YA SON las máscaras
anatómicas — cero segmentación nueva ([Blender bone deform docs](https://docs.blender.org/manual/en/latest/animation/armatures/bones/properties/deform.html):
la influencia se multiplica por el peso del vértice en el grupo). El primitivo nativo del gesto es
Shrink/Fatten ([docs](https://docs.blender.org/manual/en/latest/modeling/meshes/editing/transform/shrink-fatten.html)),
pero acá se implementa a mano para controlar dirección/máscara/taper.

### Algoritmo

```python
def engordar(obj, arm, gains, amount, gravity=0.35, normal_blend=0.25,
             protect=("head","hand.L","hand.R","foot.L","foot.R"),  # nombres reales del rig al implementar
             smooth_iters=3, key_name="fat"):
    # gains: {hueso: gain} del mapa §1 (matchear a los 20 huesos reales de Filomeno_rig)
    # amount: escalar del adjetivo — SIEMPRE fracción del radio local (0.20 = +20% de grosor)

    # 0) precomputar por hueso con gain: head/tail en mundo, eje normalizado, largo
    # 0b) precomputar normales SUAVIZADAS (promedio 1-ring de v.normal, 2 iters)
    #     — normal cruda genera spikes; suavizarla es práctica de ingeniería, no paper canónico

    disp = [Vector0] * len(verts)
    for v in verts:
        # 1) MÁSCARA = pesos de skinning de los huesos con gain; hueso dominante = mayor peso
        mask = clamp(sum(w for hueso_con_gain), 0, 1)
        # 2) PROTECCIÓN: desvanecer sobre grupos protegidos -> mask *= (1 - w_protegido)
        if mask < 1e-4: continue

        h, ax, L = bone[dom]
        t = clamp((p - h).dot(ax) / L, 0, 1)      # proyección sobre segmento del hueso
        radial = p - (h + ax * t * L)              # vector radial; |radial| = radio local
        r_local = radial.length                    # (degenerado: caer a la normal suavizada)

        # 3) TAPER articular: parábola 4t(1-t) = 0 en head/tail, 1 al medio del hueso
        taper = 4 * t * (1 - t)

        # 4) DIRECCIÓN: blend radial <-> normal suavizada, luego axial_lock
        d = lerp(radial.normalized(), n_suave, normal_blend).normalized()
        d -= d.project(ax)                         # mata todo componente axial: no alarga hueso

        # 5) MAGNITUD proporcional al grosor local + gravedad
        mag = amount * gains[dom] * mask * taper * r_local
        disp[v] = d * mag + DOWN * (mag * gravity * sag[region(dom)])   # overhang panza/papada

    # 6) SUAVIZADO Laplaciano del CAMPO (clave anti-escalón): 3 iters,
    #    disp[v] = 0.5*disp[v] + 0.5*avg(disp vecinos 1-ring)   (adyacencia vía bmesh)

    # 7) SHAPE KEY (nunca bake directo): Basis si falta, key "fat_<adjetivo>", value=1.0
    #    -> slider vivo, reversible, componible (MakeHuman-style: instrucciones = suma de keys)
```

Por qué cada pieza mata un fallo conocido:
- **radial al hueso** → el muslo se redondea perpendicular a SU eje, no al eje X del mundo (el scale mundial cizalla limbs diagonales y traslada partes lejanas del origen — el "pedazo de muslo").
- **pesos de skinning como máscara** → falloff continuo entre regiones gratis; sin corte duro entre "filas".
- **taper 4t(1-t) + protect** → articulaciones y extremos en 0; con el smooth quedan como hoyuelos.
- **proporcional a r_local** → un solo `amount` sirve para torso y muñeca.
- **axial_lock** → proporciones/largos intactos (mata el fallo "muy delgado pese a calzar métrica" a la inversa).
- **normal_blend bajo (0.25)** → forma orgánica sin el riesgo del offset puro por normales: el offset se auto-interseca en cóncavos cuando d > 1/κ ([Patrikalakis–Maekawa–Cho, MIT](https://web.mit.edu/hyperbook/Patrikalakis-Maekawa-Cho/node227.html)) — y los cóncavos de un personaje son exactamente axila/entrepierna/cuello. Si aparece pinch: bajar `normal_blend`.

### Gate (verificación numérica + ojo, en este orden)

1. **Circunferencia por anillo** a t=0.5 de cada hueso con gain: ratio después/antes ≈ 1 + amount·gain (tolerancia ±30% del delta).
2. **Anillos articulares** (t≈0.05 y t≈0.95): ratio ≈ 1.00 ±5% — rodilla/codo/muñeca NO crecen.
3. **Extensión axial** del set de vértices por hueso: sin cambio (±2%) — no se alargó nada.
4. **Landmarks** (punta hocico, orejas, paw tips, ojos): |Δpos| < ε.
5. **Auto-intersección**: probe BVH self-overlap en axila/entrepierna/cuello (usar `preflight_destructivo.py` antes si se banconea el resultado).
6. **Eye-review con `corporeo_glance.py`** — OBLIGATORIO. La métrica sola ya demostró no bastar (fallo histórico #1).

---

## 3. RECETA 2D (Python/PIL/numpy/scipy/skimage, PNG fondo blanco)

**Elección**: MLS-similarity ([Schaefer et al. SIGGRAPH 2006](https://people.engr.tamu.edu/schaefer/research/mls.pdf),
impl numpy de referencia [Jarvis73/Moving-Least-Squares](https://github.com/Jarvis73/Moving-Least-Squares))
— 90% de la calidad de ARAP ([Igarashi 2005](https://www-ui.is.s.u-tokyo.ac.jp/~takeo/research/rigid/index.html))
con 20% del código, fórmula cerrada por pixel, cero dependencias nuevas. Cada pixel se transforma
como similaridad LOCAL (rotación+escala uniforme, sin cizalla) → rasgos internos coherentes.
Arquitectura general = patrón Zhou 2010: atributo semántico → warp body-aware, no manipulación de ejes.

### Algoritmo

```python
def engordar_2d(img, gains, amount):
    # 1) SILUETA: mask = ~near_white(img); contour = skimage.find_contours(mask)[0]
    # 2) EJE + GROSOR LOCAL: skel, dist = skimage.morphology.medial_axis(mask, return_distance=True)
    #    -> dist en el skel = halfwidth REAL por región (el análogo 2D del radio del hueso)
    # 3) SEGMENTAR el contorno por región anatómica (mapa §1):
    #    bandas y/x calibradas sobre la pose canónica del ref de Filomeno + landmarks
    #    (cara arriba, panza banda central, muslos infero-laterales, paws extremos)
    # 4) CONTROL POINTS sobre el contorno (cada ~10 px):
    #    n_i   = normal exterior local (de la tangente del contorno, NO eje X)
    #    d_i   = amount * gains[region(p_i)] * halfwidth_local(p_i)   # proporcional al grosor
    #    d_i  += componente DOWN * gravity[region] para panza/papada
    # 5) *** LA CLAVE anti-"muslo ultra grande" ***
    #    d = gaussian_filter1d(d, sigma=3, mode="wrap")   # suaviza a lo largo del contorno:
    #    jamás corte duro entre regiones
    #    d[cerca_de(anchors)] = 0                          # cara, paw tips, línea de piso
    #    Q = P + d[:,None] * N
    # 6) ANCLAS INTERIORES: puntos sampleados del medial axis como controles fijos (src == dst)
    #    -> engordar no traslada al personaje ni le rompe la pose
    # 7) WARP MLS-similarity con mapping INVERSO (grilla gruesa cada 4px + upsample bilineal;
    #    resamplear con scipy.ndimage.map_coordinates, order=1, cval=blanco)
    # 8) GATE: re-medir halfwidth por región con medial_axis -> ratio ≈ 1 + amount*gain
    #    + eye-review SIEMPRE
```

Si la malla 3D ya fue engordada con la receta §2, **derivar el warp 2D de la proyección de la
deformación 3D** (patrón exacto de Zhou 2010) — garantiza coherencia 2D↔3D. El pipeline standalone
de arriba es el fallback cuando solo existe la imagen.

Validación manual equivalente (para comparar a ojo): Photoshop Liquify "Bloat" con freeze mask en
cara/paws, o Puppet Warp modo **Rigid** ([Adobe docs](https://helpx.adobe.com/photoshop/desktop/effects-filters/artistic-stylize-filters/distort-specific-image-areas-with-puppet-warp.html)).
Nunca Distort ni Transform>Scale.

---

## 4. PARÁMETROS — vocabulario de masa (adjetivo NL → parámetros)

Regla de despacho previa: **"más grande" (personaje entero) = escala uniforme isotrópica** — la
ÚNICA situación donde scale es legítimo. Todo lo demás ("gordo/flaco/ancho/macizo/panzón/cachetón")
entra a esta receta.

| Adjetivo | region_gains | amount | gravity | Nota |
|---|---|---|---|---|
| "más gordo" | mapa completo §1 | +0.20 | 0.35 | perfil grasa default |
| "un poco más gordo" | idem | +0.10 | 0.30 | |
| "mucho más gordo / bien gordo" | idem | +0.35 | 0.40 | |
| "más flaco" | idem | −0.15 | 0.0 | inverso; articulaciones re-emergen |
| "más macizo / robusto / fornido" | pecho 0.9 · hombros/brazo sup 0.8 · espalda 0.7 · muslos 0.6 · pantorrilla 0.4 · panza 0.3 | +0.20 | 0.0 | músculo NO cuelga |
| "más ancho" (global) | como macizo + flancos/caderas 0.7 | +0.20 | 0.0 | |
| "hombros más anchos" | hombro/brazo sup 1.0 · pecho 0.4 · resto 0 | +0.25 | 0.0 | local |
| "más panza / panzón" | panza 1.0 · flancos 0.5 · pubis 0.5 · resto 0 | +0.30 | 0.50 | overhang |
| "cara más redonda / cachetón" | mejillas 0.6 · papada 0.7 · ojos/nariz/orejas 0.0 | +0.15 | 0.20 | cráneo fijo |

- Cada instrucción produce su **shape key nombrado** (`fat_gordo`, `fat_hombros`, …); se COMPONEN
  por suma como los targets de MakeHuman. Repetir el mismo adjetivo = ajustar el value del key
  existente, no apilar keys duplicados.
- Los gains del mapa §1 son defaults **editables por instrucción** ("más gordo pero sin panza" =
  perfil gordo con panza→0).
- Registrar en el motor como **semántica canónica**: adjetivo de tamaño → tuple
  `(region_gains, amount, gravity)` → `engordar(...)`. Jamás → transform.

---

## 5. ANTI-PATRONES (registrar junto a las anti-recetas de RECETAS.md)

1. **[HISTÓRICO 2026-07-16] Escalado horizontal por filas** hacia perfil de anchos → "muslo ultra
   grande, hombros ensanchados". Tres roturas simultáneas: dirección global (X del mundo, no
   perpendicular al miembro), sin semántica de región, sin continuidad entre filas (cada fila se
   transforma independiente — C0 roto; mismo modo de fallo documentado en seam carving sobre
   cuerpos: [CACM](https://cacm.acm.org/research/seam-carving-for-media-retargeting/)).
2. **[HISTÓRICO 2026-07-13] Warp de perfil que calza la métrica pero rompe la semántica** →
   "muy delgado". Corolario permanente: **calzar la métrica NO basta; eye-review siempre** (ya en
   anti-recetas como "escalados por bandas secuenciales contra métrica normalizada").
3. **Scale de eje mundial sobre un limb diagonal** → cizalla + alarga + traslada (el scale es
   respecto de un origen: partes lejanas se corren de lugar).
4. **Inflado puro por normales sin máscara ni suavizado** → pinch/auto-intersección en cóncavos
   (axila, entrepierna, cuello — falla cuando d > 1/κ) e infla landmarks (hocico, orejas, dedos)
   destruyendo identidad.
5. **Desplazamiento en unidades absolutas** (px, metros) en vez de proporcional al grosor local →
   la muñeca crece tanto como el torso.
6. **Fronteras de región como corte duro** — sin falloff (3D: pesos de skinning; 2D:
   gaussian_filter1d sobre el contorno) el borde entre regiones es un escalón visible.
7. **Alargar huesos / tocar el andamiaje al engordar** — la grasa es soft tissue; el esqueleto y
   las proporciones son la identidad (Sea of Thieves: toda variante comparte skeleton/rig).
8. **Articulaciones como bultos** — engordar las hunde (hoyuelo); si el resultado muestra
   rodillas/codos más gruesos que sus vecinos, la receta está mal aplicada.
9. **Bakear la deformación directo sobre la malla** en vez de shape key → irreversible, no
   componible, y el siguiente adjetivo opera sobre base corrupta.

---

## Fuentes principales

- Anatomía/arte: [ebonrune fat bodies](https://ebonrune.home.blog/2017/12/22/fat-bodies-tutorial/) · [Game Developer](https://www.gamedeveloper.com/game-platforms/better-ways-to-design-fat-characters-in-games) · [Brooke Eggleston](https://brookeseggleston.com/blog/draw-more-dynamic-character-bodies)
- Industria 3D: [MakeHuman targets](https://static.makehumancommunity.org/mpfb/docs/assets/targets.html) · [SMPL](https://patents.google.com/patent/US10395411B2/en) · [MetaHuman](https://dev.epicgames.com/documentation/metahuman/metahuman-creator-body-params-tool-in-unreal-engine) · [Sims 4 DMap sliders](https://aqxaromods.com/the-sims-4/articles_the_sims_4/1076-making-a-cas-slider-with-ts4morphmaker-using-a-deformer-map.html)
- Papers: [Igarashi 2005 ARAP](https://cs.brown.edu/people/jhughes/papers/Igarashi-ASM-2005/paper.pdf) · [Schaefer 2006 MLS](https://people.engr.tamu.edu/schaefer/research/mls.pdf) · [Zhou 2010 Parametric Reshaping](https://hongbofu.people.ust.hk/projects/ParametricBodyReshaping/index.html) · [offset self-intersection (MIT)](https://web.mit.edu/hyperbook/Patrikalakis-Maekawa-Cho/node227.html)
- Blender/tooling: [Shrink/Fatten](https://docs.blender.org/manual/en/latest/modeling/meshes/editing/transform/shrink-fatten.html) · [bone deform/envelopes](https://docs.blender.org/manual/en/latest/animation/armatures/bones/properties/deform.html) · [skimage medial_axis](https://scikit-image.org/docs/stable/auto_examples/edges/plot_skeleton.html) · [MLS numpy](https://github.com/Jarvis73/Moving-Least-Squares)

**Tramos sin fuente citable** (marcados en el cuerpo): (a) el mapa de coeficientes para oso bípedo
toon — síntesis a calibrar contra el prototipo; (b) suavizar el campo de desplazamiento como
mitigación de auto-intersección — práctica de ingeniería estándar, sin paper canónico que lo
formule así.
