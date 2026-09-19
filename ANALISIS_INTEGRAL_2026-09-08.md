# Análisis Integral Motor-Blender + Dungeon Party (2026-09-08)

## RESUMEN EJECUTIVO — Estado real tras auditoría completa de ambos repos

---

## MOTOR-BLENDER (núcleo transversal)
✅ 26/26 fixtures adversariales pasan (verdict.py, asset_spec.py, preflight_router.py)
✅ Gates funcionando: veredicto 4 estados, estructura obligatoria, router por técnica con descartadas
⚠️ **ESCRITO PERO NO GATEADO** (ESTADO_ACTUAL.md:40-51):
  - Citar canon por archivo/sección (preflight punto 1) → sin verificación automática
  - 0b CON QUÉ TRUCO para familias sin entrada en router (router cubre 4: pelo/quelonio/material_procedural/export)
  - Rampa de variantes la elige Joan (punto 5) → sin gate que obligue ≥2 variantes
  - Vistas ingratas nuca/cenital (punto 6) → preview_object.py existe pero no obligatorio
  - require_structure()/require_technique() → probados en fixtures, NO cableados a generadores del juego

---

## DUNGEON PARTY — Estado mobpack Piso 1
**Fuente:** `_mob_pipeline.md` + `_mob_audit_2026-08-22.md`

### LISTOS REALES (motor maduro + Joan ≥7/10)
- tortuga (8/10)
- halcón (8/10)
- slime (≥7)

### REPASAR CON MOTOR
- king_slime — Joan: "no hemos trabajado en él" con motor maduro
- mimic — nunca pasó por el pipeline

### REHACER CON MOTOR (insignia)
- **golem** — pedido explícito Joan al nivel tortuga/halcón

### SOLO DEPLOY+CABLEAR (S)
- rata — bug luma BYTE_COLOR ~12x (luma media 0.287)
- avispa

### REBUILD M
- serpiente — UV+bake, 152 verts no sostienen escamas
- pájaro — ala blanca + escala córvido

### DECISIÓN PENDIENTE (L) — bespoke vs pack
- lobo, zorro, cabra, escorpión, bandidos

---

## BUGS CRÍTICOS DOCUMENTADOS
1. **Color loss**: shaders procedurales no exportan glTF → 4 mobs blancos en juego (serpiente, tortuga, avispa, ave)
2. **BYTE_COLOR vs FLOAT_COLOR**: rata luma media 0.287 (bug ~12x documentado)
3. **Export silencioso**: Base Color node graph descartado sin error, showcase renderiza CON grafo
4. **Espacios de coordenadas**: umbral mundo sobre coords locales (3 casos pagados)
5. **Medio-arreglo**: arreglar una instancia deja hermanas rotas (4 casos)

---

## PATRONES DE FALLO RECURRENTES (engram LECCIONES.md)
1. **Motor sabe más de lo que ejecuta** (2.5% auto-carga, 97.5% busca manual) — 4/4 PUSH ok, 5/5 PULL fallaron
2. **Valor correcto en datos e invisible en pantalla NO está hecho** (escudos tortuga, húmero horizontal, solapamiento pelo, 4 mobs blancos)
3. **Métricas ciegas** miden algo real que no es la pregunta (desv.std sobre cubos = sombreado caras, NO textura)
4. **Prosa correcta que nunca baja a geometría** ('patas palmeadas' → 4 conos iguales)
5. **Parámetros MEDIDA vs ESTRUCTURA** — estructura siempre se saltea
6. **Pintar estructura sobre superficie continua no da estructura** (cáscara offset = gorro)
7. **Arreglo a medias = bug** (ojos al rango, cejas/narinas fuera)
8. **Constante obsoleta en gate peor que no tener gate** (assert codo vs ancho caparazón viejo)
9. **Godot es ground truth; Blender no puede sustituirlo** (6 criaturas blancas 1 mes)
10. **Ojo del agente falla en DOS direcciones** (aprueba defectos + inventa defectos inexistentes)
14. **"No medido" no es "aprobado"** — y lo escrito no es lo gateado (preflight 4d decía estructura obligatoria, 0 specs estructurales)

---

## PIPELINE CANÓNICO (_mob_pipeline.md — 10 fases con gates)
| Fase | Qué | Gate |
|---|---|---|
| 0 | Ficha anatómica (MEDIDA + ESTRUCTURA por parte móvil) | SIN ESTRUCTURA NO SE MODELA |
| 1 | Motion spec (criterio éxito ANTES de construir) | Asserts medidos sobre samplers |
| 2 | Geometría DESDE anatomía | No pintar sobre superficie continua |
| 3 | Textura horneada DESDE funciones de forma | PROHIBIDO nodo mezcla Base Color |
| 4 | Gates en build (SystemExit) | Conteos, ratios, GAPs, coords MUNDO |
| 5 | Probe GLB post-export | COLOR_0, baseColorTexture, N clips |
| 6 | Deploy directo a assets/ + manifest | Gate paridad hook Stop |
| 7 | Juicio visual Joan | 7 vistas OBLIGATORIAS (incluye inferior) |
| 8 | Vida en juego | IA trayectoria + clip, inercia, checklist |
| 9 | Banco mob_lab EN VIVO con Joan | Feel movimiento + capturas orbitando |

---

## QUÉ TRABAJAR AHORA (orden impacto/costo)

| # | Acción | Impacto | Costo | Por qué |
|---|--------|---------|-------|---------|
| 1 | Cablear `require_structure()` y `require_technique()` a `build_slime.py` + `build_king_slime.py` + `build_golem.py` | ALTO | CORTO | Cierra el gap #14 (escrito ≠ gateado) |
| 2 | Hacer `preview_object.py` obligatorio en `build_mob.py` | ALTO | CORTO | Fuerza vistas ingratas (nuca, cenital) |
| 3 | Fix rata BYTE_COLOR → FLOAT_COLOR + verificar luma real | ALTO | MEDIO | Bug documentado ~12x, mob ya modelado |
| 4 | Deploy+cablear rata y avispa (copiar receta turtle/hawk) | ALTO | MEDIO | 2 mobs listos, solo falta deploy |
| 5 | King slime + mimic por pipeline completo | MEDIO | MEDIO | Repasar al estándar motor maduro |
| 6 | **Golem rebuild con motor maduro** | ALTO | LARGO | Pedido explícito Joan, insignia |
| 7 | Cosechar router para biomas/props/arquitectura | ESTRUCTURAL | MEDIO | 0b CON QUÉ TRUCO cobertura incompleta |
| 8 | Gate rampa variantes ≥2 + gate vistas ingratas | ESTRUCTURAL | MEDIO | Previene elegir un solo valor |

---

## PRÓXIMA RONDA REVISIÓN EXTERNA
**Bundle v3** con: ESTADO_ACTUAL.md actualizado + lecciones nuevas + cableados reales + métricas gates cableados
**Prompt idéntico** (PROMPT_REVISION_EXTERNA.md) a 4 modelos → síntesis comparativa
**Repo público:** https://github.com/Jouyancito/motor-blender

---

## ARCHIVOS CLAVE PARA LA PRÓXIMA SESIÓN
- `/mnt/c/Users/the_j/motor-blender/ESTADO_ACTUAL.md` — qué está gateado hoy y qué está solo escrito
- `/mnt/c/Users/the_j/motor-blender/LECCIONES.md` — 14 lecciones con casos reales
- `/mnt/c/Users/the_j/motor-blender/CREATION_PROTOCOL.md` — protocolo 6 pasos antes de construir
- `/mnt/c/Users/the_j/motor-blender/recetas/RECETAS.md` — índice técnicas verificadas + anti-recetas
- `/mnt/c/Users/the_j/Desktop/Juego/DungeonParty-A/game/docs/art/_mob_pipeline.md` — pipeline 10 fases
- `/mnt/c/Users/the_j/Desktop/Juego/DungeonParty-A/game/docs/art/_mob_audit_2026-08-22.md` — auditoría dura con datos medidos
- `/mnt/c/Users/the_j/Desktop/Juego/DungeonParty-A/CLAUDE.md` — reglas duras, preflight 10 pts, índice canon

---

## COMANDOS ÚTILES
```bash
# Tests del motor
cd /mnt/c/Users/the_j/motor-blender && python3 tools/test_gates.py

# Build + check + truth render un mob
cd /mnt/c/Users/the_j/Desktop/Juego/DungeonParty-A && python game/tools/blender/build_mob.py slime

# Probe GLB post-export
python game/tools/blender/_glb_color_check.py game/tools/blender/slime/slime.glb
python game/tools/blender/_glb_truth_render.py -- --glb game/tools/blender/slime/slime.glb

# Deploy a assets/
python game/tools/blender/_deploy.py

# Engram search
cd /mnt/c/Users/the_j && ./AppData/Local/engram/bin/engram.exe search "palabras" --project motor-blender --limit 10
```