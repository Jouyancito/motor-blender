# preflight_router.py -- resolve WHICH rules apply from WHAT is being built.
#
# WHY THIS EXISTS (2026-09-02, external review)
#
# The motor already moved an index into layer 0 (CLAUDE.md's canon table). That
# closes one failure mode -- "I did not know it existed". It does not close the
# one that actually cost the hair pass:
#
#     The agent KNEW the recipe existed. It did not know it APPLIED.
#
# An index is addressed by document. This is addressed by SUBJECT. You say what
# you are about to build; it returns the rules, the established technique, and
# the techniques already ruled out -- without anyone having to remember which
# file holds them.
#
# And it is a gate, not a reminder: declare the technique you intend to use and
# a discarded one raises SystemExit. The 2026-08-22 failure was building two
# hair techniques the contract listed as discarded, twice in one session, with
# the contract sitting in the repo. A printed warning would have been read the
# same way the contract was: not at all.
#
# USAGE
#     from recetas.preflight_router import route, require_technique
#
#     rules = route("voy a modelar el pelo del guerrero")
#     print(rules.render())
#
#     require_technique("pelo", "polygon_shells")   # -> SystemExit
#     require_technique("pelo", "cards_alpha")      # -> ok
#     require_technique("astrolabio", "x")          # -> SystemExit: unknown subject
#     require_technique("astrolabio", "x", allow_unknown=True,
#                       reason="instrumento unico")  # -> ok, said out loud
#
# EXTENDING IT
# One entry per category, harvested from a real failure. Do not add speculative
# entries: an unverified rule here is a constant nobody maintains, which is
# lesson 8. Every `discarded` value must cite where the ruling lives.

import os
import re

from recetas.verdict import Report, PASS, NOT_TESTED

# Category knowledge. `discarded` maps technique key -> why + where it is ruled.
CATEGORIES = {
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
        },
        "must_read": [
            "art/_modeling_knowledge_base.md §pelo en 3 capas",
            "art/_asset_creation_contract.md §402 (tecnicas DESCARTADAS)",
        ],
        "structural_note": (
            "el pelo crece de foliculos, cae por gravedad, se peina en una "
            "direccion y LOS MECHONES SE SOLAPAN: en una cabeza con pelo no se "
            "ve el cuero cabelludo salvo en la raya"),
    },
    "quelonio": {
        "aliases": ["tortuga", "turtle", "quelonio", "caparazon", "carapace"],
        "established": "carapacho construido DESDE sus escudos (_carapace.py)",
        "discarded": {
            "uv_sphere_painted": (
                "una esfera UV con escudos pintados encima tiene el edge flow "
                "de una esfera: los bordes de placa cortan poligonos por la "
                "mitad. LECCIONES.md leccion 6"),
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
    },
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
        },
        "must_read": [
            "~/motor-blender/recetas/material_swatch.py (gate de variacion)",
            "~/motor-blender/LECCIONES.md leccion 12",
        ],
        "structural_note": (
            "con coords Object la escala es CICLOS POR METRO, y una textura "
            "bandeada sobre un eje que la superficie no recorre renderiza lisa "
            "sin error"),
    },
    "export_godot": {
        "aliases": ["glb", "gltf", "export", "godot", "exportar"],
        "established": "truth render del GLB exportado (build_mob.py)",
        "discarded": {
            "showcase_del_generador": (
                "el showcase renderiza CON el grafo de nodos que el .glb no "
                "lleva. Ningun asset se aprueba desde el render del generador"),
        },
        "must_read": [
            "art/_modeling_knowledge_base.md §gate de validacion pre-export",
        ],
        "structural_note": (
            "un gate debe testear una PROPIEDAD DEL ARTEFACTO, no la existencia "
            "de evidencia sobre el"),
    },
}


class Rules:
    """What applies to one subject, resolved by keyword."""

    def __init__(self, subject, category, data):
        self.subject = subject
        self.category = category
        self.data = data or {}

    @property
    def matched(self):
        return self.category is not None

    def render(self):
        if not self.matched:
            return (
                "\n  PREFLIGHT ROUTER -- sin categoria para %r\n"
                "  Categorias conocidas: %s\n"
                "  Que no haya entrada NO significa que no haya reglas: significa\n"
                "  que nadie las cosecho todavia. Cargá el indice de CLAUDE.md a\n"
                "  mano, y si esta sesion descubre una regla, agregala acá.\n"
                % (self.subject, ", ".join(sorted(CATEGORIES))))

        d = self.data
        out = ["", "  PREFLIGHT ROUTER -- %s  (categoria: %s)"
               % (self.subject, self.category), "  " + "-" * 66]
        out.append("  QUE ES (0):   %s" % d.get("structural_note", "-"))
        out.append("  TECNICA (0b): %s" % d.get("established", "-"))
        if d.get("discarded"):
            out.append("  DESCARTADAS:")
            for key, why in d["discarded"].items():
                out.append("    x %s" % key)
                out.append("      %s" % why)
        if d.get("must_read"):
            out.append("  CITAR (1):")
            for doc in d["must_read"]:
                out.append("    - %s" % doc)
        if d.get("moving_parts"):
            out.append("  PARTES MOVILES (4d): %s" % ", ".join(d["moving_parts"]))
        return "\n".join(out) + "\n"

    def to_report(self):
        """Router coverage as a Report, so an unknown subject reads NOT_TESTED."""
        r = Report("ROUTER %s" % self.subject)
        if self.matched:
            r.add("categoria_resuelta", PASS, self.category)
        else:
            r.add("categoria_resuelta", NOT_TESTED,
                  "sin entrada; las reglas de esta familia no estan cosechadas")
        return r


_FOLD = str.maketrans("áéíóúÁÉÍÓÚñÑ", "aeiouAEIOUnN")


def _norm(text):
    return (text or "").translate(_FOLD).lower()


def _alias_pattern(alias):
    """Whole-word match, plural-tolerant. A bare substring test made
    'woodpecker' resolve to 'wood' (material_procedural) and 'furniture' to
    'fur' (pelo): wrong rules applied silently are worse than none. Underscore
    counts as a separator so slugs like 'wood_door' still match."""
    return re.compile(r"(?<![a-z0-9])%s(?:s|es)?(?![a-z0-9])"
                      % re.escape(_norm(alias)))


def route_all(text):
    """Every category whose alias appears in `text` as a whole word, in order
    of first appearance. [] when nothing matches."""
    low = _norm(text)
    hits = []
    for category, data in CATEGORIES.items():
        first = None
        for alias in data["aliases"]:
            m = _alias_pattern(alias).search(low)
            if m and (first is None or m.start() < first):
                first = m.start()
        if first is not None:
            hits.append((first, category))
    hits.sort()
    return [Rules(text, c, CATEGORIES[c]) for _pos, c in hits]


def route(text):
    """Resolve a free-text description to its (first) category rules."""
    rules = route_all(text)
    return rules[0] if rules else Rules(text, None, None)


def require_technique(subject, technique, verbose=True,
                      allow_unknown=False, reason=""):
    """
    Fail the build when the intended technique is one already ruled out, or when
    the subject has no registered knowledge at all.

    This is preflight 0b with teeth. A warning would be read exactly as well as
    the contract was on 2026-08-22, which is to say not at all.

    FAIL CLOSED ON UNKNOWN. This used to return silently for a subject with no
    category, so a family nobody harvested passed the gate it was meant to face:
    the absence of a rule read as the absence of a problem. Now an unknown
    subject raises unless the caller states `allow_unknown=True` AND a `reason`
    -- the same contract as verdict.NOT_APPLICABLE.
    """
    matches = route_all(subject)
    if verbose:
        if matches:
            for rules in matches:
                print(rules.render())
        else:
            print(Rules(subject, None, None).render())

    if not matches:
        if not allow_unknown:
            raise SystemExit(
                "\nSIN CONOCIMIENTO REGISTRADO para %r: no knowledge registered "
                "for it.\nAdd a router entry (recetas/preflight_router.py, every "
                "field cited to its source) or pass allow_unknown=True with a "
                "reason.\nCategorias conocidas: %s\n"
                % (subject, ", ".join(sorted(CATEGORIES))))
        if not (reason or "").strip():
            raise SystemExit(
                "\nallow_unknown=True needs a reason (why is it safe to build %r "
                "with no registered rules?). An unreasoned exemption is an "
                "unchecked gate wearing a costume.\n" % subject)
        print("  PREFLIGHT ROUTER -- %r allowed UNKNOWN: %s" % (subject, reason))
        return Rules(subject, None, None)

    key = (technique or "").strip().lower().replace("-", "_").replace(" ", "_")
    for rules in matches:
        why = rules.data.get("discarded", {}).get(key)
        if why:
            raise SystemExit(
                "\nTECNICA DESCARTADA: %r para %r (categoria %s)\n\n  %s\n\n"
                "La tecnica establecida de la familia es: %s\n"
                % (technique, subject, rules.category, why,
                   rules.data.get("established", "(sin registrar)")))
    return matches[0]
