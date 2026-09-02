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


def main():
    print("FIXTURES ADVERSARIALES -- cada gate contra un caso que DEBE fallar")
    test_verdict()
    test_asset_spec()
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
