# biome_stem.py -- tapered-prism / card verticals for the biome packs.
#
# Blades, stalks, seed heads and spikes: the thin vertical vocabulary that sits
# on top of a lobe mass or straight on the ground.
#
# NAMING WARNING (divergence D17): grass_pack and flower_pack both used to define
# `add_blade`, but they are NOT drifted copies of one recipe -- they are two
# genuinely different recipes that happened to share a name:
#   add_blade_strip -- multi-segment curved tapered STRIP (grass), azimuth +
#                      curve_power + taper_power, colored by height fraction.
#   add_blade_card  -- 2-triangle bent CARD (flower), single bend factor.
# Extracting them under one name would silently hand one pack the other's
# geometry. They keep distinct names permanently.
import math
import bmesh
from mathutils import Vector, Matrix

from biome_vcol import lerp3


def add_blade_strip(bm, vcol, base_xy, height, width_base, width_tip, azimuth_deg,
                    bend_amount, bend_azimuth_deg, color_base, color_tip,
                    segments=4, curve_power=2.2, taper_power=1.3,
                    base_z=0.0, edge_noise=0.0, noise_seed=0,
                    break_at=None, break_droop=0.0, color_break=None):
    """ONE blade as a chain of `segments` quads growing along +Z, tapering
    width_base -> width_tip, bending laterally toward bend_azimuth_deg with an
    accelerating curve (curve_power) so it reads like a real blade arc, not a
    straight ramp. Colors each vertex by its height fraction (dark base -> light
    tip). Returns the tip-center Vector (for accent placement).

    Consumes NO rng draws -- every value arrives pre-sampled from the caller.

    M3 options, all inert at their defaults so existing callers are byte-identical:

    base_z      Lift the blade's foot. Lets a caller sit a clump on uneven ground
                (_ground_common.ground_height) instead of a flat Z=0 plate.
    edge_noise  Fraction of half-width. Wobbles the two edges INDEPENDENTLY with a
                deterministic hash of (noise_seed, u), so the silhouette stops being
                a perfect algebraic taper. This is the per-vertex surface noise the
                M3 checklist asks for, in the form a flat strip can carry.
    break_at    Arc fraction (0..1) where the blade SNAPS. Past it the blade keeps
                its length but folds over by `break_droop`, so it hangs instead of
                standing. Joan's brief, 2026-08-08: "pueden tener diferente altura,
                algunas quizas rotas".
    break_droop 0 = no fold, 1 = folded to 150 deg off vertical (hanging past
                horizontal).
    color_break Tint for the snapped section, blended in across it. A broken blade
                dries out; leaving it green reads as a modelling error, not damage.
    """
    az = math.radians(azimuth_deg)
    width_dir = Vector((math.cos(az), math.sin(az), 0.0))
    bend_rad = math.radians(bend_azimuth_deg)
    bend_dir = Vector((math.cos(bend_rad), math.sin(bend_rad), 0.0))
    bx, by = base_xy
    broken = break_at is not None and break_droop > 0.0
    fold = math.radians(150.0) * break_droop if broken else 0.0
    # Arc position of every row, kept explicitly: once a blade folds, height no
    # longer increases with u, so the z-derived gradient below would run backwards.
    u_of_vert = {}
    rows = []
    for i in range(segments + 1):
        u = i / segments
        z = height * u
        half_w = 0.5 * (width_base + (width_tip - width_base) * (u ** taper_power))
        bend = bend_amount * (u ** curve_power)
        if broken and u > break_at:
            # Everything past the break travels in a straight folded line from the
            # break point: it kept its length, it just is not upright any more.
            over = (u - break_at) * height
            z = height * break_at + over * math.cos(fold)
            bend = bend_amount * (break_at ** curve_power) + over * math.sin(fold)
        cx = bx + bend_dir.x * bend
        cy = by + bend_dir.y * bend
        wl = half_w
        wr = half_w
        if edge_noise > 0.0:
            wl *= 1.0 + edge_noise * math.sin(noise_seed * 12.9898 + u * 9.7)
            wr *= 1.0 + edge_noise * math.sin(noise_seed * 78.233 + u * 11.3 + 2.1)
        left = bm.verts.new((cx - width_dir.x * wl, cy - width_dir.y * wl, z + base_z))
        right = bm.verts.new((cx + width_dir.x * wr, cy + width_dir.y * wr, z + base_z))
        u_of_vert[left] = u
        u_of_vert[right] = u
        rows.append((left, right))
    for i in range(segments):
        a, b = rows[i]
        c, d = rows[i + 1]
        f = bm.faces.new((a, c, d, b))
        # The height fraction is re-read from the STORED vertex coordinate rather
        # than reused from the loop above: v.co is float32, so height*u rounded
        # into the mesh and then divided back out is not bit-identical to u.
        for loop in f.loops:
            if broken or base_z:
                u = u_of_vert[loop.vert]
            else:
                u = max(0.0, min(1.0, loop.vert.co.z / height)) if height > 1e-6 else 0.0
            col = lerp3(color_base, color_tip, u)
            if broken and color_break is not None and u > break_at:
                # Ramp into the dry tint across the snapped length rather than
                # switching at the crease, so the damage reads as drying, not paint.
                span = max(1.0 - break_at, 1e-6)
                col = lerp3(col, color_break, min(1.0, (u - break_at) / span))
            vcol[loop.vert] = col
    tip_left, tip_right = rows[-1]
    return (tip_left.co + tip_right.co) * 0.5


def add_seed_spike(bm, vcol, base_pos, radius, depth, color):
    """Slim tapered cone (grass/sedge seed panicle) -- reads as a plume, not a
    round berry. ~8 tris (segments=6, capped). Consumes no rng draws."""
    center = Vector((base_pos.x, base_pos.y, base_pos.z + depth * 0.5))
    res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=6,
                                radius1=radius, radius2=radius * 0.12, depth=depth,
                                matrix=Matrix.Translation(center))
    paint_verts_of_faces(res["verts"], vcol, color)


def paint_verts_of_faces(new_verts, vcol, color):
    """Flat-color every vertex touched by the faces linked to `new_verts`.

    The vertex set is derived FROM THE FACES rather than from the primitive op's
    returned vert list: cap-center verts are not guaranteed to appear in that
    list, and a missed vert would silently fall through to the finalize default
    color instead of the intended one. This mirrors exactly which loops the
    original per-face painting reached.
    """
    faces = set()
    for v in new_verts:
        for f in v.link_faces:
            faces.add(f)
    for f in faces:
        for loop in f.loops:
            vcol[loop.vert] = color
