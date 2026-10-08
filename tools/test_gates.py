"""
test_gates.py -- adversarial fixtures for the motor's gates.

WHY THIS EXISTS (2026-09-02)

Four external reviewers converged on the same criticism of material_swatch.py:
it is calibrated against ONE harvest case, with no permanent suite of known-bad
inputs. And the motor's own history says why that matters -- that gate was
broken twice in the shape it exists to prevent (planes blind to a banded axis,
then stddev measuring face shading instead of texture), and its test reported a
false positive on top. Three layers, the same instrument error.

So every gate here is run against a case that MUST fail and a case that MUST
pass. A gate that has never been shown a known-bad input is decoration.

Run:
    python tools/test_gates.py        # no Blender needed for these three
"""

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from recetas.verdict import (Report, PASS, FAIL, NOT_TESTED,  # noqa: E402
                             NOT_APPLICABLE)
from recetas import asset_spec                                # noqa: E402
from recetas import preflight_router                          # noqa: E402
from recetas import material_swatch                           # noqa: E402
from recetas import scale_ref                                 # noqa: E402
from recetas import views                                     # noqa: E402

_results = []


def check(name, condition, detail=""):
    _results.append((name, bool(condition), detail))
    print("  %s  %s%s" % ("ok  " if condition else "FAIL", name,
                          (" -- " + detail) if detail and not condition else ""))


def expect_exit(name, fn, *args, **kwargs):
    """A gate that does not raise on a known-bad input has failed its job."""
    try:
        fn(*args, **kwargs)
    except SystemExit as exc:
        check(name, True)
        return str(exc)
    check(name, False, "no lanzo SystemExit con entrada mala conocida")
    return ""


def expect_no_exit(name, fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except SystemExit as exc:
        check(name, False, "falso positivo: %s" % str(exc)[:120])
        return
    check(name, True)


# ---------------------------------------------------------------------------
# verdict.py
# ---------------------------------------------------------------------------

def test_verdict():
    print("\nverdict.py")

    r = Report("x").add("a", PASS).add("b", NOT_TESTED, "no corrio")
    check("NOT_TESTED no cuenta como aprobado", r.verdict() == NOT_TESTED)
    check("un report con NOT_TESTED no esta completo", not r.is_complete())
    expect_exit("require_complete frena con NOT_TESTED", r.require_complete)

    r2 = Report("y").add("a", PASS).add("b", NOT_APPLICABLE,
                                        reason="el asset no tiene ropa")
    check("NOT_APPLICABLE con razon SI aprueba", r2.verdict() == PASS)
    expect_no_exit("require_complete pasa sin FAIL ni NOT_TESTED",
                   r2.require_complete)

    try:
        Report("z").add("a", NOT_APPLICABLE)
        check("NOT_APPLICABLE sin razon es rechazado", False,
              "acepto una exencion sin justificar")
    except ValueError:
        check("NOT_APPLICABLE sin razon es rechazado", True)

    r3 = Report("w").add("a", FAIL, "roto")
    check("FAIL domina el veredicto", r3.verdict() == FAIL)


# ---------------------------------------------------------------------------
# asset_spec.py
# ---------------------------------------------------------------------------

GOOD_SPEC = """# Tortuga

## STRUCTURE

| Parte | Plano | Angulo | Limite |
|---|---|---|---|
| humerus_L | horizontal | 0 deg vs suelo | queda FUERA del caparazon |
| forearm_L | vertical | 90 deg vs humero | no cruza la linea media |
| neck | sagital | 0-45 deg | se retrae dentro del caparazon |
"""

EMPTY_CELL_SPEC = """# Tortuga

## STRUCTURE

| Parte | Plano | Angulo | Limite |
|---|---|---|---|
| humerus_L | horizontal |  | queda fuera |
"""

NO_SECTION_SPEC = """# Tortuga

## MEASURE

| Parametro | Valor |
|---|---|
| carapace | 0.845 m |
"""


def _spec_dir(tmp, body):
    d = os.path.join(tmp, "ref")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "_structure_spec.md"), "w", encoding="utf-8") as fh:
        fh.write(body)
    return d


def test_asset_spec():
    print("\nasset_spec.py")
    with tempfile.TemporaryDirectory() as tmp:
        good = _spec_dir(tmp, GOOD_SPEC)

        expect_no_exit("spec completo pasa", asset_spec.require_structure,
                       good, ["humerus_L", "forearm_L", "neck"], verbose=False)

        # THE harvest case: the part exists in the build and not in the research.
        msg = expect_exit("parte movil sin renglon -> SystemExit",
                          asset_spec.require_structure, good,
                          ["humerus_L", "tail"], verbose=False)
        check("el error nombra la parte que falta", "tail" in msg)

        rep = asset_spec.check_structure(good, ["tail"])
        check("parte ausente se marca NOT_TESTED, no FAIL",
              rep.rows[0]["state"] == NOT_TESTED)

    with tempfile.TemporaryDirectory() as tmp:
        empty = _spec_dir(tmp, EMPTY_CELL_SPEC)
        rep = asset_spec.check_structure(empty, ["humerus_L"])
        check("celda vacia es FAIL (preguntado y sin responder)",
              rep.rows[0]["state"] == FAIL)

    with tempfile.TemporaryDirectory() as tmp:
        nosec = _spec_dir(tmp, NO_SECTION_SPEC)
        expect_exit("spec con MEASURE y sin STRUCTURE -> SystemExit",
                    asset_spec.require_structure, nosec, ["humerus_L"],
                    verbose=False)
        rep = asset_spec.check_structure(nosec, ["humerus_L"])
        check("solo-MEDIDA no aprueba (el caso tortuga)",
              rep.verdict() != PASS)

    # A directory with no spec at all must not read as "nothing to check".
    with tempfile.TemporaryDirectory() as tmp:
        expect_exit("carpeta sin spec -> SystemExit",
                    asset_spec.require_structure, tmp, ["humerus_L"],
                    verbose=False)


NESTED_SYNTHESIS = """# turtle synthesis

### ESTRUCTURA -- plano, angulo y limite por parte movil

#### Miembros

| Parametro | Valor | Fuente |
|---|---|---|
| UPPER_LIMB_PLANE | horizontal | JEB |

| Parte | Plano | Angulo | Limite |
|---|---|---|---|
| humerus_L | horizontal | 0 deg | fuera del caparazon |

### Otra seccion

| Parte | Plano | Angulo | Limite |
|---|---|---|---|
| leaked_part | x | x | x |
"""

MOTION_ONLY = """# motion

## Idle

| Parte | Plano | Angulo | Limite |
|---|---|---|---|
| humerus_L | horizontal | 0 | fuera |
"""


def test_asset_spec_corpus_shapes():
    """D7: the corpus keeps research in _synthesis.md, nested and 3-column."""
    print("\nasset_spec.py -- corpus shapes (REVIEW_FABLE D7)")
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "_synthesis.md"), "w", encoding="utf-8") as fh:
            fh.write(NESTED_SYNTHESIS)
        check("find_spec cae a un .md con encabezado ESTRUCTURA",
              asset_spec.find_spec(tmp) is not None)
        rep = asset_spec.check_structure(tmp, ["humerus_L"])
        check("tabla de 4 columnas bajo #### se lee", rep.verdict() == PASS)
        rep = asset_spec.check_structure(tmp, ["UPPER_LIMB_PLANE"])
        check("fila de 3 columnas (Parametro|Valor|Fuente) no es una parte",
              rep.rows[0]["state"] == NOT_TESTED)
        rep = asset_spec.check_structure(tmp, ["leaked_part"])
        check("la seccion termina en el siguiente encabezado del mismo nivel",
              rep.rows[0]["state"] == NOT_TESTED)

    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "motion"))
        with open(os.path.join(tmp, "motion", "_motion_spec.md"), "w",
                  encoding="utf-8") as fh:
            fh.write(MOTION_ONLY)
        check("un _motion_spec.md sin seccion STRUCTURE no cuenta como spec",
              asset_spec.find_spec(tmp) is None)
        expect_exit("carpeta con solo movimiento -> SystemExit",
                    asset_spec.require_structure, tmp, ["humerus_L"],
                    verbose=False)

    # The shipped quelonio spec: 6 researched parts pass; `tail` has no source
    # row and must read as NOT researched, not as invented.
    spec_dir = os.path.join(ROOT, "recetas", "specs", "quelonio")
    parts = ["humerus_L", "humerus_R", "forearm_L", "forearm_R", "neck", "head"]
    expect_no_exit("spec de tortuga del repo cubre sus 6 partes investigadas",
                   asset_spec.require_structure, spec_dir, parts, verbose=False)
    rep = asset_spec.check_structure(spec_dir, ["tail"])
    check("tail sin fuente -> NOT_TESTED (no se inventa)",
          rep.rows[0]["state"] == NOT_TESTED)


# ---------------------------------------------------------------------------
# material_swatch.py (pure part -- no Blender)
# ---------------------------------------------------------------------------

# Measured 2026-10-08, tools/measure_swatch_floor.py (see material_swatch.py).
_FLOOR = 0.00004          # CONTROL_flat
_SWING_1PCT = 0.00008     # +-1 % albedo: must read as flat
_SWING_3PCT = 0.00021     # +-3 % albedo: must read as textured


def _stats(detail):
    return {"m": {"mean": 0.3, "stddev": 0.01, "detail": detail}}


def test_material_swatch():
    print("\nmaterial_swatch.py -- threshold vs measured instrument floor")
    thr = material_swatch.MIN_DETAIL_DEFAULT
    check("el umbral esta por encima del piso del instrumento (control)",
          thr > _FLOOR * 2, "umbral %.5f piso %.5f" % (thr, _FLOOR))
    expect_exit("el control plano medido FALLA el gate",
                material_swatch.assert_materials_vary, _stats(_FLOOR))
    expect_exit("variacion de +-1 % de albedo FALLA (invisible)",
                material_swatch.assert_materials_vary, _stats(_SWING_1PCT))
    expect_no_exit("variacion de +-3 % de albedo PASA",
                   material_swatch.assert_materials_vary, _stats(_SWING_3PCT))
    expect_exit("a caballo del umbral, justo debajo, falla",
                material_swatch.assert_materials_vary, _stats(thr * 0.95))
    expect_no_exit("a caballo del umbral, justo encima, pasa",
                   material_swatch.assert_materials_vary, _stats(thr * 1.05))
    expect_exit("umbral en el piso del instrumento es rechazado",
                material_swatch.assert_materials_vary, _stats(_SWING_3PCT),
                min_detail=_FLOOR)
    expect_exit("exempt como lista es rechazado",
                material_swatch.assert_materials_vary, _stats(_FLOOR),
                exempt=["m"])
    expect_exit("exempt como string es rechazado",
                material_swatch.assert_materials_vary, _stats(_FLOOR),
                exempt="m")
    rep = material_swatch.assert_materials_vary(
        _stats(_FLOOR), exempt={"m": "vidrio pulido, uniforme a proposito"})
    check("exempt con razon queda NOT_APPLICABLE", rep.verdict() == PASS)


# ---------------------------------------------------------------------------
# scale_ref.py / views.py (pure parts -- no Blender)
# ---------------------------------------------------------------------------

def test_scale_ref_and_views():
    print("\nscale_ref.py / views.py")
    check("la geometria del maniqui suma 1.80 m",
          abs(scale_ref.HEAD_Z + scale_ref.HEAD_R - 1.80) < 1e-9
          and scale_ref.MANNEQUIN_H == 1.80)

    ok = lambda p: True            # noqa: E731
    big = lambda p: 100            # noqa: E731
    rep = scale_ref.scale_evidence_report(1.80, ["a.png"], exists=ok, size_of=big)
    check("maniqui 1.80 + renders -> sin FAIL ni NOT_TESTED duro",
          not rep.failed and rep.rows[0]["state"] == PASS
          and rep.rows[1]["state"] == PASS)
    rep = scale_ref.scale_evidence_report(None, ["a.png"], exists=ok, size_of=big)
    check("sin maniqui en la escena -> FAIL", rep.rows[0]["state"] == FAIL)
    rep = scale_ref.scale_evidence_report(1.20, ["a.png"], exists=ok, size_of=big)
    check("maniqui reescalado (1.20 m) -> FAIL", rep.rows[0]["state"] == FAIL)
    rep = scale_ref.scale_evidence_report(1.80, ["a.png"],
                                          exists=lambda p: False, size_of=big)
    check("render que no existe -> FAIL", rep.rows[1]["state"] == FAIL)
    rep = scale_ref.scale_evidence_report(1.80, ["a.png"], exists=ok,
                                          size_of=lambda p: 0)
    check("render vacio -> FAIL", rep.rows[1]["state"] == FAIL)
    rep = scale_ref.scale_evidence_report(1.80, [], exists=ok, size_of=big)
    check("sin lista de renders -> NOT_TESTED, no PASS",
          rep.rows[1]["state"] == NOT_TESTED)
    rep = scale_ref.scale_evidence_report(1.80, ["a.png"], asset_height=0.80,
                                          expected_height_m=(0.66, 0.84),
                                          exists=ok, size_of=big)
    check("altura del asset dentro del rango CON fuente -> PASS",
          rep.rows[2]["state"] == PASS)
    rep = scale_ref.scale_evidence_report(1.80, ["a.png"], asset_height=1.30,
                                          expected_height_m=(0.66, 0.84),
                                          exists=ok, size_of=big)
    check("altura del asset fuera del rango -> FAIL",
          rep.rows[2]["state"] == FAIL)
    rep = scale_ref.scale_evidence_report(1.80, ["a.png"], asset_height=1.30,
                                          exists=ok, size_of=big)
    check("sin rango con fuente la altura queda NOT_TESTED (no se inventa)",
          rep.rows[2]["state"] == NOT_TESTED)

    # No copy of the mannequin may come back into the generators.
    for gen in ("village_gen.py", "clown_gen.py"):
        with open(os.path.join(ROOT, "recetas", gen), encoding="utf-8") as fh:
            src = fh.read()
        check("%s no vuelve a copiar el maniqui" % gen,
              "ref_human_body" not in src and "scale_ref.build_mannequin" in src)

    # views: the guard, with positive controls.
    expect_no_exit("el set canonico pasa require_views", views.require_views,
                   views.VIEWS)
    no_bajo = [v for v in views.VIEWS if v[0] != "bajo"]
    msg = expect_exit("un set sin 'bajo' -> SystemExit", views.require_views,
                      no_bajo)
    check("el error nombra el angulo perdido", "bajo" in msg)
    no_perfil = [v for v in views.VIEWS if v[0] != "perfil"]
    expect_exit("un set sin 'perfil' -> SystemExit", views.require_views,
                no_perfil)
    only_front = [v for v in views.VIEWS if v[0] in ("frente", "perfil", "bajo")]
    expect_exit("un set sin vista cenital/alta -> SystemExit",
                views.require_views, only_front)
    expect_exit("etiqueta de vista desconocida -> SystemExit",
                views.resolve_views, ["frente", "inventada"])
    check("resolve_views devuelve las tuplas pedidas",
          [v[0] for v in views.resolve_views(
              ["cenital", "tresq_alto", "perfil", "bajo"])]
          == ["cenital", "tresq_alto", "perfil", "bajo"])


# ---------------------------------------------------------------------------
# router_knowledge.py -- every entry complete, every citation resolvable
# ---------------------------------------------------------------------------

import re                                                    # noqa: E402
from recetas import router_knowledge                         # noqa: E402

GAME_REFS = os.path.expanduser(
    "~/proyectos/Juego/DungeonParty-A/game/docs/art/_references")
GAME_TOOLS = os.path.expanduser(
    "~/proyectos/Juego/DungeonParty-A/game/tools/blender")
MEMORY = os.path.expanduser(
    "~/.claude/projects/-home-jouyan-proyectos/memory")
_PTR = re.compile(r"^(?:(game|gametools|memory|game-doc):)?([^:#]+)"
                  r"(?::(\d+)(?:-(\d+))?|#(\d+))?$")


def resolve_pointer(ptr):
    """
    Returns (state, detail): "ok" | "bad" | "unchecked" (base dir absent or a
    doc outside this machine's reach -- reported, never silently counted as ok).
    """
    m = _PTR.match(ptr)
    if not m:
        return "bad", "unparseable pointer %r" % ptr
    kind, rel, a, b, lesson = m.groups()
    base = {None: ROOT, "game": GAME_REFS, "gametools": GAME_TOOLS,
            "memory": MEMORY}.get(kind)
    if kind == "game-doc":
        return "unchecked", "outside reach: %s" % ptr
    if not os.path.isdir(base):
        return "unchecked", "base dir missing for %r" % ptr
    path = os.path.join(base, rel)
    if not os.path.isfile(path):
        return "bad", "no such file %s" % path
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    if lesson:
        if any(l.startswith("## %s. " % lesson) for l in lines):
            return "ok", ""
        return "bad", "%s has no lesson %s" % (rel, lesson)
    if a:
        lo, hi = int(a), int(b or a)
        if 1 <= lo <= hi <= len(lines):
            return "ok", ""
        return "bad", "%s:%d-%d outside the file (%d lines)" % (
            rel, lo, hi, len(lines))
    return "ok", ""


def test_router_knowledge():
    print("\nrouter_knowledge.py -- completeness and citations")

    # Positive/negative controls for the pointer checker itself: a checker that
    # cannot say "bad" would make every pointer below meaningless.
    check("control: puntero bueno resuelve",
          resolve_pointer("LECCIONES.md#6")[0] == "ok"
          and resolve_pointer("CREATION_PROTOCOL.md:151-172")[0] == "ok")
    check("control: leccion inexistente -> bad",
          resolve_pointer("LECCIONES.md#99")[0] == "bad")
    check("control: rango fuera del archivo -> bad",
          resolve_pointer("LECCIONES.md:9990-9999")[0] == "bad")
    check("control: archivo inexistente -> bad",
          resolve_pointer("NOPE.md:1")[0] == "bad")

    cats = router_knowledge.CATEGORIES
    for needed in ("pelo", "quelonio", "material_procedural", "export_godot",
                   "mamifero", "prop", "arquitectura", "bioma"):
        check("existe la categoria %s" % needed, needed in cats)

    n_ok = n_unchecked = 0
    for name, d in cats.items():
        miss = [f for f in ("aliases", "established", "discarded",
                            "discarded_sources", "structural_note", "must_read",
                            "required_views", "lessons", "sources") if not d.get(f)]
        if "mannequin_m" not in d:
            miss.append("mannequin_m")
        check("%s: campos obligatorios" % name, not miss, "faltan %s" % miss)
        check("%s: mannequin_m es 1.80 o trae razon" % name,
              d["mannequin_m"] == 1.80
              or (d["mannequin_m"] is None and d.get("mannequin_exempt")))
        check("%s: use_size tiene sizes+basis o trae razon" % name,
              (d.get("use_size") and d["use_size"].get("sizes")
               and d["use_size"].get("basis"))
              or (d.get("use_size") is None and d.get("use_size_exempt")))
        try:
            views.resolve_views(d["required_views"])
            ok_views = True
        except SystemExit:
            ok_views = False
        check("%s: required_views validas y con los angulos ingratos" % name,
              ok_views)
        check("%s: cada tecnica descartada cita su fuente" % name,
              set(d["discarded"]) == set(d["discarded_sources"]))
        ptrs = list(d["sources"]) + list(d["discarded_sources"].values()) \
            + list(d["lessons"]) \
            + [sr["source"] for sr in d.get("size_ranges", [])]
        bad = []
        for ptr in ptrs:
            st, detail = resolve_pointer(ptr)
            if st == "bad":
                bad.append(detail)
            elif st == "ok":
                n_ok += 1
            else:
                n_unchecked += 1
        check("%s: toda cita resuelve" % name, not bad, "; ".join(bad))
        if d.get("structure_spec"):
            check("%s: structure_spec existe" % name, os.path.isfile(
                os.path.join(ROOT, d["structure_spec"], "_structure_spec.md")))
    print("      citas verificadas: %d   sin verificar (fuera de alcance): %d"
          % (n_ok, n_unchecked))
    check("se verifico al menos una cita (el chequeo no esta ciego)", n_ok > 0)

    for k, (why, src) in router_knowledge.UNIVERSAL_DISCARDED.items():
        check("universal %s cita fuente que resuelve" % k,
              resolve_pointer(src)[0] in ("ok", "unchecked"))

    # Aliases must not be shared between families (ambiguous routing), and the
    # detector must be able to see a collision.
    def collisions(categories):
        seen, dup = {}, []
        for cname, cd in categories.items():
            for al in cd["aliases"]:
                if al in seen and seen[al] != cname:
                    dup.append(al)
                seen[al] = cname
        return dup
    check("control: el detector ve un alias repetido",
          collisions({"a": {"aliases": ["x"]}, "b": {"aliases": ["x"]}}) == ["x"])
    check("ningun alias esta en dos familias", not collisions(cats),
          str(collisions(cats)))


# ---------------------------------------------------------------------------
# motor_run.py -- the single entry point must keep calling every gate
# ---------------------------------------------------------------------------

import ast                                                   # noqa: E402
import json                                                  # noqa: E402
import motor_run                                             # noqa: E402

# step function -> the gate call that must stay inside it.
WIRING = {
    "step_technique": ["preflight_router.require_technique",
                       "preflight_router.requirements"],
    "step_structure": ["asset_spec.check_structure"],
    "step_generator": ["runpy.run_path"],
    "step_evidence": ["views.orbit_capture", "scale_ref.build_mannequin",
                      "views.resolve_views"],
    "step_scale": ["scale_ref.require_scale_evidence"],
    "step_use_size": ["use_size.require_use_size"],
}
ORDER = ["technique", "structure", "generator", "evidence", "scale", "use_size"]


def _calls_by_function(source):
    """{function name: set of dotted call names} -- the AST view of the file."""
    out = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef):
            names = set()
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    f, parts = sub.func, []
                    while isinstance(f, ast.Attribute):
                        parts.append(f.attr)
                        f = f.value
                    if isinstance(f, ast.Name):
                        parts.append(f.id)
                    names.add(".".join(reversed(parts)))
            out[node.name] = names
    return out


def _missing_wiring(source):
    calls = _calls_by_function(source)
    return ["%s -> %s" % (fn, c) for fn, need in WIRING.items()
            for c in need if c not in calls.get(fn, set())]


def _steps_order(source):
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(
                getattr(t, "id", "") == "STEPS" for t in node.targets):
            return [e.elts[0].value for e in node.value.elts]
    return []


def test_motor_run():
    print("\nmotor_run.py -- wiring (a gate that stops being called must be loud)")
    with open(os.path.join(ROOT, "motor_run.py"), encoding="utf-8") as fh:
        src = fh.read()

    miss = _missing_wiring(src)
    check("motor_run llama a TODOS los gates", not miss, "; ".join(miss))
    check("el orden de pasos es technique>structure>generator>evidence>scale>use_size",
          _steps_order(src) == ORDER, str(_steps_order(src)))

    # Controls: the detector must see a gate being unwired.
    unwired = src.replace("use_size.require_use_size(", "print(")
    check("control: detecta require_use_size removido",
          any("require_use_size" in m for m in _missing_wiring(unwired)))
    unwired = src.replace("scale_ref.require_scale_evidence(", "print(")
    check("control: detecta require_scale_evidence removido",
          any("require_scale_evidence" in m for m in _missing_wiring(unwired)))
    unwired = src.replace("preflight_router.require_technique(", "print(")
    check("control: detecta require_technique removido",
          any("require_technique" in m for m in _missing_wiring(unwired)))
    unwired = src.replace("asset_spec.check_structure(", "print(")
    check("control: detecta check_structure removido",
          any("check_structure" in m for m in _missing_wiring(unwired)))
    reordered = src.replace('("technique", step_technique),\n    ("structure", '
                            'step_structure),', '("structure", step_structure),\n'
                            '    ("technique", step_technique),')
    check("control: detecta pasos reordenados",
          _steps_order(reordered) != ORDER)

    # Behaviour, no Blender: bad inputs stop BEFORE the generator runs.
    with tempfile.TemporaryDirectory() as tmp:
        gen = os.path.join(tmp, "g.py")
        with open(gen, "w", encoding="utf-8") as fh:
            fh.write("# empty generator\n")
        ran = []

        def fake_generator(ctx):
            ran.append(ctx["subject"])

        def steps(extra=None):
            return [("technique", motor_run.step_technique),
                    ("structure", motor_run.step_structure),
                    ("generator", fake_generator)]

        def go(subject, *opts, sidecar=None):
            ran.clear()
            if sidecar is not None:
                with open(os.path.join(tmp, "g.motor.json"), "w",
                          encoding="utf-8") as fh:
                    json.dump(sidecar, fh)
            elif os.path.exists(os.path.join(tmp, "g.motor.json")):
                os.remove(os.path.join(tmp, "g.motor.json"))
            return motor_run.run([gen, subject, "--motor-out",
                                  os.path.join(tmp, "out")] + list(opts),
                                 steps=steps())

        expect_exit("sujeto desconocido -> frena",
                    go, "astrolabio de bronce", "--motor-technique", "x")
        check("... y el generador NO corrio", ran == [])
        expect_exit("sin tecnica declarada -> frena", go, "gato gris")
        check("... y el generador NO corrio (sin tecnica)", ran == [])
        expect_exit("tecnica descartada -> frena", go, "pelo del guerrero",
                    "--motor-technique", "polygon_shells")
        check("... y el generador NO corrio (descartada)", ran == [])
        expect_exit("sin partes moviles ni exencion -> frena",
                    go, "gato gris", "--motor-technique", "x")
        check("... y el generador NO corrio (sin estructura)", ran == [])
        expect_exit("tortuga: 'tail' sin fila de estructura -> frena",
                    go, "tortuga", "--motor-technique", "x")
        check("... y el generador NO corrio (parte sin investigar)", ran == [])
        expect_exit("exencion SIN razon no cuenta como exencion",
                    go, "gato gris", "--motor-technique", "x",
                    sidecar={"structure": {"exempt": ""}})
        ctx = go("gato gris", "--motor-technique", "x",
                 sidecar={"structure": {"exempt": "placeholder sin anatomia"}})
        check("con exencion razonada el generador SI corre", ran == ["gato gris"])
        rows = {r["prop"]: r["state"] for r in ctx["report"].rows}
        check("la exencion queda NOT_APPLICABLE en el veredicto",
              rows.get("structure") == NOT_APPLICABLE)
        check("el veredicto se escribio a disco",
              os.path.isfile(os.path.join(tmp, "out", "motor_verdict.json")))

    # The first real client's sidecar must be valid against the live router.
    with open(os.path.join(ROOT, "recetas", "gato", "build_gato.motor.json"),
              encoding="utf-8") as fh:
        side = json.load(fh)
    expect_no_exit("build_gato.motor.json: tecnica aceptada por el router",
                   preflight_router.require_technique, "gato gris",
                   side["technique"], verbose=False)
    check("build_gato.motor.json: la exencion de estructura trae razon",
          len(side["structure"]["exempt"]) > 20)
    with open(os.path.join(ROOT, "recetas", "gato", "build_gato.py"),
              encoding="utf-8") as fh:
        gsrc = fh.read()
    check("build_gato no llama gates por su cuenta (los corre motor_run)",
          "require_technique" not in gsrc and "require_structure" not in gsrc)


# ---------------------------------------------------------------------------
# preflight_router.py
# ---------------------------------------------------------------------------

def test_router():
    print("\npreflight_router.py")

    r = preflight_router.route("voy a modelar el pelo del guerrero")
    check("resuelve 'pelo' por palabra clave", r.category == "pelo")
    check("trae la tecnica establecida", "cards" in r.data["established"])

    # THE 2026-08-22 case: the technique the contract had already ruled out.
    msg = expect_exit("tecnica descartada -> SystemExit",
                      preflight_router.require_technique,
                      "pelo del guerrero", "polygon_shells", verbose=False)
    check("el error explica POR QUE esta descartada", "gorro" in msg)

    expect_no_exit("tecnica establecida pasa",
                   preflight_router.require_technique,
                   "pelo del guerrero", "cards_alpha", verbose=False)

    expect_no_exit("alias en ingles resuelve igual",
                   preflight_router.require_technique,
                   "warrior hair pass", "cards_alpha", verbose=False)

    check("resuelve tortuga", preflight_router.route("build turtle").category
          == "quelonio")
    check("tortuga trae sus partes moviles",
          "humerus_L" in preflight_router.route("turtle").data["moving_parts"])
    check("resuelve material procedural",
          preflight_router.route("material de hormigon").category
          == "material_procedural")

    # An unknown subject must be loud about being unknown, never silently fine.
    unknown = preflight_router.route("astrolabio de bronce")
    check("categoria desconocida no matchea", not unknown.matched)
    check("categoria desconocida es NOT_TESTED, no PASS",
          unknown.to_report().verdict() == NOT_TESTED)

    # Step 2: fail closed on unknown (it used to return silently).
    msg = expect_exit("sujeto sin categoria -> SystemExit (fail closed)",
                      preflight_router.require_technique,
                      "astrolabio de bronce", "cualquiera", verbose=False)
    check("el error dice que no hay conocimiento y como salir",
          "no knowledge registered" in msg and "allow_unknown=True" in msg
          and "astrolabio" in msg)
    expect_exit("allow_unknown sin razon -> SystemExit",
                preflight_router.require_technique, "astrolabio de bronce",
                "x", verbose=False, allow_unknown=True)
    expect_no_exit("allow_unknown con razon pasa",
                   preflight_router.require_technique, "astrolabio de bronce",
                   "x", verbose=False, allow_unknown=True,
                   reason="instrumento unico, sin familia que cosechar")
    expect_exit("sujeto vacio -> SystemExit",
                preflight_router.require_technique, "", "x", verbose=False)

    # Step 2: aliases are whole words. Positive controls first, so the
    # negatives below cannot be a blind regex.
    check("control: 'wood door' resuelve material_procedural",
          preflight_router.route("wood door").category == "material_procedural")
    check("control: plural 'tortugas' resuelve",
          preflight_router.route("dos tortugas").category == "quelonio")
    check("control: slug 'wood_door' resuelve",
          preflight_router.route("wood_door").category == "material_procedural")
    check("control: acento 'caparazón' resuelve",
          preflight_router.route("caparazón").category == "quelonio")
    check("'woodpecker' NO resuelve a wood",
          not preflight_router.route("woodpecker").matched)
    check("'furniture' NO resuelve a fur (pelo)",
          not preflight_router.route("furniture").matched)
    check("'exporter' NO resuelve a export",
          not preflight_router.route("exporter").matched)
    expect_exit("woodpecker pasa a ser desconocido -> SystemExit",
                preflight_router.require_technique, "woodpecker", "x",
                verbose=False)

    # Several families in one subject: the discarded set is the UNION.
    both = preflight_router.route_all("pelo de la tortuga")
    check("un sujeto con dos familias resuelve las dos",
          {r.category for r in both} == {"pelo", "quelonio"})
    expect_exit("tecnica descartada de la SEGUNDA familia tambien frena",
                preflight_router.require_technique, "pelo de la tortuga",
                "uv_sphere_painted", verbose=False)


def test_router_requirements():
    print("\npreflight_router.requirements()")
    check("gato -> mamifero", preflight_router.route("gato gris").category
          == "mamifero")
    check("carro de la aldea -> prop y arquitectura",
          {r.category for r in preflight_router.route_all("carro de la aldea")}
          == {"prop", "arquitectura"})
    check("pradera -> bioma", preflight_router.route("pradera").category
          == "bioma")
    check("gatito/'catapult' no son gato",
          not preflight_router.route("catapult").matched)

    expect_exit("tecnica universal (viewport screenshot) frena",
                preflight_router.require_technique, "gato gris",
                "viewport_screenshot_evidence", verbose=False)
    expect_exit("tecnica universal frena tambien con allow_unknown",
                preflight_router.require_technique, "astrolabio",
                "single_view_judgement", verbose=False, allow_unknown=True,
                reason="x")
    expect_exit("tecnica descartada de mamifero frena",
                preflight_router.require_technique, "gato", "copy_paste_sibling",
                verbose=False)
    expect_exit("tecnica descartada de bioma frena",
                preflight_router.require_technique, "roca del bosque",
                "noise_normal_displacement_rock", verbose=False)
    expect_no_exit("tecnica no descartada de mamifero pasa",
                   preflight_router.require_technique, "gato",
                   "shape_keys_on_float_color_body", verbose=False)

    req = preflight_router.requirements("gato gris")
    check("gato exige maniqui y las 7 vistas", req["mannequin"]
          and len(req["views"]) == 7)
    check("gato declara el hueco de investigacion felina",
          any("feline" in g for g in req["gaps"]))
    req = preflight_router.requirements("lobo")
    check("lobo trae el rango de altura CON fuente", req["height_range"]
          == (0.66, 0.84))
    check("gato NO inventa rango de altura (no hay fuente)",
          preflight_router.requirements("gato")["height_range"] is None)
    req = preflight_router.requirements("material de hormigon")
    check("material: maniqui exento con razon, sin use_size",
          not req["mannequin"] and req["mannequin_exempt"]
          and req["use_size"] is None and req["use_size_exempt"])
    req = preflight_router.requirements("tortuga")
    check("tortuga arrastra su structure_spec y sus 7 partes",
          req["structure"] and len(req["structure"][0][1]) == 7)


def main():
    print("FIXTURES ADVERSARIALES -- cada gate contra un caso que DEBE fallar")
    test_verdict()
    test_asset_spec()
    test_asset_spec_corpus_shapes()
    test_material_swatch()
    test_scale_ref_and_views()
    test_router_knowledge()
    test_router()
    test_router_requirements()
    test_motor_run()

    failed = [n for n, ok, _ in _results if not ok]
    print("\n" + "=" * 60)
    print("  %d/%d ok" % (len(_results) - len(failed), len(_results)))
    if failed:
        print("  FALLARON:")
        for n in failed:
            print("    - %s" % n)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
