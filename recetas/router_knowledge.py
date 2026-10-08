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
#     size_ranges          [{"aliases": [...], "height_m": (lo, hi), "source": ptr}]

# Techniques ruled out for EVERYTHING, whatever family matched.
UNIVERSAL_DISCARDED = {
    "viewport_screenshot_evidence": (
        "get_viewport_screenshot is a raw screen grab (black with Local View or "
        "without focus) and measures nothing: never verdict evidence",
        "recetas/RECETAS.md:40|get_viewport_screenshot"),
    "single_view_judgement": (
        "judging or presenting from one overview render hides the defects that "
        "only show from behind, above or below (eyeball through the eyelid, "
        "broken scalp edge, phantom brow on the nape)",
        "memory:feedback_orbitar_siempre_antes_de_reportar.md:11-28|orbitar la zona"),
    "vertex_paint_for_sharp_features": (
        "nails and sharp features by vertex paint reach 28 paintable verts -> "
        "0.001; geometry, always",
        "recetas/RECETAS.md:35|vertex-paint"),
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
            "blade_sticks_mane": "recetas/RECETAS.md:36|Melena por blades",
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
        "lessons": ["LECCIONES.md#9", "LECCIONES.md#14"],
        "sources": ["LECCIONES.md:124-133|ground truth", "LECCIONES.md:208-240|No medido"],
    },
    # ------------------------------------------------------------- mamifero
    "mamifero": {
        "aliases": ["mamifero", "mammal", "cuadrupedo", "quadruped",
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
            {"aliases": ["lobo", "wolf"], "height_m": (0.66, 0.84),
             "source": "game:wolf/_synthesis.md:14|Alzada"},
        ],
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
        "lessons": ["LECCIONES.md#1", "LECCIONES.md#2"],
        "sources": [
            "TECNICAS.md:10-21|distancia al foco",
            "TECNICAS.md:61-73|scatter_biome",
            "recetas/biome_facet.py:1-18|planar-decomposition",
            "recetas/use_size.py:13-17|tree_pack",
        ],
    },
}
