# Librería de RECETAS del motor — índice (formato Voyager)

Cada receta = **código VERIFICADO en un caso real** + descripción de 1 línea + cuándo usarla +
gotchas + exemplar de invocación. Regla de admisión: una receta entra SOLO si pasó gate+ojo en
un caso real (referencia al commit donde se probó). Este índice es el retrieval — leerlo entero
antes de escribir bpy nuevo: si existe receta, SE USA; si el caso es nuevo, al resolverlo se
COSECHA acá (mismo aliento, como el manifest).

Patrón validado externamente: skill library de Voyager (arxiv 2305.16291 — skills transferidas
subieron el éxito de otro agente 0/3→2/3) + outer loop de SceneCraft. Tier A.

| Receta | Qué hace | Probada en |
|---|---|---|
| `sample_base.py` | Samplear la paleta REAL de la malla (nunca asumir del doc) | manchas-sellos 2026-07-13 (commit e737637→) |
| `paint_por_geometria.py` | Pintar zonas por criterio 3D (normales/altura/elipse), numpy vectorizado | pera, ventral, orejas |
| `elipsoide_apex.py` | Zona facial anclada al ápex del hocico (auto-adapta a geometría nueva) | pera del tan, re-anclada post-warp |
| `contorno_2d.py` | Extraer contorno/perfil de silueta desde una imagen 2D (fg mask + cumsum) | contorno melena, warp tables |
| `warp_perfil.py` | Re-proporcionar el cuerpo entero contra un perfil 2D (remapeo por masa + curva de anchos) | cirugía proporciones 2026-07-13 |
| `ribbon_tinta.py` | Línea de tinta paramétrica que cabalga el relieve (raycast + strip grosor constante) | sonrisa v3 (curva + comisuras) |
| `nails_asentados.py` | Cuñas de queratina asentadas en puntas (uñas/garras), material mate | uñas de pies (close-up verificado) |
| `bvh_glue.py` | Conformar/pegar un objeto a la superficie con offset proud por normal | mouth_lip re-glue |
| `pose_swing.py` | Rotar un hueso en eje de MUNDO alrededor de su cabeza (pose, reversible) | brazos A-pose (IoU 0.651→0.760) |
| `preflight_destructivo.py` | Chequeo ANTES de Solidify/Boolean/Remesh/moves masivos: open edges, non-manifold, min-edge (grosor máximo seguro) | melena_v5 post-mortem 2026-07-16 (460 open edges = la explosión era previsible) |
| `corporeo_glance.py` | GLANCE cadencia-1 (~2-4s): probes numéricos + render offscreen real (`render.opengl view_context=False`, cámara temp) + ledger `glance.jsonl` | purga oso muerto 2026-07-16 (probes); render path validado vs el hoyo del screenshot |

## Anti-recetas (métodos PROBADOS como callejón — no reintentar)
- Uñas/rasgos nítidos por vertex-paint (28 verts pintables → 0.001; geometría siempre).
- Melena por blades individuales (palitos) o esferas+voxel (almohadón) — superficie+contorno 2D.
- Escalados por bandas secuenciales contra métrica normalizada (3 pases fallidos) — warp de perfil.
- Solidify para "engrosar" un ribbon conformado (lo entierra) — reconstruir paramétrico.
- Ficha/valores desde el doc sin samplear la malla (los 1183 sellos).
- `get_viewport_screenshot` como evidencia de veredicto (captura cruda de pantalla: negro con Local View/sin foco; jamás mide nada) — glance/step siempre.
- Solidify Simple sobre lámina con bordes abiertos/normales irregulares (explosión en cuchillas, Blender #110057) — correr `preflight_destructivo` primero; si hay open edges: modo COMPLEX, Clamp, o join+voxel_remesh.
