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

# Category knowledge lives in recetas/router_knowledge.py (one entry per family,
# every field cited to its source). Re-exported here so `preflight_router.CATEGORIES`
# keeps working.
from recetas.router_knowledge import CATEGORIES, UNIVERSAL_DISCARDED  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
        if d.get("mannequin_m"):
            out.append("  ESCALA (3):   maniqui de %.2f m en la escena, renders con el"
                       % d["mannequin_m"])
        elif d.get("mannequin_exempt"):
            out.append("  ESCALA (3):   n/a -- %s" % d["mannequin_exempt"])
        if d.get("required_views"):
            out.append("  VISTAS (5):   %s" % ", ".join(d["required_views"]))
        for gap in d.get("gaps", []):
            out.append("  HUECO:        %s" % gap)
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

    key = (technique or "").strip().lower().replace("-", "_").replace(" ", "_")
    if key in UNIVERSAL_DISCARDED:
        why, src = UNIVERSAL_DISCARDED[key]
        raise SystemExit("\nTECNICA DESCARTADA (universal): %r\n\n  %s  [%s]\n"
                         % (technique, why, src))

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

    for rules in matches:
        why = rules.data.get("discarded", {}).get(key)
        if why:
            raise SystemExit(
                "\nTECNICA DESCARTADA: %r para %r (categoria %s)\n\n  %s\n\n"
                "La tecnica establecida de la familia es: %s\n"
                % (technique, subject, rules.category, why,
                   rules.data.get("established", "(sin registrar)")))
    return matches[0]


def requirements(subject, rules=None):
    """
    Merge what every matched family demands into ONE dict for motor_run:

        mannequin          True, or False with `mannequin_exempt` reasons
        views              ordered union of required view labels
        use_size           {"sizes": [...]} union, or None with `use_size_exempt`
        structure          [(abs_ref_dir, [parts])] one per family with a spec
        declared_parts     parts families declare but have no spec dir for
        gaps               declared research holes of every matched family
        height_range       sourced (lo, hi) for the asset, or None
        lessons            lesson pointers of every matched family
    """
    rules = rules if rules is not None else route_all(subject)
    low = _norm(subject)
    req = {"categories": [r.category for r in rules], "mannequin": False,
           "mannequin_exempt": [], "views": [], "use_size": None,
           "use_size_exempt": [], "structure": [], "declared_parts": [],
           "gaps": [], "height_range": None, "lessons": []}
    sizes = set()
    for r in rules:
        d = r.data
        if d.get("mannequin_m"):
            req["mannequin"] = True
        elif d.get("mannequin_exempt"):
            req["mannequin_exempt"].append("%s: %s" % (r.category,
                                                       d["mannequin_exempt"]))
        for v in d.get("required_views", []):
            if v not in req["views"]:
                req["views"].append(v)
        if d.get("use_size"):
            sizes.update(d["use_size"]["sizes"])
        elif d.get("use_size_exempt"):
            req["use_size_exempt"].append("%s: %s" % (r.category,
                                                      d["use_size_exempt"]))
        if d.get("structure_spec") and d.get("moving_parts"):
            req["structure"].append((os.path.join(REPO, d["structure_spec"]),
                                     list(d["moving_parts"])))
        elif d.get("moving_parts"):
            req["declared_parts"].extend(d["moving_parts"])
        req["gaps"].extend("%s: %s" % (r.category, g) for g in d.get("gaps", []))
        req["lessons"].extend(d.get("lessons", []))
        for sr in d.get("size_ranges", []):
            if any(_alias_pattern(a).search(low) for a in sr["aliases"]):
                req["height_range"] = tuple(sr["height_m"])
    if sizes:
        req["use_size"] = {"sizes": sorted(sizes, reverse=True)}
    return req
