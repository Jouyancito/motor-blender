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


def main():
    print("FIXTURES ADVERSARIALES -- cada gate contra un caso que DEBE fallar")
    test_verdict()
    test_asset_spec()
    test_asset_spec_corpus_shapes()
    test_material_swatch()
    test_scale_ref_and_views()
    test_router()

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
