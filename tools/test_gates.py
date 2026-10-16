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
import shutil
import subprocess
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
from recetas import rubric as rubric_mod                      # noqa: E402

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
    with open(os.path.join(ROOT, "recetas", "material_swatch.py"),
              encoding="utf-8") as fh:
        msrc = fh.read()
    check("el probe renderiza a 16 bits con dither apagado (camino real)",
          "color_depth='16'" in msrc and "dither_intensity = 0.0" in msrc
          and "image_settings.color_depth = color_depth" in msrc)
    check("el umbral declara a que exposicion fue calibrado (media ~0.094)",
          "0.094" in msrc)
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
    # Review 3 #4: a WEAK source warns, it never fails.
    rep = scale_ref.scale_evidence_report(1.80, ["a.png"], asset_height=1.5,
                                          expected_height_m=(3.2, 4.8), weak_source=True,
                                          exists=ok, size_of=big)
    row = rep.rows[-1]
    check("fuente DEBIL fuera de rango -> WARN (NOT_TESTED), no FAIL",
          row["state"] == NOT_TESTED and "WARN (weak source)" in row["detail"]
          and not rep.failed, str(row))
    rep = scale_ref.scale_evidence_report(1.80, ["a.png"], asset_height=1.5,
                                          expected_height_m=(3.2, 4.8),
                                          exists=ok, size_of=big)
    check("control: la MISMA medicion con fuente explicita -> FAIL",
          rep.rows[-1]["state"] == FAIL)
    rep = scale_ref.scale_evidence_report(1.80, ["a.png"], asset_height=4.0,
                                          expected_height_m=(3.2, 4.8), weak_source=True,
                                          exists=ok, size_of=big)
    check("fuente debil dentro de rango -> PASS", rep.rows[-1]["state"] == PASS)
    rep = scale_ref.scale_evidence_report(1.80, ["a.png"], asset_span=0.3,
                                          expected_span_m=(1.15, 1.53), weak_source=True,
                                          exists=ok, size_of=big)
    check("fuente debil en span fuera de rango -> WARN tambien",
          rep.rows[-1]["state"] == NOT_TESTED)
    rep = scale_ref.scale_evidence_report(1.80, ["a.png"], asset_span=1.30,
                                          expected_span_m=(1.15, 1.53),
                                          exists=ok, size_of=big)
    check("envergadura dentro del rango CON fuente -> PASS",
          rep.rows[-1]["prop"] == "asset_span_vs_source"
          and rep.rows[-1]["state"] == PASS)
    rep = scale_ref.scale_evidence_report(1.80, ["a.png"], asset_span=0.30,
                                          expected_span_m=(1.15, 1.53),
                                          exists=ok, size_of=big)
    check("paloma de 0.30 m de envergadura (cuervo) -> FAIL",
          rep.rows[-1]["state"] == FAIL)
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

    with tempfile.TemporaryDirectory() as tmp:
        for n in ("g_frente.png", "g_bajo.png", "other_frente.png", "g_notes.txt"):
            open(os.path.join(tmp, n), "wb").write(b"x")
        removed = views.clear_stale(tmp, "g")
        left = sorted(os.listdir(tmp))
        check("clear_stale borra los PNG viejos del prefijo", removed == 2)
        check("... y no toca otros prefijos ni archivos que no son PNG",
              left == ["g_notes.txt", "other_frente.png"], str(left))
    check("orbit_capture llama clear_stale antes de renderizar",
          "clear_stale(out_dir, prefix)" in open(os.path.join(
              ROOT, "recetas", "views.py"), encoding="utf-8").read().split(
              "def orbit_capture")[1])

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
GAME_ART = os.path.expanduser("~/proyectos/Juego/DungeonParty-A/game/docs/art")
_PTR = re.compile(r"^(?:(game|gametools|memory|gameart):)?([^:#|]+)"
                  r"(?::(\d+)(?:-(\d+))?|#(\d+))?(?:\|(.+))?$")


def resolve_pointer(ptr):
    """
    Returns (state, detail): "ok" | "bad" | "unchecked" (base dir absent or a
    doc outside this machine's reach -- reported, never silently counted as ok).
    """
    m = _PTR.match(ptr)
    if not m:
        return "bad", "unparseable pointer %r" % ptr
    kind, rel, a, b, lesson, anchor = m.groups()
    base = {None: ROOT, "game": GAME_REFS, "gametools": GAME_TOOLS,
            "memory": MEMORY, "gameart": GAME_ART}.get(kind)
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
        if not (1 <= lo <= hi <= len(lines)):
            return "bad", "%s:%d-%d outside the file (%d lines)" % (
                rel, lo, hi, len(lines))
        if not anchor:
            return "bad", ("%s has no |anchor: a line range without a content "
                           "check drifts silently" % ptr)
        if anchor not in "\n".join(lines[lo - 1:hi]):
            return "bad", "anchor %r not found in %s:%d-%d" % (anchor, rel, lo, hi)
    return "ok", ""


def test_router_knowledge():
    print("\nrouter_knowledge.py -- completeness and citations")

    # Positive/negative controls for the pointer checker itself: a checker that
    # cannot say "bad" would make every pointer below meaningless.
    check("control: puntero bueno resuelve",
          resolve_pointer("LECCIONES.md#6")[0] == "ok"
          and resolve_pointer("CREATION_PROTOCOL.md:151-172|mannequin")[0] == "ok")
    check("control: leccion inexistente -> bad",
          resolve_pointer("LECCIONES.md#99")[0] == "bad")
    check("control: rango fuera del archivo -> bad",
          resolve_pointer("LECCIONES.md:9990-9999|x")[0] == "bad")
    check("control: ancla ausente en el rango -> bad (cita desplazada)",
          resolve_pointer("CREATION_PROTOCOL.md:151-172|zzz_no_esta")[0] == "bad")
    check("control: la cita vieja (RECETAS:36, desplazada +4) ahora falla",
          resolve_pointer("recetas/RECETAS.md:36|get_viewport_screenshot")[0] == "bad")
    check("control: rango sin ancla -> bad",
          resolve_pointer("CREATION_PROTOCOL.md:151-172")[0] == "bad")
    check("control: ancla correcta -> ok",
          resolve_pointer("CREATION_PROTOCOL.md:151-172|1.80 m mannequin")[0]
          == "ok")
    check("control: archivo inexistente -> bad",
          resolve_pointer("NOPE.md:1")[0] == "bad")

    cats = router_knowledge.CATEGORIES
    for needed in ("pelo", "quelonio", "material_procedural", "export_godot",
                   "mamifero", "prop", "arquitectura", "bioma", "construct",
                   "blob", "artropodo", "serpiente", "ave", "humano"):
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
        for sr in d.get("size_ranges", []):
            check("%s: size_range %s trae dim valida y rango ordenado"
                  % (name, sr["aliases"][0]),
                  sr["dim"] in ("height", "span")
                  and sr["range_m"][0] < sr["range_m"][1])
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
    check("el doc del juego existe: las citas gameart: se verifican de verdad",
          os.path.isfile(os.path.join(GAME_ART, "_asset_creation_contract.md")))
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
sys.path.insert(0, os.path.join(ROOT, "tools"))

# step function -> the gate call that must stay inside it.
WIRING = {
    "step_technique": ["preflight_router.require_technique",
                       "preflight_router.requirements"],
    "step_structure": ["asset_spec.check_structure"],
    "step_generator": ["runpy.run_path"],
    "step_mesh": ["mesh_quality.check_mesh"],
    "step_gltf": ["gltf_check.validate", "gltf_check.judge"],
    "step_physics": ["physics.check_physics"],
    "step_evidence": ["views.orbit_capture", "_place_mannequin",
                      "views.resolve_views"],
    "step_scale": ["scale_ref.require_scale_evidence"],
    "step_use_size": ["use_size.require_use_size"],
}
ORDER = ["technique", "structure", "generator", "mesh", "gltf", "physics",
         "evidence", "scale", "use_size"]


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


def _raises(exc, fn, *a):
    try:
        fn(*a)
    except exc:
        return True
    return False


EXPECTED_FUNCS = {"technique": "step_technique", "structure": "step_structure",
                  "generator": "step_generator", "mesh": "step_mesh",
                  "gltf": "step_gltf", "physics": "step_physics",
                  "evidence": "step_evidence",
                  "scale": "step_scale", "use_size": "step_use_size"}


def _steps_wired(steps):
    """Each STEPS entry must be the real function for its label (a lambda or a
    swapped function under the right label is not wiring)."""
    return [(n, getattr(f, "__name__", "?")) for n, f in steps
            if EXPECTED_FUNCS.get(n) != getattr(f, "__name__", "?")
            or f is not getattr(motor_run, EXPECTED_FUNCS.get(n, ""), None)]


def _early_return_before_gate(source):
    """Functions whose gate call sits AFTER an unconditional return/raise at
    the top level of the body (dead gate)."""
    bad = []
    for node in ast.parse(source).body:
        if not (isinstance(node, ast.FunctionDef) and node.name in WIRING):
            continue
        for i, stmt in enumerate(node.body):
            seg = ast.Module(body=[stmt], type_ignores=[])
            dotted = set()
            for sub in ast.walk(seg):
                if isinstance(sub, ast.Call):
                    f, parts = sub.func, []
                    while isinstance(f, ast.Attribute):
                        parts.append(f.attr)
                        f = f.value
                    if isinstance(f, ast.Name):
                        parts.append(f.id)
                    dotted.add(".".join(reversed(parts)))
            if any(c in dotted for c in WIRING[node.name]):
                break
            if isinstance(stmt, (ast.Return, ast.Raise)):
                bad.append(node.name)
                break
    return bad


class _Obj:
    """Stand-in for a bpy object in the Blender-free behaviour tests."""
    name = "stub"


def _install_stubs(tmp, spies):
    """Patch ONLY the Blender-touching edges; every step function and every
    gate call site stays real, and the gates are replaced by spies so the test
    can prove they are reached."""
    saved = {}

    def patch(obj, attr, value):
        saved[(obj, attr)] = getattr(obj, attr)
        setattr(obj, attr, value)

    def orbit(out_dir, prefix, frame, chosen):
        os.makedirs(out_dir, exist_ok=True)
        paths = []
        for v in chosen:
            pth = os.path.join(out_dir, "%s_%s.png" % (prefix, v[0]))
            with open(pth, "wb") as fh:
                fh.write(b"png")
            paths.append(pth)
        spies.append(("orbit", len(chosen)))
        return paths

    def scale_gate(paths, **kw):
        spies.append(("scale", len(paths)))
        return Report("SCALE").add("mannequin_in_scene", PASS)

    def size_gate(path, sizes, out=None):
        spies.append(("use_size", tuple(sizes)))
        return out

    def mesh_gate(objs, limits, verbose=True):
        spies.append(("mesh", dict(limits)))
        return Report("MESH").add("x: nonmanifold_edges", PASS), {"stub": {}}

    def physics_gate(objs, cfg, ground_z=0.0, verbose=True):
        spies.append(("physics", dict(cfg)))
        return (Report("PHYSICS").add("ground_contact", PASS),
                {"com": [0, 0, 0.5], "islands": {"count": 0}})

    patch(motor_run.physics, "check_physics", physics_gate)
    patch(motor_run.mesh_quality, "check_mesh", mesh_gate)
    patch(motor_run, "_asset_objects", lambda ctx: [_Obj()])
    patch(motor_run, "_place_mannequin", lambda a: spies.append(("mannequin", 1)) or [_Obj()])
    patch(motor_run, "_save_blend", lambda p: spies.append(("save", 1)))
    patch(motor_run.views, "orbit_capture", orbit)
    patch(motor_run.scale_ref, "require_scale_evidence", scale_gate)
    patch(motor_run.use_size, "require_use_size", size_gate)

    def restore():
        for (obj, attr), val in saved.items():
            setattr(obj, attr, val)
    return restore


def test_motor_run():
    print("\nmotor_run.py -- wiring (a gate that stops being called must be loud)")
    with open(os.path.join(ROOT, "motor_run.py"), encoding="utf-8") as fh:
        src = fh.read()

    miss = _missing_wiring(src)
    check("motor_run llama a TODOS los gates", not miss, "; ".join(miss))
    check("el orden de pasos es technique>structure>generator>evidence>scale>use_size",
          _steps_order(src) == ORDER, str(_steps_order(src)))
    check("cada entrada de STEPS es la funcion real de su etiqueta",
          not _steps_wired(motor_run.STEPS), str(_steps_wired(motor_run.STEPS)))
    check("ningun gate queda detras de un return/raise incondicional",
          not _early_return_before_gate(src), str(_early_return_before_gate(src)))

    # Mutation controls: the detectors must SEE each way of unwiring a gate.
    for gate in ("use_size.require_use_size(", "scale_ref.require_scale_evidence(",
                 "preflight_router.require_technique(", "asset_spec.check_structure("):
        check("control: detecta %s removido" % gate.split("(")[0],
              bool(_missing_wiring(src.replace(gate, "print("))))
    reordered = src.replace('("technique", step_technique),\n    ("structure", '
                            'step_structure),', '("structure", step_structure),\n'
                            '    ("technique", step_technique),')
    check("control: detecta pasos reordenados", _steps_order(reordered) != ORDER)
    lam = [(n, (lambda c: None) if n == "scale" else f) for n, f in motor_run.STEPS]
    check("control: detecta ('scale', lambda) en STEPS", bool(_steps_wired(lam)))
    dead = src.replace("def step_scale(ctx):\n", "def step_scale(ctx):\n    return\n", 1)
    check("control: detecta un return antes de require_scale_evidence",
          "step_scale" in _early_return_before_gate(dead))
    check("control: la fuente sin mutar no dispara el detector de return",
          "step_scale" not in _early_return_before_gate(src))

    # Behaviour through the REAL motor_run.STEPS, no Blender.
    with tempfile.TemporaryDirectory() as tmp:
        def gen(name, body):
            path = os.path.join(tmp, name)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(body)
            return path

        ok_gen = gen("ok.py", "RAN = True\n")
        exit0_gen = gen("ex.py", "import sys\nsys.exit(0)\n")
        raise0_gen = gen("rz.py", "raise SystemExit(0)\n")
        boom_gen = gen("bm.py", "raise RuntimeError('boom')\n")
        out = os.path.join(tmp, "out")
        spies = []
        restore = _install_stubs(tmp, spies)

        reg = os.path.join(tmp, "approved.json")
        saved_reg = motor_run.REGISTRY_PATH
        motor_run.REGISTRY_PATH = reg

        def write_registry(entries):
            with open(reg, "w", encoding="utf-8") as fh:
                json.dump(entries, fh)

        def entry(generator, subject, kind, **over):
            e = {"generator": generator, "subject": subject, "type": kind,
                 "reason": "approved: placeholder with no anatomy claim",
                 "approved_by": "Joan", "date": "2026-10-08"}
            e.update(over)
            return e

        def go(generator, subject, *opts, sidecar=None, steps=None,
               approve=False, approvals=None):
            spies.clear()
            write_registry(approvals if approvals is not None else (
                [entry(generator, subject, "structure_exempt")] if approve else []))
            side = os.path.splitext(generator)[0] + ".motor.json"
            if sidecar is not None:
                with open(side, "w", encoding="utf-8") as fh:
                    json.dump(sidecar, fh)
            elif os.path.exists(side):
                os.remove(side)
            return motor_run.run([generator, subject, "--motor-out", out]
                                 + list(opts), steps=steps)

        exempt = {"structure": {"exempt": "placeholder sin anatomia"}}
        try:
            expect_exit("sujeto desconocido -> frena",
                        go, ok_gen, "astrolabio de bronce", "--motor-technique", "x")
            expect_exit("sin tecnica declarada -> frena", go, ok_gen, "gato gris")
            expect_exit("tecnica descartada -> frena", go, ok_gen,
                        "pelo del guerrero", "--motor-technique", "polygon_shells")
            expect_exit("sin partes moviles ni exencion -> frena",
                        go, ok_gen, "gato gris", "--motor-technique", "x")
            expect_exit("tortuga: 'tail' sin fila de estructura -> frena",
                        go, ok_gen, "tortuga", "--motor-technique", "x")
            expect_exit("exencion SIN razon no cuenta",
                        go, ok_gen, "gato gris", "--motor-technique", "x",
                        sidecar={"structure": {"exempt": ""}})
            check("... ningun frenado temprano llego a orbitar ni a los gates",
                  spies == [])

            ctx = go(ok_gen, "gato gris", "--motor-technique", "x", sidecar=exempt, approve=True)
            check("STEPS reales: los 6 pasos corrieron y se registraron",
                  ctx["completed"] == ORDER, str(ctx["completed"]))
            gates = [s[0] for s in spies]
            check("cada gate fue ALCANZADO (mesh, physics, orbit, scale, use_size)",
                  all(g in gates for g in ("mesh", "physics", "orbit", "scale",
                                           "use_size")), str(gates))
            ph_cfg = [s[1] for s in spies if s[0] == "physics"][0]
            check("el gate de physics recibe la politica de la familia (mamifero: se para, "
                  "islas fail)", ph_cfg["stands"] and ph_cfg["islands"] == "fail"
                  and ph_cfg["drop_test"], str(ph_cfg))
            mesh_lim = [s[1] for s in spies if s[0] == "mesh"][0]
            check("el gate de mesh recibe los limites de la familia (router)",
                  mesh_lim["max_nonmanifold"] == 0 and mesh_lim["needs_uv"] is False
                  and mesh_lim["max_tris"] is None, str(mesh_lim))
            check("el use_size gate recibio los tamanos de la familia",
                  ("use_size", (512, 256, 128)) in spies)
            rows = {r["prop"]: r["state"] for r in ctx["report"].rows}
            check("el veredicto tiene una fila por paso",
                  all(rows.get(ROW) for ROW in ("technique", "structure",
                                               "generator", "mesh", "gltf",
                                               "physics", "views", "scale",
                                               "use_size")), str(rows))
            check("la exencion queda NOT_APPLICABLE", rows["structure"] == NOT_APPLICABLE)
            with open(os.path.join(out, "motor_verdict.json"), encoding="utf-8") as fh:
                vj = json.load(fh)
            check("con huecos abiertos el veredicto es PASS_WITH_GAPS, no PASS",
                  vj["verdict"] == "PASS_WITH_GAPS" and len(vj["gaps"]) >= 3,
                  str(vj["verdict"]))
            check("el verdict.json trae rubric PENDING y status EVIDENCE_READY (no PASS)",
                  vj["status"] == "EVIDENCE_READY"
                  and vj["rubric"]["status"] == "PENDING"
                  and len(vj["rubric"]["dimensions"]) == 5
                  and len(vj["rubric"]["questions"]) > 5, str(vj.get("status")))
            check("el verdict.json guarda sha256 de CADA evidencia y es puntuable",
                  vj["scoreable"] is True and set(vj["evidence_sha256"]) == set(vj["evidence"])
                  and all(len(h) == 64 for h in vj["evidence_sha256"].values()))
            check("... y esos hashes coinciden con los archivos en disco",
                  all(rubric_mod.sha256_file(p) == h
                      for p, h in vj["evidence_sha256"].items()))
            check("... y apply_review sobre ese verdict real lo acepta",
                  rubric_mod.apply_review(
                      vj, "Joan",
                      {k: (4, "") for k in vj["rubric"]["dimensions"]},
                      {q["id"]: ("yes", "") for q in vj["rubric"]["questions"]})
                  == "PASS_WITH_GAPS")
            check("... y un verdict real con un render alterado se rechaza", (
                lambda: (open(vj["evidence"][0], "ab").write(b"x"),
                         _raises(rubric_mod.RubricError, rubric_mod.apply_review,
                                 json.load(open(os.path.join(out, "motor_verdict.json"))),
                                 "Joan", {}, {}))[1])())
            check("... y un verdict real con gates NOT_TESTED nunca es puntuable",
                  rubric_mod.overall_status(dict(vj, verdict="NOT_TESTED")) == "FAIL")
            check("... y los huecos nombran la exencion y la altura sin fuente",
                  any("structure exempt" in g for g in vj["gaps"])
                  and any("size range" in g for g in vj["gaps"]))
            check("el veredicto se escribio a disco",
                  os.path.isfile(os.path.join(out, "motor_verdict.json")))

            # HIGH #1: a generator that exits by itself must FAIL the run.
            for label, g in (("sys.exit(0)", exit0_gen),
                             ("raise SystemExit(0)", raise0_gen),
                             ("RuntimeError", boom_gen)):
                msg = ""
                try:
                    go(g, "gato gris", "--motor-technique", "x", sidecar=exempt, approve=True)
                except (SystemExit, RuntimeError) as exc:
                    msg = str(exc)
                check("generador con %s -> la corrida FALLA" % label, bool(msg))
                check("... y no llego a evidencia/escala/use_size",
                      not any(s[0] in ("orbit", "scale", "use_size")
                              for s in spies))
            check("el mensaje dice que el generador salio solo",
                  "exited by itself" in msg or "boom" in msg)

            # mesh gate FAIL stops the run before evidence.
            orig_check = motor_run.mesh_quality.check_mesh
            motor_run.mesh_quality.check_mesh = lambda o, l, verbose=True: (
                Report("MESH").add("bad: nonmanifold_edges", FAIL, "3"), {})
            try:
                expect_exit("mesh con FAIL -> la corrida falla",
                            go, ok_gen, "gato gris", "--motor-technique", "x",
                            sidecar=exempt, approve=True)
                check("... y no llego a la evidencia", not any(
                    s[0] == "orbit" for s in spies))
            finally:
                motor_run.mesh_quality.check_mesh = orig_check

            orig_ph = motor_run.physics.check_physics
            motor_run.physics.check_physics = lambda o, c, ground_z=0.0, verbose=True: (
                Report("PHYSICS").add("com_in_support", FAIL, "tips over"), {})
            try:
                expect_exit("physics con FAIL -> la corrida falla",
                            go, ok_gen, "gato gris", "--motor-technique", "x",
                            sidecar=exempt, approve=True)
                check("... y no llego a la evidencia (physics)", not any(
                    s[0] == "orbit" for s in spies))
            finally:
                motor_run.physics.check_physics = orig_ph

            # Review 3 #4 through the real step_scale: weak golem size only warns.
            real_scale = motor_run.scale_ref.require_scale_evidence
            real_validate = motor_run.gltf_check.validate
            motor_run.scale_ref.require_scale_evidence = lambda paths, **kw: \
                motor_run.scale_ref.scale_evidence_report(
                    1.80, paths, asset_height=1.5,
                    expected_height_m=kw["expected_height_m"], weak_source=kw["weak_source"],
                    exists=lambda p: True, size_of=lambda p: 9)
            try:
                glb_ok = gen("gk.py", "import os\nopen(os.path.join(os.environ["
                                      "'MOTOR_OUT_DIR'], 'g.glb'), 'wb').write(b'g')\n")
                motor_run.gltf_check.validate = lambda p, **k: {
                    "file": "g.glb", "numErrors": 0, "numWarnings": 0,
                    "numInfos": 0, "version": "t"}
                ctx = go(glb_ok, "golem", "--motor-technique", "x",
                         sidecar=exempt, approve=True)
                check("golem de 1.5 m (rango debil 3.2-4.8): la corrida PASA con WARN",
                      ctx["completed"] == ORDER)
                check("... y el WARN + la fuente debil quedan como huecos",
                      any(g.startswith("size WARN") for g in ctx["gaps"])
                      and any("WEAK" in g for g in ctx["gaps"]), str(ctx["gaps"]))
            finally:
                motor_run.scale_ref.require_scale_evidence = real_scale
                motor_run.gltf_check.validate = real_validate

            # glTF: a .glb written by the generator must be validated.
            glb_gen = gen("gl.py", "import os\nopen(os.path.join(os.environ["
                                   "'MOTOR_OUT_DIR'], 'x.glb'), 'wb').write(b'g')\n")
            orig_val = motor_run.gltf_check.validate
            try:
                motor_run.gltf_check.validate = lambda p, **k: {
                    "file": "x.glb", "numErrors": 0, "numWarnings": 0,
                    "numInfos": 1, "version": "t"}
                ctx = go(glb_gen, "gato gris", "--motor-technique", "x",
                         sidecar=exempt, approve=True)
                rows = {r["prop"]: r for r in ctx["report"].rows}
                check("glb escrito por el generador -> gltf PASS validado",
                      rows["gltf"]["state"] == PASS and "1 .glb" in rows["gltf"]["detail"])
                motor_run.gltf_check.validate = lambda p, **k: {
                    "file": "x.glb", "numErrors": 2, "numWarnings": 0,
                    "numInfos": 0, "version": "t", "errors": ["E1", "E2"]}
                expect_exit("glb con errores del validador -> la corrida falla",
                            go, glb_gen, "gato gris", "--motor-technique", "x",
                            sidecar=exempt, approve=True)
                motor_run.gltf_check.validate = lambda p, **k: {
                    "error": "validator not installed. Install: npm ..."}
                msg = expect_exit("validador NO instalado -> falla ruidosamente",
                                  go, glb_gen, "gato gris", "--motor-technique", "x",
                                  sidecar=exempt, approve=True)
                check("... con el texto 'validator not installed'",
                      "validator not installed" in msg)
            finally:
                motor_run.gltf_check.validate = orig_val
            ctx = go(ok_gen, "gato gris", "--motor-technique", "x",
                     sidecar=exempt, approve=True)
            rows = {r["prop"]: r["state"] for r in ctx["report"].rows}
            check("sin .glb el paso gltf es NOT_APPLICABLE con razon",
                  rows["gltf"] == NOT_APPLICABLE)
            check("... y queda como HUECO abierto (review 3 #2)",
                  "no glb exported - glTF not validated" in ctx["gaps"])
            for subj in ("golem", "king slime", "avispa", "serpiente", "pajaro",
                         "export glb"):
                msg = expect_exit("sin .glb, la familia de %r (entregable GLB) -> FAIL" % subj,
                                  go, ok_gen, subj, "--motor-technique", "x",
                                  sidecar=exempt, approve=True)
                check("... con mensaje 'no .glb was exported'", "no .glb was exported" in msg)
            ctx = go(ok_gen, "gato gris", "--motor-technique", "x",
                     sidecar=exempt, approve=True)
            check("control: el gato (no exige GLB) sigue pasando sin .glb",
                  ctx["completed"] == ORDER)
            # declared export path (sidecar / CLI), outside out/ and gen dir
            sub_gen = gen("sg.py", "import os\nos.makedirs(os.path.join(os.path.dirname("
                                   "__file__), 'exp'), exist_ok=True)\n"
                                   "open(os.path.join(os.path.dirname(__file__), 'exp', "
                                   "'m.glb'), 'wb').write(b'g')\n")
            seen = []
            motor_run.gltf_check.validate = lambda p, **k: seen.append(p) or {
                "file": "m.glb", "numErrors": 0, "numWarnings": 0, "numInfos": 0,
                "version": "t"}
            try:
                ctx = go(sub_gen, "golem", "--motor-technique", "x",
                         sidecar=dict(exempt, export_glb=["exp/m.glb"]), approve=True)
                check("export_glb declarado en el sidecar se valida (y el golem pasa)",
                      seen and seen[0].endswith("exp/m.glb")
                      and ctx["completed"] == ORDER, str(seen))
                seen.clear()
                ctx = go(sub_gen, "golem", "--motor-technique", "x",
                         "--motor-export", "exp/m.glb", sidecar=exempt, approve=True)
                check("--motor-export declarado por CLI se valida", bool(seen))
                expect_exit("path declarado que el generador NO escribio -> FAIL",
                            go, ok_gen, "gato gris", "--motor-technique", "x",
                            "--motor-export", "exp/nada.glb", sidecar=exempt,
                            approve=True)
            finally:
                motor_run.gltf_check.validate = orig_val

            # Mutations on the live STEPS must not pass.
            lam_steps = [(n, (lambda c: None) if n == "scale" else f)
                         for n, f in motor_run.STEPS]
            expect_exit("mutacion: ('scale', lambda) -> la corrida falla",
                        go, ok_gen, "gato gris", "--motor-technique", "x",
                        sidecar=exempt, approve=True, steps=lam_steps)
            noop_steps = [(n, (lambda c: None) if n == "use_size" else f)
                          for n, f in motor_run.STEPS]
            expect_exit("mutacion: ('use_size', lambda) -> la corrida falla",
                        go, ok_gen, "gato gris", "--motor-technique", "x",
                        sidecar=exempt, approve=True, steps=noop_steps)

            # Review #6: a generator cannot grant itself exemptions.
            msg = expect_exit("sidecar con exencion SIN entrada en el registro -> FAIL",
                              go, ok_gen, "gato gris", "--motor-technique", "x",
                              sidecar=exempt)
            check("... el mensaje manda a pedir aprobacion a Joan",
                  "ask Joan" in msg)
            check("... y el generador NO corrio", not any(
                s[0] in ("orbit", "scale", "use_size") for s in spies))
            expect_exit("entrada de OTRO sujeto no vale",
                        go, ok_gen, "gato blanco", "--motor-technique", "x",
                        sidecar=exempt,
                        approvals=[entry(ok_gen, "gato gris", "structure_exempt")])
            expect_exit("entrada de OTRO generador no vale",
                        go, ok_gen, "gato gris", "--motor-technique", "x",
                        sidecar=exempt,
                        approvals=[entry(exit0_gen, "gato gris", "structure_exempt")])
            expect_exit("entrada de otro TIPO no vale (allow_unknown != structure)",
                        go, ok_gen, "gato gris", "--motor-technique", "x",
                        sidecar=exempt,
                        approvals=[entry(ok_gen, "gato gris", "allow_unknown")])
            expect_exit("entrada sin approved_by -> registro malformado",
                        go, ok_gen, "gato gris", "--motor-technique", "x",
                        sidecar=exempt,
                        approvals=[entry(ok_gen, "gato gris", "structure_exempt",
                                         approved_by="")])
            expect_exit("sidecar asset_objects ya no se acepta",
                        go, ok_gen, "gato gris", "--motor-technique", "x",
                        sidecar={"asset_objects": ["x"]})
            expect_exit("--motor-allow-unknown sin entrada -> FAIL",
                        go, ok_gen, "astrolabio", "--motor-technique", "x",
                        "--motor-allow-unknown", "because")
            expect_exit("allow_unknown en el sidecar sin entrada -> FAIL",
                        go, ok_gen, "astrolabio", "--motor-technique", "x",
                        sidecar={"allow_unknown": "because"})
            # Approved unknown: still gets the mannequin, the 7 views, use_size.
            ctx = go(ok_gen, "astrolabio", "--motor-technique", "x",
                     "--motor-allow-unknown", "ignored text",
                     approvals=[entry(ok_gen, "astrolabio", "allow_unknown"),
                                entry(ok_gen, "astrolabio", "structure_exempt")])
            check("unknown aprobado: la escala NO se salta (maniqui puesto)",
                  ("mannequin", 1) in spies)
            check("unknown aprobado: las 7 vistas", ("orbit", 7) in spies)
            check("unknown aprobado: el gate de escala corre", any(
                s[0] == "scale" for s in spies))
            check("unknown aprobado: use_size por defecto", any(
                s[0] == "use_size" for s in spies))
            rows = {r["prop"]: r for r in ctx["report"].rows}
            check("se usa la razon DEL REGISTRO, no la del pedido",
                  "ignored text" not in json.dumps(ctx["report"].rows))
        finally:
            motor_run.REGISTRY_PATH = saved_reg
            restore()

    # The first real client's sidecar must be valid against the live router.
    with open(os.path.join(ROOT, "recetas", "gato", "build_gato.motor.json"),
              encoding="utf-8") as fh:
        side = json.load(fh)
    expect_no_exit("build_gato.motor.json: tecnica aceptada por el router",
                   preflight_router.require_technique, "gato gris",
                   side["technique"], verbose=False)
    with open(os.path.join(ROOT, "recetas", "gato", "build_gato.py"),
              encoding="utf-8") as fh:
        gsrc = fh.read()
    reg_entries = motor_run.load_registry()
    check("el registro real carga y valida", isinstance(reg_entries, list))
    gato = [e for e in reg_entries
            if e["generator"] == "recetas/gato/build_gato.py"
            and e["subject"] == "gato gris" and e["type"] == "structure_exempt"]
    check("la exencion del gato esta en el registro, aprobada por Joan",
          len(gato) == 1 and gato[0]["approved_by"] == "Joan"
          and gato[0]["date"] == "2026-10-08")
    check("el sidecar del gato ya no se auto-exime",
          "structure" not in side and "allow_unknown" not in side)
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
                   "warrior hair", "cards_alpha", verbose=False)

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
    check("control: 'wood' (cabeza) resuelve material_procedural",
          preflight_router.route("wood").category == "material_procedural")
    check("'wood door': la cabeza es 'door' -> arquitectura, wood es modificador",
          [r.category for r in preflight_router.route_all("wood door")]
          == ["arquitectura"])
    check("control: plural 'tortugas' resuelve",
          preflight_router.route("dos tortugas").category == "quelonio")
    check("control: slug 'wood_texture' -> material (sin sufijo, cabeza al inicio)",
          preflight_router.route("wood_texture").category == "material_procedural")
    check("control: slug 'madera_oscura' resuelve por la cabeza al inicio",
          preflight_router.route("madera_oscura").category == "material_procedural")
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

    # Head-noun routing (review #5): a modifier never assigns a family.
    check("'pelo de la tortuga': la cabeza es pelo, tortuga es modificador",
          [r.category for r in preflight_router.route_all("pelo de la tortuga")]
          == ["pelo"])
    expect_no_exit("... asi que una tecnica de tortuga no frena un sujeto pelo",
                   preflight_router.require_technique, "pelo de la tortuga",
                   "uv_sphere_painted", verbose=False)
    for subj in ("robot WALL-E", "astrolabio con cat", "astrolabio de piedra",
                 "cat tree", "mice"):
        check("modificador NO asigna familia: %r queda desconocido" % subj,
              not preflight_router.route(subj).matched)
        expect_exit("... y require_technique frena (%r)" % subj,
                    preflight_router.require_technique, subj, "x",
                    verbose=False)
    # Review A: a pre-modifier must not win over the head noun.
    for subj in ("rock golem", "stone golem", "golem de piedra", "golem with a rock",
                 "mossy stone golem"):
        check("%r -> construct (la cabeza es golem, no la piedra)" % subj,
              [r.category for r in preflight_router.route_all(subj)] == ["construct"])
    check("'wood door' -> arquitectura (modificador material no gana)",
          [r.category for r in preflight_router.route_all("wood door")]
          == ["arquitectura"])
    check("'gato gris' -> mamifero",
          [r.category for r in preflight_router.route_all("gato gris")]
          == ["mamifero"])
    check("'cat tree' es ambiguo (criatura + objeto) -> desconocido, no bioma",
          not preflight_router.route("cat tree").matched)
    check("control: 'cat hair' -> pelo (criatura como modificador de pelo si vale)",
          preflight_router.route("cat hair").category == "pelo")
    # Review B: the Dungeon Party mobs have a family.
    for subj, fam in (("golem", "construct"), ("king_slime", "blob"),
                      ("slime", "blob"), ("babosa", "blob"), ("limo", "blob"),
                      ("wasp", "artropodo"), ("avispa", "artropodo"),
                      ("snake", "serpiente"), ("serpiente", "serpiente"),
                      ("bird", "ave"), ("pájaro", "ave"), ("hawk", "ave"),
                      ("cuervo", "ave"), ("roedor", "mamifero"),
                      ("rata gris", "mamifero")):
        check("%r -> %s" % (subj, fam), preflight_router.route(subj).category == fam,
              str(preflight_router.route(subj).category))
    check("irregular 'wolves' -> mamifero",
          preflight_router.route("wolves").category == "mamifero")
    check("irregular 'mice' es desconocido A PROPOSITO (no hay alias raton)",
          not preflight_router.route("mice").matched)
    check("control: 'roca del bosque' -> bioma por la cabeza roca",
          preflight_router.route("roca del bosque").category == "bioma")
    check("control: 'the grey cat' -> mamifero (cabeza al final, ingles)",
          preflight_router.route("the grey cat").category == "mamifero")
    check("control: 'gato gris' -> mamifero (cabeza al inicio, espanol)",
          preflight_router.route("gato gris").category == "mamifero")
    check("control: alias de dos palabras 'hanging line' -> prop",
          preflight_router.route("old hanging line").category == "prop")



def test_mesh_and_gltf_pure():
    print("\nmesh_quality.judge / gltf_check (no Blender)")
    from recetas import mesh_quality, gltf_check
    clean = {"nonmanifold_edges": 0, "degenerate_faces": 0, "inconsistent_edges": 0,
             "inward_closed": False, "signed_volume": 1.0, "tris_total": 12,
             "uv": {"has_uv": False, "overlap": None}}
    rep = mesh_quality.judge(clean, {})
    check("judge: malla limpia -> sin FAIL ni NOT_TESTED", rep.is_complete(),
          rep.render())
    for key, bad in (("nonmanifold_edges", 2), ("degenerate_faces", 1),
                     ("inconsistent_edges", 4)):
        m = dict(clean, **{key: bad})
        check("judge: %s=%d -> FAIL" % (key, bad),
              mesh_quality.judge(m, {}).verdict() == FAIL)
    check("judge: normales hacia adentro -> FAIL",
          mesh_quality.judge(dict(clean, inward_closed=True, signed_volume=-1.0),
                             {}).verdict() == FAIL)
    check("judge: familia que exige UV y malla sin UV -> FAIL",
          mesh_quality.judge(clean, {"needs_uv": True}).verdict() == FAIL)
    check("judge: UV con 50 % de solapamiento -> FAIL",
          mesh_quality.judge(dict(clean, uv={"has_uv": True, "overlap": 0.5,
                                             "tris": 4}),
                             {"needs_uv": True}).verdict() == FAIL)
    check("judge: UV con 1 % de solapamiento (limite 2 %) -> PASS",
          mesh_quality.judge(dict(clean, uv={"has_uv": True, "overlap": 0.01,
                                             "tris": 4}),
                             {"needs_uv": True}).verdict() == PASS)
    check("judge: sin presupuesto con fuente el tri_budget es NOT_APPLICABLE",
          [r for r in mesh_quality.judge(clean, {}).rows
           if r["prop"] == "tri_budget"][0]["state"] == NOT_APPLICABLE)
    check("judge: presupuesto excedido -> FAIL",
          mesh_quality.judge(dict(clean, tris_total=9000),
                             {"max_tris": 7600}).verdict() == FAIL)
    # router -> mesh limits
    req = preflight_router.requirements("tortuga")
    check("tortuga exige UV (textura del caparazon, con fuente)",
          req["mesh"]["needs_uv"] is True)
    check("slime: presupuesto de tris con fuente (build_slime.py:100)",
          preflight_router.requirements("slime")["mesh"]["max_tris"] == 11000)
    check("lobo: sin presupuesto ni UV inventados",
          preflight_router.requirements("lobo")["mesh"]["max_tris"] is None
          and preflight_router.requirements("lobo")["mesh"]["needs_uv"] is False)
    for name, d in router_knowledge.CATEGORIES.items():
        mesh = d.get("mesh")
        if mesh:
            check("%s: la clave mesh cita una fuente que resuelve" % name,
                  resolve_pointer(mesh["source"])[0] == "ok"
                  and "basis" in mesh, str(mesh))
    check("MESH_DEFAULT cita una fuente que resuelve",
          resolve_pointer(router_knowledge.MESH_DEFAULT["source"])[0] == "ok")
    # gltf_check judge + loud failure when the validator cannot run
    state, _ = gltf_check.judge({"file": "a.glb", "numErrors": 0, "numWarnings": 3,
                                 "numInfos": 0, "version": "x"})
    check("gltf judge: 0 errores -> PASS", state == PASS)
    state, detail = gltf_check.judge({"file": "a.glb", "numErrors": 2,
                                      "numWarnings": 0, "numInfos": 0,
                                      "version": "x", "errors": ["E1", "E2"]})
    check("gltf judge: 2 errores -> FAIL con el primero a la vista",
          state == FAIL and "E1" in detail)
    state, detail = gltf_check.judge({"error": "validator not installed"})
    check("gltf judge: validador ausente -> FAIL, nunca PASS",
          state == FAIL and "not installed" in detail)
    with tempfile.TemporaryDirectory() as tmp:
        junk = os.path.join(tmp, "j.glb")
        open(junk, "wb").write(b"glTF" + b"\0" * 20)
        old = os.environ.get("MOTOR_GLTF_VALIDATOR_DIR")
        os.environ["MOTOR_GLTF_VALIDATOR_DIR"] = os.path.join(tmp, "nope")
        try:
            res = gltf_check.validate(junk)
        finally:
            if old is None:
                del os.environ["MOTOR_GLTF_VALIDATOR_DIR"]
            else:
                os.environ["MOTOR_GLTF_VALIDATOR_DIR"] = old
        check("validate: modulo ausente -> 'validator not installed' + comando",
              "validator not installed" in res.get("error", "")
              and "npm install" in res["error"], str(res))
        check("validate: sin node en PATH tambien falla ruidoso",
              "validator not installed" in gltf_check.validate(
                  junk, node="/nonexistent/node").get("error", ""))
        res = gltf_check.validate(junk)
        check("validate: un GLB basura lo rechaza el validador real",
              gltf_check.judge(res)[0] == FAIL, str(res))


def test_rubric():
    print("\nrubric.py / score_rubric.py")
    from recetas import rubric as R
    import score_rubric as CLI

    rules = preflight_router.route_all("tortuga")
    req = preflight_router.requirements("tortuga")
    rows = motor_run._structure_rows(rules)
    rub = R.build_rubric("tortuga", rules, req, rows)
    check("las 5 dimensiones GPTEval3D/3DGen-Bench empiezan PENDING (sin score)",
          list(rub["dimensions"]) == ["plausibility_3d", "geometry_detail",
                                      "texture_quality",
                                      "geometry_texture_coherence",
                                      "prompt_fidelity"]
          and all(d["score"] is None for d in rub["dimensions"].values())
          and rub["status"] == "PENDING")
    qs = rub["questions"]
    check("hay preguntas derivadas del router y TODAS citan su campo",
          len(qs) >= 10 and all(q["source"].startswith("router:") for q in qs))
    check("los ids de pregunta son unicos",
          len({q["id"] for q in qs}) == len(qs))
    check("preguntas de estructura salen de las filas del spec (6 partes)",
          len([q for q in qs if "structure_spec#" in q["source"]]) == 6)
    check("una pregunta por tecnica descartada de la familia",
          len([q for q in qs if q["source"].startswith("router:quelonio.discarded")])
          == len(router_knowledge.CATEGORIES["quelonio"]["discarded"]))
    check("las vistas ingratas tienen su pregunta (perfil, bajo, cenital, atras)",
          all(any("required_views[%s]" % v in q["source"] for q in qs)
              for v in ("perfil", "bajo", "cenital", "atras")))
    check("el hueco declarado (tail) se pregunta",
          any("tail" in q["text"] and q["source"].endswith(".gaps") for q in qs))
    unk = R.build_rubric("astrolabio", [], preflight_router.requirements("astrolabio"))
    check("sujeto sin familia: pregunta de reconocimiento con fuente router:unknown",
          unk["questions"][0]["source"] == "router:unknown")

    with tempfile.TemporaryDirectory() as tmp:
        ev = os.path.join(tmp, "a.png")
        open(ev, "wb").write(b"x")

        def doc(**kw):
            d = {"verdict": "PASS", "gaps": [], "evidence": [ev],
                 "evidence_sha256": {ev: R.sha256_file(ev)},
                 "rubric": R.build_rubric("tortuga", rules, req, rows)}
            d.update(kw)
            d["status"] = R.overall_status(d)
            return d

        d = doc()
        check("gates PASS + rubric PENDING -> EVIDENCE_READY, jamas PASS",
              d["status"] == "EVIDENCE_READY")
        d["status"] = "PASS"          # tampered field must not matter
        check("control: overall_status recalcula, no confia en el campo 'status'",
              R.overall_status(d) == "EVIDENCE_READY")
        check("verdict sin bloque rubric -> EVIDENCE_READY (no PASS)",
              R.overall_status({"verdict": "PASS"}) == "EVIDENCE_READY")
        check("gates FAIL domina todo",
              R.overall_status(dict(doc(), verdict="FAIL")) == "FAIL")

        # Review 3 #1(a): the reviewer's exact repro. A NOT_TESTED gate verdict
        # used to be scoreable to PASS_WITH_GAPS with rc 0.
        for gv in ("NOT_TESTED", "FAIL", "", "WHATEVER"):
            check("overall_status con gates %r -> FAIL (nunca puntuable)" % gv,
                  R.overall_status(dict(doc(), verdict=gv)) == "FAIL")
        check("overall_status sin clave verdict -> FAIL",
              R.overall_status({"rubric": doc()["rubric"], "evidence": [ev]}) == "FAIL")

        def full(d, score=4, ans="yes"):
            sc = {k: (score, "ok" if score < 3 else "") for k in d["rubric"]["dimensions"]}
            an = {q["id"]: (ans, "n" if ans != "yes" else "") for q in d["rubric"]["questions"]}
            return sc, an

        d = doc()
        sc, an = full(d)
        st = R.apply_review(d, "Joan", sc, an)
        check("todo completo y bueno -> PASS", st == "PASS" and d["rubric"]["status"] == "PASS")
        check("... con revisor y fecha registrados",
              d["rubric"]["reviewer"] == "Joan" and d["rubric"]["date"])
        d = doc(gaps=["a gap"])
        sc, an = full(d)
        check("completo y bueno CON huecos -> PASS_WITH_GAPS",
              R.apply_review(d, "Joan", sc, an) == "PASS_WITH_GAPS")
        d = doc()
        sc, an = full(d)
        sc["texture_quality"] = (2, "costuras visibles en el vientre")
        check("un score < 3 (con nota) -> FAIL", R.apply_review(d, "Joan", sc, an) == "FAIL")
        d = doc()
        sc, an = full(d)
        qid = d["rubric"]["questions"][0]["id"]
        an[qid] = ("no", "la cola flota")
        check("una respuesta 'no' -> FAIL", R.apply_review(d, "Joan", sc, an) == "FAIL")
        d = doc()
        sc, an = full(d)
        del an[qid]
        check("una pregunta sin responder -> sigue EVIDENCE_READY",
              R.apply_review(d, "Joan", sc, an) == "EVIDENCE_READY")
        d = doc()
        sc, _an = full(d)
        check("scores sin responder preguntas -> EVIDENCE_READY",
              R.apply_review(d, "Joan", sc, {}) == "EVIDENCE_READY")
        for label, kw in (("score 6", {"scores": {"plausibility_3d": (6, "")}}),
                          ("score 0", {"scores": {"plausibility_3d": (0, "")}}),
                          ("score 2 sin nota", {"scores": {"plausibility_3d": (2, "")}}),
                          ("dimension inventada", {"scores": {"belleza": (5, "")}}),
                          ("respuesta inventada", {"answers": {"q01": ("maybe", "")}}),
                          ("'no' sin nota", {"answers": {"q01": ("no", "")}}),
                          ("pregunta inexistente", {"answers": {"q99": ("yes", "")}}),
                          ("sin revisor", {"reviewer": ""})):
            reviewer = kw.pop("reviewer", "Joan")
            try:
                R.apply_review(doc(), reviewer, kw.get("scores"), kw.get("answers"))
                check("rechaza %s" % label, False, "lo acepto")
            except R.RubricError:
                check("rechaza %s" % label, True)
        # (a)(b) apply_review refuses a non-scoreable verdict and leaves it intact.
        nt = doc(verdict="NOT_TESTED")
        before = json.dumps(nt, sort_keys=True)
        try:
            R.apply_review(nt, "Joan", *full(nt))
            check("apply_review rechaza gates NOT_TESTED (repro del revisor)", False)
        except R.RubricError as exc:
            check("apply_review rechaza gates NOT_TESTED (repro del revisor)",
                  "not scoreable" in str(exc))
        check("... y la verdad rechazada no se modifica",
              json.dumps(nt, sort_keys=True) == before and nt["status"] == "FAIL")
        # (c) hashes
        d = doc()
        open(ev, "wb").write(b"OTRA COSA")
        try:
            R.apply_review(d, "Joan", *full(d))
            check("evidencia cambiada tras el veredicto -> rechazada", False)
        except R.RubricError as exc:
            check("evidencia cambiada tras el veredicto -> rechazada",
                  "sha256 mismatch" in str(exc))
        open(ev, "wb").write(b"x")
        d = doc()
        del d["evidence_sha256"]
        try:
            R.apply_review(d, "Joan", *full(d))
            check("verdict sin evidence_sha256 -> rechazado", False)
        except R.RubricError:
            check("verdict sin evidence_sha256 -> rechazado", True)
        d = doc()
        d["evidence_sha256"][ev] = "0" * 64
        try:
            R.apply_review(d, "Joan", *full(d))
            check("hash registrado distinto -> rechazado", False)
        except R.RubricError:
            check("hash registrado distinto -> rechazado", True)
        # (e) who/when/what was reviewed
        d = doc()
        R.apply_review(d, "cualquiera", *full(d))
        check("se registran revisor, timestamp UTC y los hashes revisados",
              d["rubric"]["reviewer"] == "cualquiera"
              and "T" in d["rubric"]["reviewed_at"]
              and d["rubric"]["reviewed_sha256"] == {ev: R.sha256_file(ev)})
        # (d) na abuse
        d = doc()
        sc, an = full(d)
        an = {k: ("na", "no aplica a este sujeto en absoluto") for k in an}
        try:
            R.apply_review(d, "Joan", sc, an)
            check("TODAS las preguntas na -> rechazado", False)
        except R.RubricError as exc:
            check("TODAS las preguntas na -> rechazado", "every question" in str(exc))
        check("... y el verdict quedo intacto (sigue EVIDENCE_READY)",
              d["status"] == "EVIDENCE_READY" and d["rubric"]["reviewer"] is None)
        d = doc()
        sc, an = full(d)
        qid0 = d["rubric"]["questions"][0]["id"]
        an[qid0] = ("na", "corto")
        try:
            R.apply_review(d, "Joan", sc, an)
            check("na con nota corta -> rechazado", False)
        except R.RubricError as exc:
            check("na con nota corta -> rechazado", "at least" in str(exc))
        d = doc()
        sc, an = full(d)
        n = len(d["rubric"]["questions"])
        k = int(n * R.NA_MAX_RATIO) + 1
        for q in d["rubric"]["questions"][:k]:
            an[q["id"]] = ("na", "esta pregunta no aplica por una razon concreta")
        try:
            R.apply_review(d, "Joan", sc, an)
            check("na por encima del tope (%d/%d) -> rechazado" % (k, n), False)
        except R.RubricError as exc:
            check("na por encima del tope (%d/%d) -> rechazado" % (k, n),
                  "cap" in str(exc))
        d = doc()
        sc, an = full(d)
        an[qid0] = ("na", "esta pregunta no aplica por una razon concreta")
        check("control: UN na con nota suficiente (bajo el tope) se acepta",
              R.apply_review(d, "Joan", sc, an) == "PASS")
        gone = doc()
        gsc, gan = full(gone)
        os.remove(ev)
        try:
            R.apply_review(gone, "Joan", gsc, gan)
            check("rechaza juzgar evidencia que ya no existe", False)
        except R.RubricError:
            check("rechaza juzgar evidencia que ya no existe", True)

        # CLI end to end, batch mode.
        open(ev, "wb").write(b"x")
        d = doc()
        path = os.path.join(tmp, "motor_verdict.json")
        json.dump(d, open(path, "w"))
        argv = [path, "--reviewer", "Joan"]
        for k in d["rubric"]["dimensions"]:
            argv += ["--score", "%s=4" % k]
        for q in d["rubric"]["questions"][:-1]:
            argv += ["--answer", "%s=yes" % q["id"]]
        CLI.main(argv)
        after = json.load(open(path))
        check("CLI: faltando UNA respuesta el estado sigue EVIDENCE_READY",
              after["status"] == "EVIDENCE_READY")
        last = d["rubric"]["questions"][-1]["id"]
        CLI.main([path, "--reviewer", "Joan", "--answer", "%s=yes" % last])
        after = json.load(open(path))
        check("CLI: al completar todo pasa a PASS", after["status"] == "PASS"
              and after["rubric"]["reviewer"] == "Joan")
        try:
            CLI.main([path, "--reviewer", "Joan", "--score", "plausibility_3d=1"])
            check("CLI: score 1 sin nota se rechaza", False)
        except SystemExit as exc:
            check("CLI: score 1 sin nota se rechaza", "needs a note" in str(exc))

    src = open(os.path.join(ROOT, "motor_run.py"), encoding="utf-8").read()
    check("motor_run.run construye el rubric (no se puede omitir)",
          "rubric.build_rubric" in _calls_by_function(src)["run"])
    check("control: detecta build_rubric removido",
          "rubric.build_rubric" not in _calls_by_function(
              src.replace("rubric.build_rubric(", "print("))["run"])
    check("no hay llamadas a APIs externas de IA en el rubric ni en la CLI",
          not any(w in open(os.path.join(ROOT, f), encoding="utf-8").read().lower()
                  for f in ("recetas/rubric.py", "tools/score_rubric.py")
                  for w in ("anthropic", "openai", "urllib.request", "requests.",
                            "http://", "https://api")))


def test_physics_pure():
    print("\nphysics.py (pure geometry + judge, no Blender)")
    from recetas import physics as PH
    sq = [(0, 0), (1, 0), (1, 1), (0, 1), (0.5, 0.5), (0.2, 0.8)]
    hull = PH.convex_hull_2d(sq)
    check("hull: las 4 esquinas, interior descartado",
          sorted(hull) == [(0, 0), (0, 1), (1, 0), (1, 1)], str(hull))
    check("hull: area de un cuadrado unidad = 1", abs(PH.hull_area(hull) - 1) < 1e-9)
    check("hull: puntos colineales -> sin area",
          PH.hull_area(PH.convex_hull_2d([(0, 0), (1, 1), (2, 2)])) == 0.0)
    check("hull: un solo punto", PH.convex_hull_2d([(3, 3)]) == [(3, 3)])
    check("margen: centro del cuadrado = +0.5",
          abs(PH.inside_margin((0.5, 0.5), hull) - 0.5) < 1e-9)
    check("margen: punto fuera = negativo", PH.inside_margin((2.0, 0.5), hull) < 0
          and abs(PH.inside_margin((2.0, 0.5), hull) + 1.0) < 1e-9)
    check("margen: en el borde ~ 0", abs(PH.inside_margin((0.5, 0.0), hull)) < 1e-9)
    check("margen: hull de un punto (cono sobre la punta) -> negativo, nunca dentro",
          PH.inside_margin((0.0, 0.0), [(0.0, 0.0)]) <= 0.0
          and PH.inside_margin((0.3, 0.0), [(0.0, 0.0)]) < 0)
    check("margen: segmento (2 apoyos alineados) no tiene interior",
          PH.inside_margin((0.5, 0.0), [(0, 0), (1, 0)]) <= 0.0)
    check("angulo: vertical vs inclinado 90 deg",
          abs(PH.angle_deg((0, 0, 1), (1, 0, 0)) - 90) < 1e-9
          and PH.angle_deg((0, 0, 1), (0, 0, 2)) < 1e-6)

    cfg = dict(router_knowledge.PHYSICS_DEFAULT)
    good = {"ground_gap_m": 0.0, "support_margin_m": 0.3, "support_contacts": 8,
            "drop": {"tilt_deg": 1.0, "drift_m": 0.01, "rest_min_z": 0.0, "frames": 60},
            "islands": {"count": 0}, "interpenetration": {"pairs": 0, "triangle_pairs": 0}}
    rep = PH.judge(good, cfg)
    check("judge: asset estable -> completo y PASS", rep.is_complete()
          and rep.verdict() == PASS, rep.render())
    for label, mod in (
            ("flotando", {"ground_gap_m": 0.5}), ("hundido", {"ground_gap_m": -0.5}),
            ("COM fuera", {"support_margin_m": -0.1}),
            ("vuelca", {"drop": {"tilt_deg": 40.0, "drift_m": 0.0, "rest_min_z": 0, "frames": 60}}),
            ("deriva", {"drop": {"tilt_deg": 0.0, "drift_m": 2.0, "rest_min_z": 0, "frames": 60}}),
            ("sin medir el suelo", {"ground_gap_m": None})):
        check("judge: %s -> FAIL" % label,
              PH.judge(dict(good, **mod), cfg).verdict() == FAIL)
    isl = dict(good, islands={"count": 2, "details": ["a", "b"]})
    check("judge: islas con politica fail -> FAIL",
          PH.judge(isl, dict(cfg, islands="fail")).verdict() == FAIL)
    check("judge: islas con politica report -> PASS (se informa)",
          PH.judge(isl, dict(cfg, islands="report")).verdict() == PASS)
    check("judge: islas con politica skip -> NOT_APPLICABLE",
          [r for r in PH.judge(isl, dict(cfg, islands="skip")).rows
           if r["prop"] == "floating_islands"][0]["state"] == NOT_APPLICABLE)
    ip = dict(good, interpenetration={"pairs": 3, "triangle_pairs": 40})
    check("judge: interpenetracion con politica fail -> FAIL",
          PH.judge(ip, dict(cfg, interpenetration="fail")).verdict() == FAIL)
    fly = dict(cfg, stands=False, drop_test=False, reason="hovers")
    rep = PH.judge({"islands": {"count": 0}, "interpenetration": {"pairs": 0,
                                                                 "triangle_pairs": 0}}, fly)
    check("judge: volador (stands/drop False) -> sin medir suelo, completo",
          rep.is_complete() and any(r["prop"] == "ground_contact"
                                    and r["state"] == NOT_APPLICABLE for r in rep.rows),
          rep.render())
    capped = dict(good, islands={"count": 0, "skipped_reason": "N parts > cap (declared gap)"})
    check("judge: analisis omitido por tope -> NOT_APPLICABLE con razon, no PASS mudo",
          [r for r in PH.judge(capped, dict(cfg, islands="fail")).rows
           if r["prop"] == "floating_islands"][0]["state"] == NOT_APPLICABLE)

    # router policy schema
    for name, d in router_knowledge.CATEGORIES.items():
        p = dict(router_knowledge.PHYSICS_DEFAULT)
        p.update(d.get("physics") or {})
        check("%s: physics trae politica valida" % name,
              d.get("physics") and p["islands"] in ("fail", "report", "skip")
              and p["interpenetration"] in ("fail", "report", "skip")
              and isinstance(p["stands"], bool) and isinstance(p["drop_test"], bool))
        check("%s: physics cita razon o basis 'initial'" % name,
              (d["physics"].get("reason") or "initial" in d["physics"].get("basis", ""))
              and (not d["physics"].get("reason") or d["physics"].get("source")),
              str(d["physics"]))
        src = d["physics"].get("source")
        if src:
            check("%s: la fuente de physics resuelve" % name,
                  resolve_pointer(src)[0] == "ok", src)
    check("PHYSICS_DEFAULT cita fuente que resuelve y declara basis initial",
          resolve_pointer(router_knowledge.PHYSICS_DEFAULT["source"])[0] == "ok"
          and "initial" in router_knowledge.PHYSICS_DEFAULT["basis"])
    rq = preflight_router.requirements
    check("voladores (avispa, ave) NO se paran ni se dejan caer",
          not rq("avispa")["physics"]["stands"] and not rq("pajaro")["physics"]["stands"]
          and not rq("avispa")["physics"]["drop_test"])
    check("golem/mamifero/prop se paran y se dejan caer",
          all(rq(x)["physics"]["stands"] and rq(x)["physics"]["drop_test"]
              for x in ("golem", "gato", "carro")))
    check("slime se para pero no se deja caer (el squash es de Godot)",
          rq("slime")["physics"]["stands"] and not rq("slime")["physics"]["drop_test"])
    check("construct: sin interpenetracion (piedras embebidas por diseno)",
          rq("golem")["physics"]["interpenetration"] == "skip")
    check("sujeto desconocido -> politica por defecto (estricta en lo que mide)",
          rq("astrolabio")["physics"]["stands"] and rq("astrolabio")["physics"]["drop_test"])
    check("pelo: ni islas ni interpenetracion (las cards se solapan a proposito)",
          rq("pelo")["physics"]["islands"] == "skip"
          and rq("pelo")["physics"]["interpenetration"] == "skip")
    check("el rubric deriva la pregunta de apoyo desde physics.stands",
          any(q["source"].endswith(".physics.stands")
              for q in rubric_mod.build_rubric(
                  "gato", preflight_router.route_all("gato"),
                  rq("gato"))["questions"]))


def test_size_sources_strength():
    print("\nsize_ranges: explicit vs weak sources")
    n_weak = 0
    for name, d in router_knowledge.CATEGORIES.items():
        for sr in d.get("size_ranges", []):
            m = re.match(r"^(?:(game|gameart|gametools|memory):)?([^:#|]+):(\d+)(?:-(\d+))?\|(.+)$",
                         sr["source"])
            kind, rel, a, b, anchor = m.groups()
            base = {None: ROOT, "game": GAME_REFS, "gameart": GAME_ART,
                    "gametools": GAME_TOOLS, "memory": MEMORY}[kind]
            lines = open(os.path.join(base, rel), encoding="utf-8").read().splitlines()
            cited = [l for l in lines[int(a) - 1:int(b or a)] if anchor in l]
            is_table_row = bool(cited) and cited[0].lstrip().startswith("|")
            label = "%s/%s" % (name, sr["aliases"][0])
            if sr.get("weak"):
                n_weak += 1
                check("%s: fuente DEBIL declarada, con basis que lo explica" % label,
                      "WEAK" in sr["basis"] and not is_table_row)
            else:
                check("%s: fuente explicita = fila de una tabla de medidas" % label,
                      is_table_row, str(cited[:1]))
    check("control: el golem (mencion al pasar) esta marcado weak",
          preflight_router.requirements("golem")["size_range"]["weak"] is True)
    check("control: el lobo (tabla de medidas) NO es weak",
          preflight_router.requirements("lobo")["size_range"]["weak"] is False)
    check("hay al menos una fuente debil registrada y el detector la ve", n_weak >= 1)
    check("el hueco del golem dice que el chequeo solo avisa",
          any("only warns" in g for g in preflight_router.requirements("golem")["gaps"]))


def test_glb_deliverable_router():
    print("\nrouter glb_deliverable")
    rq = preflight_router.requirements
    for subj in ("golem", "slime", "avispa", "serpiente", "pajaro", "export glb"):
        check("%r: el entregable es un GLB" % subj, bool(rq(subj)["glb_required"]))
    for subj in ("gato", "tortuga", "carro", "roca", "pelo"):
        check("%r: NO exige GLB (solo hueco si falta)" % subj,
              not rq(subj)["glb_required"])
    for name, d in router_knowledge.CATEGORIES.items():
        if d.get("glb_deliverable"):
            check("%s: glb_deliverable cita una fuente que resuelve" % name,
                  resolve_pointer(d["glb_deliverable"])[0] == "ok")


def test_blender_suite():
    print("\ntest_blender_gates.py (needs Blender)")
    blender = shutil.which("blender")
    if not blender:
        if os.environ.get("MOTOR_TESTS_NO_BLENDER") == "1":
            print("  SKIPPED explicitly (MOTOR_TESTS_NO_BLENDER=1): the Blender "
                  "gate fixtures did NOT run")
            return
        check("blender disponible para los fixtures de bpy", False,
              "blender no esta en PATH; MOTOR_TESTS_NO_BLENDER=1 lo omite A LA VISTA")
        return
    p = subprocess.run([blender, "-b", "--factory-startup", "--python-exit-code",
                        "1", "--python",
                        os.path.join(ROOT, "tools", "test_blender_gates.py")],
                       capture_output=True, text=True, timeout=600)
    seen = 0
    for line in p.stdout.splitlines():
        m = re.match(r"^  (ok  |FAIL)  (.*)$", line)
        if m:
            seen += 1
            check("[blender] " + m.group(2).split(" -- ")[0], m.group(1) == "ok  ",
                  line)
    check("la suite de Blender corrio y termino limpia (rc=0, >0 fixtures)",
          p.returncode == 0 and seen > 0, "rc=%s seen=%s %s" % (
              p.returncode, seen, p.stderr[-200:]))


def test_router_requirements():
    print("\npreflight_router.requirements()")
    check("gato -> mamifero", preflight_router.route("gato gris").category
          == "mamifero")
    check("carro de la aldea -> solo prop (aldea es modificador)",
          [r.category for r in preflight_router.route_all("carro de la aldea")]
          == ["prop"])
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
    check("lobo trae el rango de altura CON fuente", req["size_range"]
          == {"dim": "height", "range_m": (0.66, 0.84), "basis": "",
                          "weak": False})
    check("gato NO inventa rango de altura (no hay fuente)",
          preflight_router.requirements("gato")["size_range"] is None)
    req = preflight_router.requirements("golem")
    check("golem: altura con fuente (4.0 m +-20% inicial)",
          req["size_range"]["dim"] == "height"
          and req["size_range"]["range_m"] == (3.2, 4.8)
          and "initial" in req["size_range"]["basis"])
    check("cuervo: envergadura (span) con fuente",
          preflight_router.requirements("cuervo")["size_range"]["dim"] == "span")
    check("rata: largo total (span) derivado de dos rangos con fuente",
          preflight_router.requirements("rata")["size_range"]["range_m"]
          == (0.255, 0.52))
    check("slime/avispa/serpiente: SIN tamano inventado, hueco declarado",
          all(preflight_router.requirements(x)["size_range"] is None
              for x in ("slime", "avispa", "serpiente")))
    check("el hueco de king-vs-S=2.2 queda declarado en blob",
          any("S = 2.2" in g for g in
              preflight_router.requirements("king slime")["gaps"]))
    req = preflight_router.requirements("material de hormigon")
    check("material: maniqui exento con razon, sin use_size",
          not req["mannequin"] and req["mannequin_exempt"]
          and req["use_size"] is None and req["use_size_exempt"])
    req = preflight_router.requirements("tortuga")
    check("tortuga arrastra su structure_spec y sus 7 partes",
          req["structure"] and len(req["structure"][0][1]) == 7)


def test_registry_integrity():
    """Every registered technique points at a real recipe that defines its calls
    and stamps its output (cosecha-1: new recipes must not register ghosts)."""
    print("\ntechnique_registry integrity")
    import ast as _ast
    from recetas import technique_registry as TR
    for tid, spec in sorted(TR.REGISTRY.items()):
        path = os.path.join(ROOT, "recetas", spec["module"] + ".py")
        ok = os.path.isfile(path)
        src = open(path, encoding="utf-8").read() if ok else ""
        defs = {n.name for n in _ast.walk(_ast.parse(src)) if isinstance(n, _ast.FunctionDef)} if ok else set()
        check("registry %s: recetas/%s.py exists and defines %s"
              % (tid, spec["module"], "/".join(spec["calls"])),
              ok and all(c in defs for c in spec["calls"]), sorted(defs)[:8])
        check("registry %s: the recipe stamps its output (motor_stamp)" % tid,
              "_motor_stamp(" in src or "stamp_object(" in src)
    tmp = tempfile.mkdtemp()
    try:
        for tid, spec in sorted(TR.REGISTRY.items()):
            call = spec["calls"][0]
            good = os.path.join(tmp, "g_%s.py" % tid)
            bad = os.path.join(tmp, "b_%s.py" % tid)
            open(good, "w").write("from recetas.%s import %s\n%s(obj, part='p')\n" % (spec["module"], call, call))
            open(bad, "w").write("from recetas.%s import %s\n%s(obj)\n" % (spec["module"], call, call))
            check("registry %s: the AST gate accepts import+call with part=, rejects it without" % tid,
                  TR.evidence(good, tid)[0] and not TR.evidence(bad, tid)[0], TR.evidence(good, tid))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    check("control: an unknown technique is not registered", not TR.is_registered("no_such_technique_xyz"))
    check("material_procedural gap closed: no longer listed as missing",
          "material_procedural" not in TR.ROUTER_TECHNIQUES_WITHOUT_IMPLEMENTATION
          and TR.is_registered("bake_procedural_to_float_color"))


def test_probe_with_control():
    print("\nprobe_with_control (a clean reading needs a control that fired)")
    from recetas import probe_with_control as pwc
    from recetas.verdict import PASS as P, FAIL as F, NOT_TESTED as NT
    st = lambda ps: ps.report.rows[-1]["state"]
    ps = pwc.ProbeSet("t")
    ps.zero("clean+fired", 0, 7)
    check("clean subject + control fired -> PASS", st(ps) == P)
    ps.zero("clean+blind", 0, 0)
    check("clean subject + control that did NOT fire -> NOT_TESTED, never PASS", st(ps) == NT)
    check("the blind row says why", "instrument blind" in ps.report.rows[-1]["detail"])
    ps.zero("defect", 3, 9)
    check("defective subject -> FAIL", st(ps) == F)
    ps.zero("defect+blind", 3, 0)
    check("defective subject is FAIL even when the control slipped (a defect is a defect)", st(ps) == F)
    ps.row("no_control", True, "42 mm")
    check("clean subject with NO control supplied -> NOT_TESTED", st(ps) == NT)
    ps.row("no_control_bad", False, "42 mm")
    check("defective subject with no control -> FAIL", st(ps) == F)
    check("aggregate verdict of a mixed set is FAIL; a set with only PASS+NOT_TESTED is NOT_TESTED",
          ps.report.verdict() == F)
    ps2 = pwc.ProbeSet("t2")
    ps2.zero("a", 0, 5)
    ps2.zero("b", 0, 0)
    check("one blind probe keeps the whole set from passing (verdict NOT_TESTED)",
          ps2.report.verdict() == NT)
    # callable API: the SAME instrument on subject and control
    def count_inside(pts):
        return sum(1 for x in pts if x < 0)
    ps3 = pwc.ProbeSet("t3")
    ps3.probe("clear", count_inside, lambda n: n == 0, [1, 2, 3], [-1, 2, -3])
    check("probe(): clean subject, shrunken control hits 2 -> PASS", st(ps3) == P)
    ps3.probe("blind", count_inside, lambda n: n == 0, [1, 2, 3], [1, 2, 3])
    check("probe(): control identical to subject (cannot see the defect) -> NOT_TESTED", st(ps3) == NT)
    ps3.probe("dirty", count_inside, lambda n: n == 0, [-1, 2], [-1, -2])
    check("probe(): defective subject -> FAIL", st(ps3) == F)
    ps3.probe("crash", lambda x: 1 / 0, lambda n: True, [1], [1])
    check("probe(): a measure() that raises is NOT_TESTED, not a clean pass", st(ps3) == NT)
    tmp = tempfile.mkdtemp()
    try:
        j = json.load(open(ps3.to_json(os.path.join(tmp, "p.json"))))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    check("to_json keeps control_fired per row",
          [r["control_fired"] for r in j["rows"]][:2] == [True, False] and j["verdict"] == F)
    # truth table vs the original rem_v8_measure.row(): same ok flag, PASS only with a fired control
    for ok in (True, False):
        for fired in (True, False, None):
            q = pwc.ProbeSet("tt")
            q.row("x", ok, "", control_fired=fired)
            want = F if not ok else (P if fired else NT)
            check("truth table ok=%s control_fired=%s -> %s" % (ok, fired, want), st(q) == want)


def test_bake_shading_pure():
    print("\nbake_shading_check (pure judge)")
    import random as _r
    from recetas import bake_shading_check as bsc
    from recetas.verdict import PASS as P, FAIL as F, NOT_TESTED as NT
    rs = _r.Random(2)
    xs = [rs.random() for _ in range(400)]
    painted = [0.8 - 0.6 * x + 0.02 * rs.random() for x in xs]        # shadow painted where occluded
    stains = [0.5 + 0.1 * rs.random() for _ in xs]                    # position noise, uncorrelated
    st = lambda ys: bsc.judge(xs, ys)[0].report.rows[-1]["state"]
    check("known-FAIL: luma = 0.8 - 0.6 * occlusion (baked shadow) -> FAIL", st(painted) == F)
    check("known-PASS: uncorrelated stains -> PASS (control fired)", st(stains) == P)
    check("flat colour (no luma variance) -> NOT_TESTED, not PASS", st([0.5] * len(xs)) == NT)
    flat_occ = bsc.judge([0.0] * 400, stains)[0].report.rows[-1]["state"]
    check("blind instrument: occlusion all zero (rays never hit anything) -> NOT_TESTED, not PASS", flat_occ == NT)
    check("too few samples (10) -> NOT_TESTED", bsc.judge(xs[:10], stains[:10])[0].report.rows[-1]["state"] == NT)
    r, rc = bsc.judge(xs, stains)[1:]
    check("the in-gate control reads strongly negative (r_ctrl = %.3f) while stains read ~0 (r = %.3f)" % (rc, r),
          rc < -0.9 and abs(r) < 0.15)
    check("pearson: perfect line = 1, constant = None",
          abs(bsc.pearson([1, 2, 3], [2, 4, 6]) - 1) < 1e-9 and bsc.pearson([1, 1, 1], [1, 2, 3]) is None)


def test_harvest_gate():
    print("\nharvest gate (recetas/harvest.py + start_asset + harvest_asset)")
    from recetas import harvest as H
    tmp = tempfile.mkdtemp()
    src = os.path.join(tmp, "gen.py")
    open(src, "w").write("\n".join("line %d" % i for i in range(1, 41)) + "\n")   # 40 lines
    good = {"source": "gen.py:12-20", "why": "decal rides the final surface normals", "status": "proposed"}
    ok = lambda sec: H.validate(sec, tmp)[0]
    try:
        check("harvest: missing section -> FAIL", not ok(None))
        check("harvest: template written by start_asset (entries [], none '') -> FAIL (empty)", not ok(H.empty_section()))
        check("harvest: {} -> FAIL", not ok({}))
        check("harvest: entries [] and no none -> FAIL", not ok({"entries": []}))
        check("harvest: `none: true` without a reason -> FAIL", not ok({"none": True}))
        check("harvest: none with a real reason -> PASS",
              ok({"none": "built only from existing recipes (bvh_glue, paint_por_geometria); nothing new surfaced"}))
        check("harvest control: none with a placeholder ('n/a') -> FAIL", not ok({"none": "n/a"}))
        check("harvest control: none with a too-short reason -> FAIL", not ok({"none": "nothing new"}))
        check("harvest: one valid entry (proposed) -> PASS", ok({"entries": [good]}))
        check("harvest: promoted entry with a registered technique -> PASS",
              ok({"entries": [dict(good, status="promoted", technique="surface_decal")]}))
        check("harvest control: promoted but technique NOT in the registry -> FAIL",
              not ok({"entries": [dict(good, status="promoted", technique="made_up_technique")]}))
        check("harvest control: promoted without a technique -> FAIL",
              not ok({"entries": [dict(good, status="promoted")]}))
        check("harvest control: entries AND none together -> FAIL",
              not ok({"entries": [good], "none": "a perfectly long reason for nothing"}))
        check("harvest control: source file that does not exist -> FAIL",
              not ok({"entries": [dict(good, source="no_such_file.py:3")]}))
        check("harvest control: line beyond the end of the file (41 of 40) -> FAIL",
              not ok({"entries": [dict(good, source="gen.py:41")]}))
        check("harvest control: source without a line -> FAIL", not ok({"entries": [dict(good, source="gen.py")]}))
        check("harvest control: empty why -> FAIL", not ok({"entries": [dict(good, why="")]}))
        check("harvest control: one-word why -> FAIL", not ok({"entries": [dict(good, why="useful")]}))
        check("harvest control: status outside promoted/proposed -> FAIL",
              not ok({"entries": [dict(good, status="maybe")]}))
        check("harvest control: one bad entry among good ones -> FAIL",
              not ok({"entries": [good, dict(good, source="gen.py:999")]}))
        check("harvest: a section that is not an object -> FAIL", not ok(["gen.py:3"]))

        # CLI + start_asset round trip
        env = dict(os.environ, MOTOR_GATE_STATE_DIR=tmp)
        adir = os.path.join(tmp, "asset")
        os.makedirs(adir)
        open(os.path.join(adir, "gen.py"), "w").write("\n".join("l%d" % i for i in range(1, 30)) + "\n")
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "start_asset.py"), adir, "gato",
                            "--technique", "body=paint_por_geometria", "--generator", "gen.py",
                            "--output", "a.blend"], capture_output=True, text=True, env=env)
        man = os.path.join(adir, "_motor", "manifest.json")
        doc = json.load(open(man))
        check("start_asset: writes an EMPTY harvest template (so the gate fails until filled)",
              r.returncode == 0 and doc.get("harvest") == {"entries": [], "none": ""}, r.stderr[-300:])
        check("start_asset: the printed instructions mention the harvest step", "HARVEST" in r.stdout)
        hcli = [sys.executable, os.path.join(ROOT, "tools", "harvest_asset.py"), man]
        r = subprocess.run(hcli + ["--add", "gen.py:30", "decal rides the final surface normals"], capture_output=True, text=True)
        check("harvest_asset: an out-of-range citation is REFUSED and the manifest is untouched",
              r.returncode == 1 and json.load(open(man))["harvest"] == {"entries": [], "none": ""})
        r = subprocess.run(hcli + ["--add", "gen.py:10-14", "decal rides the final surface normals",
                                   "--status", "promoted", "--technique", "surface_decal"], capture_output=True, text=True)
        check("harvest_asset: a valid entry is saved", r.returncode == 0 and len(json.load(open(man))["harvest"]["entries"]) == 1, r.stdout)
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "start_asset.py"), adir, "gato",
                            "--technique", "body=paint_por_geometria", "--generator", "gen.py",
                            "--output", "a.blend"], capture_output=True, text=True, env=env)
        check("start_asset: re-running it does NOT wipe an already recorded harvest",
              r.returncode == 0 and len(json.load(open(man))["harvest"]["entries"]) == 1)
        r = subprocess.run(hcli + ["--none", "x"], capture_output=True, text=True)
        check("harvest_asset: a trivial --none reason is REFUSED", r.returncode == 1)
        r = subprocess.run(hcli + ["--none", "reused only existing recipes; no new technique appeared"], capture_output=True, text=True)
        d2 = json.load(open(man))["harvest"]
        check("harvest_asset: --none with a reason replaces the entries (never both)",
              r.returncode == 0 and d2["entries"] == [] and d2["none"].startswith("reused"))
        check("harvest_asset --show: valid section exits 0",
              subprocess.run(hcli + ["--show"], capture_output=True, text=True).returncode == 0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


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
    test_mesh_and_gltf_pure()
    test_physics_pure()
    test_glb_deliverable_router()
    test_size_sources_strength()
    test_motor_run()
    test_rubric()
    test_registry_integrity()
    test_probe_with_control()
    test_bake_shading_pure()
    test_harvest_gate()
    test_blender_suite()

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
