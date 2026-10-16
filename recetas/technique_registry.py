# technique_registry.py -- technique id -> the motor code that implements it.
#
# Used by (1) tools/start_asset.py to refuse an unknown technique, (2) the
# PreToolUse gate (~/.claude/hooks/motor-modeling-gate.py) to prove, by AST,
# that a generator really imports AND calls that implementation, (3)
# tools/verify_asset.py to know which stamp to expect.
#
# RULES
#   * Register ONLY a technique whose implementation exists in recetas/ AND
#     whose recipe stamps its output (motor_stamp). Do not invent mappings.
#   * A technique not listed here must be declared `custom` in the manifest
#     with a written reason; the post-run verifier still has to pass.
#   * stdlib only (the gate imports this inside a hook).

import ast
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# id -> module (relative to recetas/) + the public callables that count as use.
REGISTRY = {
    "engordar_anatomico": {
        "module": "engordar_anatomico", "calls": ("engordar", "engordar_np"),
        "note": "fat as a shape key over the rig (engordar_anatomico.py)"},
    "ribbon_tinta": {
        "module": "ribbon_tinta", "calls": ("build_ribbon",),
        "note": "ink ribbon riding the relief (ribbon_tinta.py)"},
    "bvh_glue": {
        "module": "bvh_glue", "calls": ("glue_to_surface",),
        "note": "conform an object to the skin with proud offset (bvh_glue.py)"},
    "paint_por_geometria": {
        "module": "paint_por_geometria", "calls": ("stamp",),
        "note": "vertex-colour zones by 3D criteria (paint_por_geometria.py)"},
}

# Recipes that exist in recetas/ but are NOT registered, with the reason.
# NOT_TESTED territory: declaring these needs `custom` until they stamp.
UNREGISTERED_RECIPES = {
    "warp_perfil": "pure numpy tables, touches no bpy object -> nothing to stamp",
    "elipsoide_apex": "pure numpy mask, touches no bpy object -> nothing to stamp",
    "contorno_2d": "pure cv2/numpy, no bpy object",
    "sample_base": "read-only sampler, builds nothing",
    "nails_asentados": "add_nail() writes into a caller's bmesh; no object to stamp",
    "pose_swing": "rotates a pose bone; no mesh object to stamp",
    "biome_stem/biome_mass/biome_facet/biome_vcol/biome_ao": "bmesh helpers; the object belongs to the caller",
    "material_swatch/mesh_quality/physics/gltf_check/rubric/views/use_size": "gates and probes, not construction techniques",
}

# Router-established techniques (router_knowledge `established`) with NO
# implementation in recetas/ -- the generator writes them from scratch today.
ROUTER_TECHNIQUES_WITHOUT_IMPLEMENTATION = {
    "pelo": "cards con alpha construidos desde los mechones",
    "quelonio": "carapacho desde sus escudos (_carapace.py is not in recetas/)",
    "material_procedural": "FLOAT_COLOR horneado (only guarded by motor-bytecolor-guard.py)",
    "export_godot": "truth render del GLB exportado (build_mob.py lives in the game repo)",
    "mamifero": "gramatica de cuadrupedo compartida (recetas/gato/build_gato.py is a generator, not a technique)",
    "prop": "silueta reconocible + componentes funcionales",
    "arquitectura": "dimensiones pinneadas a MANNEQUIN_H + kit-bash",
    "bioma": "capas de cobertura con Geometry Nodes Distribute/Instance",
    "construct": "nucleo + satelites presionados (gen_*.py in the game repo)",
    "blob": "icosphere + displace + FLOAT_COLOR",
    "artropodo": "cuerpo segmentado con alas en shape keys",
    "serpiente": "tubo barrido sobre espina en S + shape keys",
    "ave": "cuerpo fusiforme, pico de geometria real",
}


def is_registered(technique):
    return _key(technique) in REGISTRY


def _key(t):
    return (t or "").strip().lower().replace("-", "_").replace(" ", "_")


def _dotted(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def _norm_mod(name):
    return name[len("recetas."):] if name.startswith("recetas.") else name


def _bindings(tree):
    """local name -> normalized fully-qualified dotted target, from real
    import statements only (comments and strings are invisible to the AST)."""
    b, mods = {}, []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                full = _norm_mod(a.name)
                b[a.asname or a.name] = full
                mods.append(a.name)
        elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
            mods.append(n.module)
            base = _norm_mod(n.module)
            for a in n.names:
                if a.name == "*":
                    continue
                full = a.name if base == "recetas" else "%s.%s" % (base, a.name)
                b[a.asname or a.name] = full
    return b, mods


def _calls_of(tree, bindings):
    """Fully-qualified dotted names of everything called, resolved via imports."""
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            d = _dotted(n.func)
            if not d:
                continue
            head, _, tail = d.partition(".")
            if head in bindings:
                d = bindings[head] + ("." + tail if tail else "")
            out.add(_norm_mod(d))
    return out


def _parse(path):
    with open(path, encoding="utf-8") as fh:
        return ast.parse(fh.read(), filename=path)


def evidence(generator_path, technique):
    """(ok, detail): does `generator_path` -- following its local imports ONE
    level -- import AND call the motor implementation of `technique`?"""
    spec = REGISTRY.get(_key(technique))
    if spec is None:
        return False, "technique %r is not in the registry" % technique
    wanted = {"%s.%s" % (spec["module"], c) for c in spec["calls"]}
    try:
        tree = _parse(generator_path)
    except (OSError, SyntaxError, ValueError) as e:
        return False, "cannot parse generator %s (%s)" % (generator_path, e)
    seen = [generator_path]
    trees = [(generator_path, tree)]
    gdir = os.path.dirname(os.path.abspath(generator_path))
    _b, mods = _bindings(tree)
    for m in mods:
        top = _norm_mod(m).split(".")[0]
        cand = os.path.join(gdir, top + ".py")
        if top != spec["module"] and os.path.isfile(cand) and cand not in seen:
            try:
                trees.append((cand, _parse(cand)))
                seen.append(cand)
            except (OSError, SyntaxError, ValueError):
                pass
    for path, t in trees:
        b, _m = _bindings(t)
        hit = _calls_of(t, b) & wanted
        if hit:
            return True, "%s calls %s" % (os.path.basename(path), sorted(hit)[0])
    return False, ("no import+call of recetas.%s (%s) in %s%s"
                   % (spec["module"], "/".join(spec["calls"]),
                      os.path.basename(generator_path),
                      " or its local imports" if len(trees) > 1 else ""))
