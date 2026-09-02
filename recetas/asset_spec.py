# asset_spec.py -- make preflight point 4d executable.
#
# WHY THIS EXISTS (2026-09-02, external review)
#
# CLAUDE.md already says it, in the preflight that loads by itself:
#
#     4d. PARAMETROS ... DOS mitades, las dos obligatorias:
#         MEDIDA ....... cuanto mide, cuantos hay, a que velocidad
#         ESTRUCTURA ... por cada parte movil: que PLANO ocupa, que ANGULO
#                        tiene respecto del cuerpo, y que la LIMITA
#         Parte sin renglon estructural = NO se modela, se investiga primero.
#
# And nothing enforces it. It is prose in a checklist the agent writes into its
# own reply. Four independent reviewers converged on the same contraexample --
# the turtle hit every MEASURE parameter (carapace 0.845 m, ratio in band, 5
# scutes, 0.54 m/s) and did not read as a turtle, because not one parameter was
# STRUCTURAL. That was never a verification failure: there was nothing to
# verify. The specification was incomplete.
#
# Measured in the repo the day this was written:
#
#     84 reference folders
#     83 _synthesis.md
#      3 _motion_spec.md
#      0 structural specs
#
# So the artefact does not need inventing -- it needs to become mandatory, and
# to fail the build when a moving part has no structural row.
#
# THE GENERATOR DECLARES ITS MOVING PARTS. That is the load-bearing idea: the
# build script is the one thing that knows what it is about to construct, so it
# is the one thing that can be held to having researched it. A part the
# generator builds but the spec does not describe is a part nobody researched.
#
# USAGE
#     from recetas.asset_spec import require_structure
#
#     require_structure(
#         "game/docs/art/_references/turtle",
#         moving_parts=["humerus_L", "humerus_R", "forearm_L", "forearm_R",
#                       "neck", "head", "tail"],
#     )      # SystemExit listing exactly which parts have no researched row
#
# SPEC FORMAT (markdown, hand-writable, lives beside _synthesis.md)
#
#     ## STRUCTURE
#
#     | Parte | Plano | Angulo | Limite |
#     |---|---|---|---|
#     | humerus_L | horizontal | 0 deg vs suelo | queda FUERA del caparazon |
#     | forearm_L | vertical | 90 deg vs humero | no cruza la linea media |
#
# Every cell must carry content. An empty cell is an unanswered question, and
# an unanswered question is what produced four legs pointing the same way.

import os
import re

from recetas.verdict import Report, PASS, FAIL, NOT_TESTED

SPEC_BASENAMES = ("_structure_spec.md", "_spec.md", "_motion_spec.md")
REQUIRED_COLUMNS = ("plano", "angulo", "limite")

# Accent-insensitive: Joan writes "Ángulo"/"Límite", ASCII creeps in from tools.
_FOLD = str.maketrans("áéíóúÁÉÍÓÚñÑ", "aeiouAEIOUnN")


def _fold(text):
    return text.translate(_FOLD).strip().lower()


def find_spec(ref_dir):
    """Return the first spec file found under `ref_dir`, or None."""
    if not os.path.isdir(ref_dir):
        return None
    for root, _dirs, files in os.walk(ref_dir):
        for base in SPEC_BASENAMES:
            if base in files:
                return os.path.join(root, base)
    return None


def parse_structure(spec_path):
    """
    Pull the STRUCTURE table out of a markdown spec.

    Returns {part_name_folded: {"plano": str, "angulo": str, "limite": str,
                                "raw": original_part_name}}.
    Missing section or malformed table yields {} -- the caller treats that as
    NOT_TESTED, never as a pass.
    """
    if not spec_path or not os.path.exists(spec_path):
        return {}

    with open(spec_path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()

    # Locate "## STRUCTURE" (or ESTRUCTURA) and read until the next heading.
    start = None
    for i, line in enumerate(lines):
        if line.startswith("#") and _fold(line).lstrip("# ").startswith(
                ("structure", "estructura")):
            start = i + 1
            break
    if start is None:
        return {}

    rows = {}
    header_seen = False
    for line in lines[start:]:
        if line.startswith("#"):
            break
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        folded = _fold(cells[0])
        # Skip the header row and the |---|---| separator.
        if not header_seen and folded in ("parte", "part", "pieza"):
            header_seen = True
            continue
        if set(cells[0].replace(" ", "")) <= set("-:"):
            continue
        rows[folded] = {"raw": cells[0], "plano": cells[1],
                        "angulo": cells[2], "limite": cells[3]}
    return rows


def check_structure(ref_dir, moving_parts):
    """
    Build a Report: one row per moving part the generator declares.

    PASS        the part has a row and all three cells carry content
    FAIL        the part has a row with an empty cell (asked, unanswered)
    NOT_TESTED  the part has no row at all (never researched)
    """
    spec_path = find_spec(ref_dir)
    table = parse_structure(spec_path)
    subject = "STRUCTURE %s" % os.path.basename(os.path.normpath(ref_dir))
    report = Report(subject)

    if not table:
        where = spec_path or os.path.join(ref_dir, SPEC_BASENAMES[0])
        for part in moving_parts:
            report.add(part, NOT_TESTED, "sin seccion STRUCTURE en %s"
                       % os.path.relpath(where))
        return report

    for part in moving_parts:
        row = table.get(_fold(part))
        if row is None:
            report.add(part, NOT_TESTED, "no figura en la tabla STRUCTURE")
            continue
        empty = [c for c in REQUIRED_COLUMNS if not row[c]]
        if empty:
            report.add(part, FAIL, "celda(s) vacia(s): %s" % ", ".join(empty))
        else:
            report.add(part, PASS, "%s | %s | %s"
                       % (row["plano"], row["angulo"], row["limite"]))
    return report


def require_structure(ref_dir, moving_parts, verbose=True):
    """
    Fail the build unless every declared moving part has a researched row.

    This is preflight 4d as a gate instead of as prose. Run it BEFORE the first
    bpy call, so the failure costs seconds rather than a modelling pass.
    """
    report = check_structure(ref_dir, moving_parts)
    if verbose:
        print(report.render())
    if report.is_complete():
        return report
    raise SystemExit(
        report.render() + "\n"
        "PREFLIGHT 4d SIN CUMPLIR.\n"
        "Una parte movil sin renglon estructural NO se modela: se investiga\n"
        "primero. Los parametros de MEDIDA salen de una ficha y siempre se\n"
        "escriben; los de ESTRUCTURA piden anatomia y son los que deciden si\n"
        "la cosa LEE. La tortuga cumplia todos los de medida.\n\n"
        "Escribi la tabla en %s:\n\n"
        "  ## STRUCTURE\n\n"
        "  | Parte | Plano | Angulo | Limite |\n"
        "  |---|---|---|---|\n"
        "  | %s | ? | ? | ? |\n"
        % (os.path.join(ref_dir, SPEC_BASENAMES[0]),
           (report.untested + report.failed)[0]["prop"]))
