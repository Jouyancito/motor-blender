# motor_stamp.py -- every object a motor recipe builds or modifies says so.
#
# WHY (2026-10-16): the pre-run gate proves a generator IMPORTS and CALLS the
# motor's implementation of a declared technique. It cannot prove the mesh in
# the .blend came from it. So the recipes stamp their output with two custom
# properties, and tools/verify_asset.py reads them back from the saved .blend:
#
#     motor_part       the declared part this object is (manifest `parts` key)
#     motor_technique  comma-joined technique ids that built/modified it
#
# A visible mesh with no motor_part was built outside the motor -> FAIL.
# Honest limit: anyone can call stamp_object() by hand. The stamp is evidence
# that the motor path was taken, not a cryptographic seal; the static gate and
# the registry's `custom` rule are what make hand-stamping a visible act.
#
# bpy-free on purpose: works on anything that supports item assignment.

PART_PROP = "motor_part"
TECH_PROP = "motor_technique"
SCALE_REF_PART = "_scale_ref"   # parts starting with "_" are infrastructure


def stamp_object(obj, part, technique):
    """Stamp `obj`. `part` defaults to the object's name (the verifier will
    then report the declared part as missing -- pass the real part name)."""
    if obj is None:
        return obj
    part = part or getattr(obj, "name", "") or "?"
    techs = [t for t in str(obj.get(TECH_PROP, "") or "").split(",") if t]
    if technique not in techs:
        techs.append(technique)
    obj[PART_PROP] = str(part)
    obj[TECH_PROP] = ",".join(techs)
    return obj
