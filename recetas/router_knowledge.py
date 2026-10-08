# router_knowledge.py -- the harvested knowledge the preflight router resolves.
#
# One entry per family. EVERY field is either copied from a cited source or
# marked as a declared gap: an entry nobody can trace is a constant nobody
# maintains (LECCIONES 8) and an invented rule is worse than a missing one.
# tools/test_gates.py checks that every `sources`/`discarded_sources` pointer
# resolves (file exists, line range inside the file, lesson id exists).
#
# SOURCE POINTER SYNTAX (checked by the fixtures)
#     "CREATION_PROTOCOL.md:151-172|anchor"   repo file, line or line range
#     "LECCIONES.md#6"                        lesson number
#     "game:wolf/_synthesis.md:26-35|anchor"  DungeonParty-A game/docs/art/_references/
#     "gameart:_asset_creation_contract.md:409|anchor"   DungeonParty-A game/docs/art/
#     "gametools:golem_guardian/build_golem_guardian.py:390-401|anchor"
#                                             DungeonParty-A game/tools/blender/
#     "memory:feedback_xxx.md:11-14|anchor"   ~/.claude/projects/-home-jouyan-proyectos/memory/
# Every line-range pointer ends in "|anchor": a short substring that MUST appear
# inside the cited lines. The fixtures check it, so a citation that drifts (rows
# inserted above it) fails loudly instead of pointing at the wrong paragraph.
#

# FIELDS
#     aliases              whole-word triggers (preflight_router matches them)
#     established          the technique that works
#     discarded            {technique_key: why}; require_technique raises on these
#     discarded_sources    {technique_key: pointer}  (one per discarded key)
#     structural_note      what the thing IS, ending in a number/orientation
#     must_read            documents to cite
#     mannequin_m          1.80, or None + mannequin_exempt (a reason)
#     required_views       labels from recetas/views.py VIEWS
#     use_size             {"sizes": [px...], "basis": str} or None + use_size_exempt
#     moving_parts         parts the generator must find in the structure spec
#     structure_spec       repo-relative dir holding a _structure_spec.md
#     lessons              ["LECCIONES.md#N", ...]
#     sources              pointers backing the entry as a whole
#     gaps                 research holes declared instead of papered over
#     size_ranges          [{"aliases": [...], "dim": "height"|"span", "range_m": (lo, hi),
#                            "source": ptr, "basis": str?, "weak": bool?}]   span = widest horizontal extent.
#                            weak=True: the citation mentions the size in passing, it is
#                            not an explicit measurement/spec -> the check only WARNS
#                            (never FAILs) and a gap is recorded until a real spec exists
#     glb_deliverable      pointer: the family's deliverable IS a .glb, so a run that
#                          exports none FAILS (otherwise it only records a gap)
#     creature             True for living/mob families (head-noun routing: a creature
#                          modifier before an object head makes the subject ambiguous)

# Techniques ruled out for EVERYTHING, whatever family matched.
UNIVERSAL_DISCARDED = {
    "viewport_screenshot_evidence": (
        "get_viewport_screenshot is a raw screen grab (black with Local View or "
        "without focus) and measures nothing: never verdict evidence",
        "recetas/RECETAS.md:44|get_viewport_screenshot"),
    "single_view_judgement": (
        "judging or presenting from one overview render hides the defects that "
        "only show from behind, above or below (eyeball through the eyelid, "
        "broken scalp edge, phantom brow on the nape)",
        "memory:feedback_orbitar_siempre_antes_de_reportar.md:11-28|orbitar la zona"),
    "vertex_paint_for_sharp_features": (
        "nails and sharp features by vertex paint reach 28 paintable verts -> "
        "0.001; geometry, always",
        "recetas/RECETAS.md:39|vertex-paint"),
}

# Mesh-gate limits (recetas/mesh_quality.py DEFAULT_LIMITS semantics). Every
# family inherits MESH_DEFAULT; a family's `mesh` dict overrides single keys and
# carries `source` (a pointer) or basis "initial, uncalibrated".
MESH_DEFAULT = {
    "max_nonmanifold": 0, "max_degenerate": 0, "max_inconsistent": 0,
    "needs_uv": False, "uv_overlap_max": 0.02, "max_tris": None,
    "basis": ("non-manifold and degenerate faces are hard errors that break "
              "export; the 0.02 UV-overlap share is initial, uncalibrated"),
    "source": "gametools:mesh_quality.py:164-167|hard errors",
}

# Physics-gate defaults (recetas/physics.py). `islands` / `interpenetration` are
# "fail" | "report" | "skip"; tilt/drift limits are INITIAL, uncalibrated.
# A family's `physics` dict overrides keys and must carry `reason` (+ `source`
# pointer when one exists) or basis "initial".
PHYSICS_DEFAULT = {
    "stands": True, "drop_test": True, "islands": "report",
    "interpenetration": "report", "max_tilt_deg": 15.0, "max_drift_m": 0.5,
    "ground_tol_m": 0.02, "drop_height_m": 0.05, "frames": 60,
    "basis": "initial, uncalibrated: limits are a first guess, not measured on "
             "real assets",
    "source": "CREATION_PROTOCOL.md:205|floating geometry",
}

_ALL_VIEWS = ["cenital", "tresq_alto", "perfil", "frente", "atras",
              "macro_placa", "bajo"]
_MOB_SIZES = {
    "sizes": [512, 256, 128],
    "basis": ("use_size.py:17-18: a character/mob is judged beside the 1.8 m "
              "post (that is the scale evidence); these strip sizes are a floor "
              "choice, NOT sourced from a measured on-screen size"),
}
_ENV_SIZES = {
    "sizes": [512, 256, 128],
    "basis": ("use_size.py:13-17: an environment prop is judged from a 1.65 m "
              "camera at walking distance (tree_pack shipped at bush scale for "
              "weeks); strip sizes are a floor choice, NOT sourced"),
}

CATEGORIES = {
    # ------------------------------------------------------------------ pelo
    "pelo": {
        "aliases": ["pelo", "hair", "cabello", "melena", "fur", "cabellera"],
        "established": "cards con alpha, construidos DESDE los mechones",
        "discarded": {
            "polygon_shells": (
                "una cascara offset del craneo es, geometricamente, un gorro. "
                "Ruled out in _asset_creation_contract.md §402 -- y la carpeta "
                "_references/hair_polygon_shells/ TODAVIA la recomienda, que es "
                "por lo que se construyo dos veces el 2026-08-22"),
            "offset_shell": "mismo defecto que polygon_shells",
            "blade_sticks_mane": (
                "melena por blades individuales (palitos) o esferas+voxel "
                "(almohadon): superficie + contorno 2D"),
        },
        "discarded_sources": {
            "polygon_shells": "gameart:_asset_creation_contract.md:409|hair_polygon_shells",
            "offset_shell": "gameart:_asset_creation_contract.md:409|hair_polygon_shells",
            "blade_sticks_mane": "recetas/RECETAS.md:40|Melena por blades",
        },
        "must_read": [
            "art/_modeling_knowledge_base.md §pelo en 3 capas",
            "art/_asset_creation_contract.md §402 (tecnicas DESCARTADAS)",
        ],
        "structural_note": (
            "el pelo crece de foliculos, cae por gravedad, se peina en una "
            "direccion y LOS MECHONES SE SOLAPAN: en una cabeza con pelo no se "
            "ve el cuero cabelludo salvo en la raya"),
        "mannequin_m": 1.80,
        "required_views": ["frente", "tresq_alto", "perfil", "atras",
                           "cenital", "bajo"],
        "use_size": _MOB_SIZES,
        "mesh": {"needs_uv": True, "source": "gametools:gen_hair_atlas.py:1-9|hair cards",
                 "basis": "hair cards sample a strand atlas, so they need UVs; overlap limit initial, uncalibrated"},
        "physics": {"stands": False, "drop_test": False, "islands": "skip", "interpenetration": "skip",
                    "reason": "hair is an attached part, not a freestanding body, and its cards overlap by design (the strands overlap is the technique)",
                    "source": "LECCIONES.md#6"},
        "lessons": ["LECCIONES.md#2", "LECCIONES.md#4", "LECCIONES.md#6"],
        "sources": [
            "LECCIONES.md:88-102|Pintar estructura",
            "LECCIONES.md:59-72|prosa correcta",
            "memory:feedback_modelar_es_modelado_full.md:28-35|Punto 0",
            "memory:feedback_orbitar_siempre_antes_de_reportar.md:11-28|orbitar la zona",
        ],
    },
    # -------------------------------------------------------------- quelonio
    "quelonio": {
        "creature": True,
        "aliases": ["tortuga", "turtle", "quelonio", "caparazon", "carapace"],
        "established": "carapacho construido DESDE sus escudos (_carapace.py)",
        "discarded": {
            "uv_sphere_painted": (
                "una esfera UV con escudos pintados encima tiene el edge flow "
                "de una esfera: los bordes de placa cortan poligonos por la "
                "mitad. LECCIONES.md leccion 6"),
            "trot_diagonal_pairs": (
                "pares diagonales moviendose juntos es un TROTE (perro, gato); "
                "ningun quelonio la usa: marcha lateral-sequence con apoyo "
                "tripode"),
            "shell_deforms": (
                "el caparazon es hueso: no deforma. El build heredaba la "
                "gramatica de shape keys del slime, cuyo cuerpo entero si "
                "deforma"),
        },
        "discarded_sources": {
            "uv_sphere_painted": "LECCIONES.md#6",
            "trot_diagonal_pairs":
                "game:turtle/motion/_motion_spec.md:38-44|TROTE",
            "shell_deforms": "game:turtle/motion/_motion_spec.md:28-30|Es hueso",
        },
        "must_read": [
            "~/motor-blender/LECCIONES.md leccion 5 (medida vs estructura)",
            "_references/turtle/motion/_motion_spec.md",
        ],
        "structural_note": (
            "postura ESPARRANCADA: humero en plano HORIZONTAL, antebrazo en "
            "plano VERTICAL, codo en L y FUERA del caparazon -- por eso las "
            "cuatro patas apuntan a cuadrantes distintos. El caparazon es "
            "hueso: no deforma. Marcha lateral-sequence, NO trote diagonal"),
        "moving_parts": ["humerus_L", "humerus_R", "forearm_L", "forearm_R",
                         "neck", "head", "tail"],
        "structure_spec": "recetas/specs/quelonio",
        "gaps": ["tail: game:turtle/_synthesis.md has no structural row for "
                 "it -- research it, then add the row to the spec"],
        "mannequin_m": 1.80,
        "required_views": list(_ALL_VIEWS),
        "use_size": _MOB_SIZES,
        "mesh": {"needs_uv": True, "source": "gametools:_carapace_texture.py:1-3|bake the carapace",
                 "basis": "the carapace albedo is baked to a texture; overlap limit initial, uncalibrated"},
        "physics": {"stands": True, "drop_test": True, "islands": "fail", "interpenetration": "report",
                    "reason": "the carapace is bone and does not deform, so a rigid drop is meaningful",
                    "source": "game:turtle/motion/_motion_spec.md:28|Es hueso"},
        "lessons": ["LECCIONES.md#2", "LECCIONES.md#5", "LECCIONES.md#6",
                    "LECCIONES.md#9", "LECCIONES.md#10", "LECCIONES.md#11"],
        "sources": [
            "game:turtle/_synthesis.md:195-242|UPPER_LIMB_PLANE",
            "game:turtle/motion/_motion_spec.md:28-44|TROTE",
            "CREATION_PROTOCOL.md:79-149|2c. The research",
        ],
    },
    # ---------------------------------------------------- material_procedural
    "material_procedural": {
        "aliases": ["material", "textura", "shader", "hormigon", "concrete",
                    "madera", "wood", "procedural"],
        "established": "FLOAT_COLOR horneado; nunca nodos de shader al exportar",
        "discarded": {
            "shader_nodes_export": (
                "los nodos de shader NO sobreviven glTF y el exportador escribe "
                "baseColorFactor blanco sin fallar: 6 criaturas blancas en Godot "
                "durante un mes. LECCIONES.md leccion 9"),
            "byte_color": (
                "BYTE_COLOR aplica una conversion sRGB asimetrica: los colores "
                "vuelven ~12x mas oscuros. Usar FLOAT_COLOR"),
            "plane_swatch": (
                "probar un material sobre PLANOS: un plano parado tiene una "
                "coordenada constante y una textura bandeada en ese eje "
                "renderiza lisa sin error. Cubos, nunca planos"),
            "stddev_as_texture_metric": (
                "sobre un cubo la desviacion estandar mide el sombreado entre "
                "caras, no la textura: un control uniforme daba 0.058 y el "
                "hormigon texturado 0.008. Usar la mediana de la diferencia "
                "entre pixeles vecinos"),
        },
        "discarded_sources": {
            "shader_nodes_export": "LECCIONES.md#9",
            "byte_color": "gametools:golem_guardian/build_golem_guardian.py:390-401|BYTE_COLOR",
            "plane_swatch": "LECCIONES.md#12",
            "stddev_as_texture_metric": "LECCIONES.md#12",
        },
        "must_read": [
            "~/motor-blender/recetas/material_swatch.py (gate de variacion)",
            "~/motor-blender/LECCIONES.md leccion 12",
        ],
        "structural_note": (
            "con coords Object la escala es CICLOS POR METRO, y una textura "
            "bandeada sobre un eje que la superficie no recorre renderiza lisa "
            "sin error"),
        "mannequin_m": None,
        "mannequin_exempt": ("a material is probed on swatch cubes "
                             "(material_swatch.py); human scale is judged "
                             "through the asset family it is applied to"),
        "required_views": ["cenital", "tresq_alto", "perfil", "bajo",
                           "macro_placa"],
        "use_size": None,
        "use_size_exempt": ("a material has no use size of its own; it is "
                            "judged at the size of the asset that carries it"),
        "physics": {"stands": False, "drop_test": False, "islands": "skip", "interpenetration": "skip",
                    "reason": "governs a material probed on swatch cubes, not a body",
                    "source": "recetas/material_swatch.py:1-50|CUBES"},
        "lessons": ["LECCIONES.md#3", "LECCIONES.md#9", "LECCIONES.md#12"],
        "sources": [
            "LECCIONES.md:158-186|control positivo",
            "recetas/material_swatch.py:1-50|CUBES",
        ],
    },
    # --------------------------------------------------------- export_godot
    "export_godot": {
        "aliases": ["glb", "gltf", "export", "godot", "exportar"],
        "established": "truth render del GLB exportado (build_mob.py)",
        "discarded": {
            "showcase_del_generador": (
                "el showcase renderiza CON el grafo de nodos que el .glb no "
                "lleva. Ningun asset se aprueba desde el render del generador"),
        },
        "discarded_sources": {"showcase_del_generador": "LECCIONES.md#9"},
        "must_read": [
            "art/_modeling_knowledge_base.md §gate de validacion pre-export",
        ],
        "structural_note": (
            "un gate debe testear una PROPIEDAD DEL ARTEFACTO, no la existencia "
            "de evidencia sobre el"),
        "mannequin_m": None,
        "mannequin_exempt": ("the export step governs the artefact, not a "
                             "family; scale is judged by the asset's own "
                             "family entry"),
        "required_views": list(_ALL_VIEWS),
        "use_size": None,
        "use_size_exempt": ("the export step has no use size of its own; the "
                            "asset family entry carries it"),
        "physics": {"stands": False, "drop_test": False, "islands": "skip", "interpenetration": "skip",
                    "reason": "governs the export step, not a family of bodies",
                    "source": "LECCIONES.md#9"},
        "glb_deliverable": "LECCIONES.md#9",
        "lessons": ["LECCIONES.md#9", "LECCIONES.md#14"],
        "sources": ["LECCIONES.md:124-133|ground truth", "LECCIONES.md:208-240|No medido"],
    },
    # ------------------------------------------------------------- mamifero
    "mamifero": {
        "creature": True,
        "aliases": ["mamifero", "mammal", "cuadrupedo", "quadruped", "roedor",
                    "rodent",
                    "gato", "gata", "cat", "felino", "feline",
                    "lobo", "wolf", "rata", "rat", "cabra", "goat",
                    "oveja", "sheep"],
        "established": ("UNA gramatica de cuadrupedo compartida y parametrizada "
                        "por especie (la hermana existente se extiende, no se "
                        "copia), construida desde una ficha de medidas reales"),
        "discarded": {
            "copy_paste_sibling": (
                "copiar la funcion de la especie hermana y retocar constantes "
                "(build_goat vs build_sheep): cada arreglo futuro hay que "
                "aplicarlo dos veces y las dos derivan"),
        },
        "discarded_sources": {
            "copy_paste_sibling": "CREATION_PROTOCOL.md:28-35|build_goat",
        },
        "must_read": [
            "CREATION_PROTOCOL.md §1 (categoria hermana) y §4 (funcion compartida)",
            "_references/wolf/_synthesis.md, _references/rat_rodent/_synthesis.md",
        ],
        "structural_note": (
            "caja toracica profunda que baja mucho (masa principal), lomo en "
            "DECLIVE de la cruz a la grupa, cuello musculado casi tan ancho "
            "como el craneo, patas largas (con patas cortas lee como otro "
            "animal); la rodilla trasera que apunta atras es el TOBILLO "
            "(digitigrado), la real va alta contra el cuerpo; la cola de la "
            "rata es MAS CORTA que cabeza+cuerpo"),
        "moving_parts": [],
        "structure_spec": None,
        "gaps": [
            "no feline (gato/cat) reference folder exists under _references/",
            "no quadruped has a per-part STRUCTURE table (plano/angulo/limite): "
            "wolf and rat_rodent carry measures only (LECCIONES 5, 11)",
        ],
        "mannequin_m": 1.80,
        "required_views": list(_ALL_VIEWS),
        "use_size": _MOB_SIZES,
        "size_ranges": [
            {"aliases": ["lobo", "wolf"], "dim": "height", "range_m": (0.66, 0.84),
             "source": "game:wolf/_synthesis.md:14|Alzada"},
            {"aliases": ["rata", "rat"], "dim": "span", "range_m": (0.255, 0.52),
             "source": "game:rat_rodent/_synthesis.md:8-16|Cabeza + cuerpo",
             "basis": "head+body 15-28 cm plus tail 10.5-24 cm, summed from the "
                      "two sourced ranges (nose-to-tail-tip length)"},
        ],
        "physics": {"stands": True, "drop_test": True, "islands": "fail", "interpenetration": "report",
                    "reason": "quadruped: low body on 4 legs, so it stands and must not have floating parts",
                    "source": "gameart:_bestiary_visual_bible.md:97|Cuadr"},
        "lessons": ["LECCIONES.md#4", "LECCIONES.md#5", "LECCIONES.md#11"],
        "sources": [
            "game:wolf/_synthesis.md:10-35|Medidas reales",
            "game:rat_rodent/_synthesis.md:6-24|Medidas reales",
            "CREATION_PROTOCOL.md:22-35|real-world object category",
            "CREATION_PROTOCOL.md:174-196|shared function",
            "TECNICAS.md:136-145|gait_brokenness",
        ],
    },
    # ----------------------------------------------------------------- prop
    "prop": {
        "aliases": ["prop", "utileria", "gate", "porton", "coop", "gallinero",
                    "cart", "carro", "carreta", "campfire", "fogata",
                    "firewood", "lena", "hanging line", "tendedero"],
        "established": ("silueta reconocible del objeto real (no una primitiva "
                        "generica); componentes funcionales dimensionados por "
                        "lo que cargan; material segun la economia de quien lo "
                        "posee; tamano segun lo que contiene"),
        "discarded": {
            "generic_primitive_stand_in": (
                "un cubo/cilindro de relleno en vez de la silueta real del "
                "objeto: el principio 'dar a los placeholders una silueta "
                "real' tuvo cero regresiones confirmadas en 4 sistemas"),
            "midpoint_clearance_check": (
                "validar una holgura contra el PUNTO MEDIO de un parametro "
                "aleatorio en vez de su peor caso (hangline_path_conflict)"),
            "copy_paste_sibling": (
                "copiar la funcion de una categoria hermana en vez de "
                "parametrizar la compartida"),
        },
        "discarded_sources": {
            "generic_primitive_stand_in": "CREATION_PROTOCOL.md:46-52|recognizable silhouette",
            "midpoint_clearance_check": "CREATION_PROTOCOL.md:65-72|hangline_path_conflict",
            "copy_paste_sibling": "CREATION_PROTOCOL.md:28-35|build_goat",
        },
        "must_read": [
            "CREATION_PROTOCOL.md §2b (logica funcional) y §3 (contra 1.80 m)",
        ],
        "structural_note": (
            "se mide contra el maniqui de 1.80 m ANTES de construir: un carro "
            "para ese personaje mide mas de 2 m (2-2.5 m), las puertas lo "
            "dejan pasar, ninguna viga a la altura del cuello"),
        "moving_parts": [],
        "structure_spec": None,
        "mannequin_m": 1.80,
        "required_views": list(_ALL_VIEWS),
        "use_size": _ENV_SIZES,
        "physics": {"stands": True, "drop_test": True, "islands": "fail", "interpenetration": "report",
                    "basis": "initial, uncalibrated: props rest on the ground; no family-specific source"},
        "lessons": ["LECCIONES.md#7", "LECCIONES.md#8"],
        "sources": [
            "CREATION_PROTOCOL.md:54-78|Functional/logical",
            "CREATION_PROTOCOL.md:151-172|1.80 m mannequin",
            "memory:feedback_proportion_rule_scale_ref.md:10-17|1.80",
        ],
    },
    # ---------------------------------------------------------- arquitectura
    "arquitectura": {
        "aliases": ["arquitectura", "architecture", "casa", "house", "puerta",
                    "door", "ventana", "window", "muralla", "palisade",
                    "empalizada", "torre", "tower", "aldea", "village",
                    "edificio", "building", "techo", "roof", "pared", "wall"],
        "established": ("dimensiones fijadas contra MANNEQUIN_H = 1.80 en UN "
                        "solo lugar y leidas de ahi por docstring y codigo; "
                        "funcion compartida parametrizada; modulo repetido "
                        "(kit-bash) con un prop hero que rompe la repeticion"),
        "discarded": {
            "copy_paste_sibling": (
                "copiar la funcion de otra categoria y retocar constantes: "
                "cada arreglo hay que aplicarlo dos veces"),
            "detail_what_will_be_covered": (
                "sobre-modelar lo que el follaje/otra capa va a tapar"),
            "unpinned_dimension": (
                "docstring y codigo que dicen numeros distintos (add_door "
                "[1.9,2.2] vs [1.90,1.98]): la medida nunca se fijo contra el "
                "maniqui en un solo lugar"),
        },
        "discarded_sources": {
            "copy_paste_sibling": "CREATION_PROTOCOL.md:28-35|build_goat",
            "detail_what_will_be_covered": "TECNICAS.md:46-47|no detallar",
            "unpinned_dimension": "CREATION_PROTOCOL.md:167-172|add_door",
        },
        "must_read": [
            "CREATION_PROTOCOL.md §3 (dimensiones contra 1.80 m) y §4",
            "TECNICAS.md §2 kitbash_modular",
        ],
        "structural_note": (
            "puertas, ventanas y escaleras se leen contra el maniqui de 1.80 m "
            "(nada a altura del cuello: 'wood at neck height', v7, hubo que "
            "arreglarlo en dos caminos de codigo); el material sigue la "
            "economia de quien es dueno y el tamano sigue lo que contiene"),
        "moving_parts": [],
        "structure_spec": None,
        "mannequin_m": 1.80,
        "required_views": list(_ALL_VIEWS),
        "use_size": _ENV_SIZES,
        "mesh": {"needs_uv": True, "source": "recetas/village_gen.py:905|USE_REAL_TEXTURES",
                 "basis": "village architecture uses real textures; overlap limit initial, uncalibrated"},
        "physics": {"stands": True, "drop_test": False, "islands": "report", "interpenetration": "report",
                    "basis": "initial, uncalibrated: buildings are fixed to the ground and never dropped; separate modules (walls, roof, stakes) are expected"},
        "lessons": ["LECCIONES.md#7", "LECCIONES.md#8"],
        "sources": [
            "CREATION_PROTOCOL.md:151-172|1.80 m mannequin",
            "CREATION_PROTOCOL.md:174-196|shared function",
            "TECNICAS.md:38-47|kitbash",
            "memory:feedback_proportion_rule_scale_ref.md:10-26|1.80",
        ],
    },
    # --------------------------------------------------------------- bioma
    "bioma": {
        "aliases": ["bioma", "biome", "terreno", "terrain", "vegetacion",
                    "vegetation", "bosque", "forest", "pradera", "prairie",
                    "hielo", "pasto", "grass", "flor", "flower", "roca",
                    "rock", "piedra", "stone", "arbol", "tree", "arbusto",
                    "bush", "scatter"],
        "established": ("capas de cobertura apiladas (pasto, plantas, "
                        "rocas/troncos, arboles hero), cada una con su regla "
                        "de densidad (pendiente, altitud, noise), con Geometry "
                        "Nodes vanilla: Distribute Points on Faces + Instance "
                        "on Points; rocas por CORTE de planos, no por ruido"),
        "discarded": {
            "noise_normal_displacement_rock": (
                "desplazar vertices a lo largo de la normal con Perlin da una "
                "superficie continuamente ondulada: puede hacer una papa mas "
                "irregular, nunca un plano. Las caras planas con aristas vivas "
                "salen de CORTAR un solido con planos"),
        },
        "discarded_sources": {
            "noise_normal_displacement_rock": "recetas/biome_facet.py:3-18|WHY THIS EXISTS",
        },
        "must_read": [
            "TECNICAS.md §4 scatter_biome",
            "recetas/biome_facet.py, recetas/biome_stem.py (D17: add_blade_strip "
            "y add_blade_card son recetas distintas, no copias)",
        ],
        "structural_note": (
            "cada elemento gasta segun su distancia al foco; con packs "
            "Kenney/Quaternius la ESTRUCTURA de densidad se logra, la "
            "fidelidad del realismo viral (Megascans) no"),
        "moving_parts": [],
        "structure_spec": None,
        "mannequin_m": 1.80,
        "required_views": list(_ALL_VIEWS),
        "use_size": _ENV_SIZES,
        "physics": {"stands": False, "drop_test": False, "islands": "skip", "interpenetration": "skip",
                    "basis": "initial, uncalibrated: terrain/vegetation are placed instances (scatter), not freestanding rigid bodies",
                    "source": "TECNICAS.md:61-73|scatter_biome"},
        "lessons": ["LECCIONES.md#1", "LECCIONES.md#2"],
        "sources": [
            "TECNICAS.md:10-21|distancia al foco",
            "TECNICAS.md:61-73|scatter_biome",
            "recetas/biome_facet.py:1-18|planar-decomposition",
            "recetas/use_size.py:13-17|tree_pack",
        ],
    },

    # -------------------------------------------------------------- construct
    "construct": {
        "creature": True,
        "aliases": ["golem", "constructo", "construct"],
        "established": ("bpy bespoke (gen_*.py), malla static con la pose en "
                        "Godot; cada masa corporal = NUCLEO grande + satelites "
                        "presionados (~40% embebidos) de tamano variado; cantos "
                        "redondeados tipo river-stone con erosion organica; el "
                        "musgo es propiedad de la malla completa desde el dormant"),
        "discarded": {
            "perfect_polyhedra_stones": (
                "hull facetado de aristas rectas largas: todas las piedras "
                "siguen leyendo como poliedros limpios; superficie = hull + "
                "erosion organica (subdiv + noise por normal)"),
            "sharp_noise_shard_rocks": (
                "el generador de rocas con noise displacement agresivo da "
                "lascas afiladas; las refs muestran cantos REDONDEADOS, nunca "
                "puntas, ni en estilo agresivo/cartoon"),
            "clean_stones_then_moss": (
                "rocas limpias que de repente tienen musgo al ensamblarse: el "
                "musgo/color es propiedad de la malla completa desde el dormant"),
            "shader_nodes_export": (
                "los nodos de shader no sobreviven glTF: baseColorFactor blanco "
                "sin fallar (mobs blancos en Godot); hornear a FLOAT_COLOR"),
        },
        "discarded_sources": {
            "perfect_polyhedra_stones":
                "game:golem/_synthesis.md:85-100|poliedros limpios",
            "sharp_noise_shard_rocks": "game:golem/_synthesis.md:58-63|lascas afiladas",
            "clean_stones_then_moss": "game:golem/_synthesis.md:64-67|no rocas limpias",
            "shader_nodes_export": "LECCIONES.md#9",
        },
        "must_read": [
            "_references/golem/_synthesis.md (+ golem_floating)",
            "_bestiary_visual_bible.md §6.5 (ficha del golem)",
        ],
        "structural_note": (
            "bottom-weighted y encorvado (base ancha, peso); DOS posturas: "
            "juggernaut erguido de brazos largos o knuckle-drag sobre nudillos; "
            "el diferenciador es un arbol/arbusto creciendo de cabeza o espalda; "
            "nucleo que brilla en el pecho; construct = angular, simetrico-ish, "
            "pesado, con un lado mas roto"),
        "moving_parts": [],
        "structure_spec": None,
        "gaps": ["no per-part STRUCTURE table (plano/angulo/limite) for the golem "
                 "limbs in _references/golem (LECCIONES 5)",
                 "golem scale '4,0 m' appears only in passing in two docs (wolf:24, "
                 "turtle:107): a weak source, so the height check only warns; "
                 "needs a real size spec in _references/golem"],
        "mannequin_m": 1.80,
        "required_views": list(_ALL_VIEWS),
        "use_size": _MOB_SIZES,
        "size_ranges": [
            {"aliases": ["golem", "constructo", "construct"], "dim": "height",
             "range_m": (3.2, 4.8),
             "source": "game:wolf/_synthesis.md:24|golem (4,0 m)",
             "weak": True,
             "basis": "WEAK source: wolf/_synthesis.md:24 and turtle/_synthesis.md:107 "
                      "mention 'golem (4,0 m)' only in passing as the example of a "
                      "deliberately raised scale; neither says it is the HEIGHT. "
                      "+-20% is an initial, uncalibrated tolerance"},
        ],
        "mesh": {"needs_uv": True, "source": "gametools:golem_guardian/build_golem_guardian.py:620|uv.new",
                 "basis": "the guardian builds UV layers for its normal-map textures; overlap limit initial, uncalibrated"},
        "physics": {"stands": True, "drop_test": True, "islands": "report", "interpenetration": "skip",
                    "reason": "bottom-weighted construct that stands; its stones are pressed ~40% embedded into the mass by design and a floating-segment variant exists",
                    "source": "game:golem/_synthesis.md:101-106|NUCLEO"},
        "glb_deliverable": "LECCIONES.md#9",
        "lessons": ["LECCIONES.md#2", "LECCIONES.md#9"],
        "sources": [
            "game:golem/_synthesis.md:20-23|bottom-weighted",
            "game:golem/_synthesis.md:101-106|NUCLEO",
            "gameart:_bestiary_visual_bible.md:100|Construct",
            "gameart:_bestiary_visual_bible.md:149|bpy bespoke",
            "game:wolf/_synthesis.md:24|golem (4,0 m)",
        ],
    },
    # ------------------------------------------------------------------ blob
    "blob": {
        "creature": True,
        "aliases": ["slime", "babosa", "limo", "gel", "blob", "amorfo"],
        "established": ("malla bpy (icosphere/UV sphere + displace) con color en "
                        "una capa FLOAT_COLOR horneada; el squash-stretch va en "
                        "shader/tween de Godot, no en la malla rigida; rasgos = "
                        "RELIEVE, no piezas"),
        "discarded": {
            "shader_nodes_gel": (
                "sombrear el gel con nodos procedurales (TexNoise/Voronoi/"
                "LayerWeight): glTF los descarta y el GLB llega como domo "
                "BLANCO sin tinte, mientras el showcase se ve verde"),
            "slime_teeth_nose_pupils": (
                "pupilas, dientes o nariz en el slime: nunca; el slime con "
                "dientes ya fue rechazado (rasgos = relieve)"),
        },
        "discarded_sources": {
            "shader_nodes_gel": "gametools:slime/build_slime.py:17-27|WHITE dome",
            "slime_teeth_nose_pupils":
                "game:slime_tensura/_synthesis.md:58-64|Nada de pupilas",
        },
        "must_read": ["_references/slime_tensura/_synthesis.md",
                      "_bestiary_visual_bible.md §3 y §6.6"],
        "structural_note": (
            "blob/amorfo: icosphere achatada sin extremidades, bottom-weighted; "
            "se individualiza por el color translucido que 'comio'; el boss "
            "(king) es la culminacion ecologica, sobresaturado, escala ~3-4x "
            "del slime comun"),
        "moving_parts": [],
        "structure_spec": None,
        "gaps": ["no absolute size source for the common slime (only ratios)",
                 "king scale: bible says ~3-4x the common slime "
                 "(_bestiary_visual_bible.md:299) but build_king_slime.py uses "
                 "S = 2.2 (line 18): the two disagree"],
        "mannequin_m": 1.80,
        "required_views": list(_ALL_VIEWS),
        "use_size": _MOB_SIZES,
        "mesh": {"max_tris": 11000, "source": "gametools:slime/build_slime.py:100|TRI_BUDGET",
                 "basis": "7600 common slime, 11000 king: the looser king budget is applied to the whole family"},
        "physics": {"stands": True, "drop_test": False, "islands": "fail", "interpenetration": "report",
                    "reason": "squash-and-stretch lives in a Godot shader/tween, so a rigid drop of the mesh says nothing",
                    "source": "gameart:_bestiary_visual_bible.md:150|jiggle"},
        "glb_deliverable": "LECCIONES.md#9",
        "lessons": ["LECCIONES.md#2", "LECCIONES.md#9"],
        "sources": [
            "gameart:_bestiary_visual_bible.md:96|Blob",
            "gameart:_bestiary_visual_bible.md:150|jiggle",
            "gameart:_bestiary_visual_bible.md:299|3-4x",
            "gametools:king_slime/build_king_slime.py:18|boss scale",
            "gametools:slime/build_slime.py:100|TRI_BUDGET",
        ],
    },
    # ------------------------------------------------------------- artropodo
    "artropodo": {
        "creature": True,
        "aliases": ["avispa", "wasp", "insecto", "insect", "artropodo",
                    "arthropod", "escorpion", "scorpion"],
        "established": ("cuerpo segmentado (3 segmentos) con alas en shape keys; "
                        "vuela flotando sobre el plano del suelo (hover), "
                        "individualizado por el arma-cola o las franjas de "
                        "alarma; color en FLOAT_COLOR"),
        "discarded": {
            "shader_nodes_export": (
                "los nodos de shader no sobreviven glTF: la avispa llego "
                "BLANCA a Godot (2 de 3 primitivas sin color)"),
        },
        "discarded_sources": {"shader_nodes_export": "LECCIONES.md#9"},
        "must_read": ["_bestiary_visual_bible.md §3 y §4",
                      "game/tools/blender/wasp/build_wasp.py"],
        "structural_note": (
            "artropodo: segmentado, patas multiples, el quiebre es el arma-cola "
            "o las pinzas; la avispa es artropodo VOLADOR de colonia/nido con "
            "franjas de alarma; 2 pares de alas"),
        "moving_parts": [],
        "structure_spec": None,
        "gaps": ["no _references folder for insects/arthropods",
                 "no real-world or game size for the wasp in the corpus",
                 "no per-part STRUCTURE table for legs/wings (LECCIONES 5, 11)"],
        "mannequin_m": 1.80,
        "required_views": list(_ALL_VIEWS),
        "use_size": _MOB_SIZES,
        "physics": {"stands": False, "drop_test": False, "islands": "fail", "interpenetration": "report",
                    "reason": "the wasp hovers: it floats above the origin ground plane by contract",
                    "source": "gametools:wasp/build_wasp.py:26|floats above"},
        "glb_deliverable": "LECCIONES.md#9",
        "lessons": ["LECCIONES.md#2", "LECCIONES.md#9"],
        "sources": [
            "gameart:_bestiary_visual_bible.md:99|Artr",
            "gameart:_bestiary_visual_bible.md:169|avispa",
            "gametools:wasp/build_wasp.py:1-3|3-segment insect body",
            "gametools:wasp/build_wasp.py:26|HOVER_Z",
        ],
    },
    # -------------------------------------------------------------- serpiente
    "serpiente": {
        "creature": True,
        "aliases": ["serpiente", "snake", "culebra", "vibora"],
        "established": ("reptil SIN extremidades definido por el MOVIMIENTO: "
                        "tubo barrido sobre una espina en S, cola fina, cabeza "
                        "en cuña del mismo tubo; ondulacion = dos shape keys "
                        "laterales en fase"),
        "discarded": {
            "shader_nodes_export": (
                "los nodos de shader no sobreviven glTF: la serpiente llego "
                "BLANCA a Godot (1 de 1 primitivas sin color)"),
        },
        "discarded_sources": {"shader_nodes_export": "LECCIONES.md#9"},
        "must_read": ["game/tools/blender/snake/build_snake.py",
                      "_bestiary_visual_bible.md §3 y §5"],
        "structural_note": (
            "sin patas ni malla de cabeza aparte: la cabeza es el mismo tubo, "
            "mas ancha y chata; se desliza con una onda S viajera "
            "(cos(t)*wave_a + sin(t)*wave_b); acento de veneno"),
        "moving_parts": [],
        "structure_spec": None,
        "gaps": ["no _references folder for snakes (no real-world size either)",
                 "no per-part STRUCTURE table (LECCIONES 5, 11)"],
        "mannequin_m": 1.80,
        "required_views": list(_ALL_VIEWS),
        "use_size": _MOB_SIZES,
        "physics": {"stands": True, "drop_test": True, "islands": "fail", "interpenetration": "report",
                    "basis": "initial, uncalibrated: a limbless body lying on the ground; no family-specific source"},
        "glb_deliverable": "LECCIONES.md#9",
        "lessons": ["LECCIONES.md#2", "LECCIONES.md#9", "LECCIONES.md#11"],
        "sources": [
            "gametools:snake/build_snake.py:1-8|limbless reptile",
            "gametools:snake/build_snake.py:11-14|slither",
            "gameart:_bestiary_visual_bible.md:148|serpiente",
            "gameart:_bestiary_visual_bible.md:166|acento veneno",
        ],
    },
    # ------------------------------------------------------------------- ave
    "ave": {
        "creature": True,
        "aliases": ["ave", "pajaro", "bird", "cuervo", "crow", "corvid",
                    "halcon", "hawk", "aguila", "eagle"],
        "established": ("cuerpo fusiforme con pecho, cabeza diferenciada y pico "
                        "de geometria real, alas anchas; volador: se mide por "
                        "ENVERGADURA contra el poste de 1.80 m, no por altura; "
                        "vuela flotando sobre el plano del suelo"),
        "discarded": {
            "hawk_falco_buteo_mix": (
                "mezclar halcon peregrino (falco) y aguilucho (buteo): son dos "
                "siluetas opuestas y mezclarlas da un pajaro sin lectura; hay "
                "que elegir uno"),
            "dove_sized_corvid": (
                "modelar el cuervo del tamano de una paloma: se pierde la "
                "presencia que justifica ponerlo (1.30 m de envergadura)"),
            "shader_nodes_export": (
                "los nodos de shader no sobreviven glTF: el pajaro llego "
                "BLANCO a Godot (2 de 5 primitivas sin color)"),
        },
        "discarded_sources": {
            "hawk_falco_buteo_mix": "game:hawk/_synthesis.md:15-17|Hay que elegir uno",
            "dove_sized_corvid": "game:corvid/_synthesis.md:14-16|paloma",
            "shader_nodes_export": "LECCIONES.md#9",
        },
        "must_read": ["_references/corvid/_synthesis.md",
                      "_references/hawk/_synthesis.md"],
        "structural_note": (
            "familia volador (silueta en el cielo): contraste por envergadura + "
            "cola; cuervo: pico grueso largo y curvo, alas largas y apuntadas; "
            "halcon/buteo: pico corto ganchudo, garras visibles en silueta; el "
            "volador alto sube la escala para verse a 10-14 m (anotarlo)"),
        "moving_parts": [],
        "structure_spec": None,
        "gaps": ["no per-part STRUCTURE table for wings/legs (LECCIONES 5, 11)"],
        "mannequin_m": 1.80,
        "required_views": list(_ALL_VIEWS),
        "use_size": _MOB_SIZES,
        "size_ranges": [
            {"aliases": ["cuervo", "crow", "corvid"], "dim": "span",
             "range_m": (1.15, 1.53),
             "source": "game:corvid/_synthesis.md:11|Envergadura"},
            {"aliases": ["halcon", "hawk", "aguila", "eagle"], "dim": "span",
             "range_m": (1.10, 1.22),
             "source": "game:hawk/_synthesis.md:11|Envergadura",
             "basis": "falco 1.10 m .. buteo 1.22 m, both sourced"},
        ],
        "physics": {"stands": False, "drop_test": False, "islands": "fail", "interpenetration": "report",
                    "reason": "the bird soars above the origin ground plane per brief, it does not stand",
                    "source": "gametools:bird_prey/build_bird.py:28|soars above"},
        "glb_deliverable": "LECCIONES.md#9",
        "lessons": ["LECCIONES.md#2", "LECCIONES.md#9"],
        "sources": [
            "game:corvid/_synthesis.md:10-16|Envergadura",
            "game:hawk/_synthesis.md:8-19|Envergadura",
            "gameart:_bestiary_visual_bible.md:98|Volador",
            "gametools:bird_prey/build_bird.py:1-3|bird of prey",
        ],
    },
}
