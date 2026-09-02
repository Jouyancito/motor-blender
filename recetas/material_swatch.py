# material_swatch.py -- prove a material actually VARIES over the geometry it is
# applied to, before spending render passes on a defect that is not there.
#
# WHY THIS EXISTS (2026-09-01, parking arch-viz)
#
# A concrete material with formwork board-marks rendered perfectly flat. Nothing
# errored. The node graph was built, linked and valid; Blender simply has no
# opinion about a procedural texture that does not vary across the surface it is
# on. Four render passes went into guessing.
#
# So a control probe was built to isolate the material -- and the probe used
# PLANES. A plane standing in world XZ has a CONSTANT Y coordinate, and the
# texture was banded along Y. The bench was geometrically incapable of showing
# the defect it was built to find, and reported "flat" with no error.
#
# The probe confirmed a false conclusion. That is worse than having no probe.
#
# This is lesson 3 of LECCIONES.md ("metricas ciegas") one level deeper: it is
# not enough for the measurement to be pointed at the right thing. The TEST
# GEOMETRY has to be able to express every axis the material can use.
#
# Hence: CUBES, never planes. A cube spans X, Y and Z, so no texture axis can
# hide from the measurement.
#
# Two more findings from the same session, both silent:
#
#   - With Object coordinates on meshes built at world position, a texture
#     `Scale` is literally CYCLES PER METRE. A value of 30 makes 3 cm bands that
#     average to nothing at 20 m. Real formwork marks are 12-18 cm -> scale 6-8.
#     A badly chosen scale is indistinguishable from a broken material by eye.
#   - Chained Mix -> ColorRamp stages each attenuate amplitude. A 0.30 mix factor
#     into a ramp compressed by a small tonal spread took the variation down to
#     +-0.007 of albedo. Invisible BY CONSTRUCTION, and the graph looks correct.
#
# USAGE
#
#   from recetas.material_swatch import render_swatches, assert_materials_vary
#
#   mats = {"floor": floor_mat, "slab": slab_mat, "wood": wood_mat}
#   stats = render_swatches(mats, "_out/swatch.png")
#   assert_materials_vary(stats)                     # fails the build
#
# Run under `--python-exit-code 1` so a failure stops the pipeline instead of
# shipping a flat asset.

import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from recetas.verdict import Report, PASS, FAIL, NOT_APPLICABLE


# Blender's bundled Python has NO Pillow, so all pixel work goes through
# bpy.data.images + foreach_get. Same constraint use_size.py hit.


def _cube(name, x0, size, material):
    """Axis-aligned cube spanning `size` on X, Y and Z from (x0, 0, 0)."""
    x1, y1, z1 = x0 + size, size, size
    verts = [
        (x0, 0.0, 0.0), (x1, 0.0, 0.0), (x1, y1, 0.0), (x0, y1, 0.0),
        (x0, 0.0, z1), (x1, 0.0, z1), (x1, y1, z1), (x0, y1, z1),
    ]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.validate()
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def render_swatches(materials, out_path, size=4.0, samples=64,
                    gap=0.4, res_per_swatch=320, height=460,
                    world_strength=3.0):
    """
    Render one cube per material under even light and report per-swatch stats.

    `materials` is an ordered dict/mapping of name -> bpy material. Returns
    {name: {"mean": float, "stddev": float}} in 0-1 luminance.

    The cubes are built at WORLD position (x0 growing along X) so that Object
    texture coordinates match how the real surfaces sit in the scene. A material
    whose texture is keyed to world position will therefore read here the same
    way it reads in the beauty render.
    """
    names = list(materials.keys())
    for i, key in enumerate(names):
        _cube(f"swatch_{key}", i * (size + gap), size, materials[key])

    world = bpy.data.worlds.new("swatch_world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = \
        world_strength
    bpy.context.scene.world = world

    span = len(names) * (size + gap)
    cam_data = bpy.data.cameras.new("swatch_cam")
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = span * 1.05
    cam = bpy.data.objects.new("swatch_cam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    # Three-quarter view: a head-on camera sees ONE face, which re-introduces
    # exactly the blindness this recipe exists to remove.
    cam.location = (span / 2 - 0.2, -size * 3.5, size * 1.9)
    cam.rotation_euler = (math.radians(66.0), 0.0, 0.0)
    bpy.context.scene.camera = cam

    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.seed = 12345
    scene.render.resolution_x = res_per_swatch * len(names)
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.filepath = out_path
    scene.render.image_settings.file_format = 'PNG'
    # Standard, not Filmic: a tone curve compresses the highlights and can make
    # a varying material look flatter than it is. The probe must be linear-ish.
    scene.view_settings.view_transform = 'Standard'
    bpy.ops.render.render(write_still=True)

    return _measure(out_path, names, res_per_swatch, height)


def _measure(png_path, names, res_per_swatch, height, margin=0.14, step=2):
    """
    Per-swatch luminance stats: `mean`, `stddev`, and -- the one the gate uses
    -- `detail`.

    WHY `detail` EXISTS (caught by the positive control, same session)
    The first version of this gate used `stddev` and it did not work. On a CUBE,
    the three visible faces sit at different angles to the light, so a perfectly
    UNIFORM material scores a large stddev purely from face shading. Measured:
    a deliberately flat control scored 0.058 while the genuinely textured slab
    scored 0.008 -- the instrument was inverted, and it would have passed every
    flat material handed to it.

    That is lesson 3 of LECCIONES.md occurring INSIDE the tool written to
    prevent lesson 3: a measurement of something real that is not the question.
    It was only caught because a known-bad control was run through the gate.

    `detail` is the MEDIAN absolute difference between pixels `step` apart. A
    smooth shading gradient across a face is low frequency and barely registers;
    a texture is high frequency and registers strongly. The median (not the
    mean) keeps the hard edges BETWEEN faces from carrying the score -- those
    are a handful of pixels, and a mean would let them fake a pass.
    """
    import numpy as np

    img = bpy.data.images.load(png_path, check_existing=False)
    w, h = img.size
    ch = img.channels
    buf = np.empty(w * h * ch, dtype=np.float32)
    img.pixels.foreach_get(buf)
    bpy.data.images.remove(img)

    rgb = buf.reshape(h, w, ch)[:, :, :3]
    lum = (0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1]
           + 0.0722 * rgb[:, :, 2])

    stats = {}
    for i, name in enumerate(names):
        x0 = int(w * i / len(names) + res_per_swatch * margin)
        x1 = int(w * (i + 1) / len(names) - res_per_swatch * margin)
        y0, y1 = int(h * margin), int(h * (1.0 - margin))
        tile = lum[y0:y1, x0:x1]

        dx = np.abs(tile[:, step:] - tile[:, :-step])
        dy = np.abs(tile[step:, :] - tile[:-step, :])
        detail = float(np.median(np.concatenate([dx.ravel(), dy.ravel()])))

        stats[name] = {"mean": float(tile.mean()),
                       "stddev": float(tile.std()),
                       "detail": detail}
    return stats


def assert_materials_vary(stats, min_detail=0.00010, exempt=None):
    """
    Fail the build when a material renders flat over real 3D geometry.

    This is a PROPERTY gate, not an evidence gate (lesson 9): it does not check
    that a swatch was produced, it checks that the swatch carries high-frequency
    variation.

    Gates on `detail`, NOT `stddev` -- see _measure() for why stddev is
    inverted on cube swatches and silently passes flat materials.

    Threshold in 0-1 luminance. Calibrated on the harvest case, measured:

        CONTROL_flat (uniform, no texture) .... 0.00000
        slab (weakest real texture) ........... 0.00028
        floor ................................. 0.00083
        wood .................................. 0.00112
        column (strongest) .................... 0.00364

    The default sits at 0.00010 -- below the weakest REAL material by ~3x and
    above the uniform control. The band is narrower than it looks because
    denoising is ON for the probe: the denoiser flattens sampling noise to
    exactly zero on a uniform surface (which is what makes the control read
    0.00000) while preserving genuine texture. Turning denoising off does NOT
    widen the margin -- it raises the floor for everything, since Cycles noise
    is itself high-frequency.

    `exempt` is a dict {material_name: reason}, NOT a list. Four external
    reviewers (2026-09-02) flagged the original bare tuple as lesson 8 waiting
    to happen: an exemption list nobody has to justify grows every time a build
    is inconvenient, and ends up silencing the gate it belongs to. A reason is
    cheap to write once and is the only thing that separates "this material is
    meant to be uniform" from "this gate annoyed me".

    Returns a Report, so an exempted material shows as NOT_APPLICABLE with its
    reason rather than vanishing from the output.
    """
    if exempt is None:
        exempt = {}
    if not isinstance(exempt, dict):
        raise SystemExit(
            "assert_materials_vary: `exempt` debe ser {material: razon}, no %s.\n"
            "Una exencion sin razon es un check que nadie corrio, disfrazado de\n"
            "aprobado. Ejemplo: exempt={'glass': 'vidrio pulido, uniforme a "
            "proposito'}" % type(exempt).__name__)

    report = Report("MATERIAL VARIATION")
    for name, s in stats.items():
        detail = s["detail"]
        if name in exempt:
            report.add(name, NOT_APPLICABLE, reason=exempt[name])
        elif detail < min_detail:
            report.add(name, FAIL,
                       "detail=%.5f < %.5f" % (detail, min_detail))
        else:
            report.add(name, PASS, "detail=%.5f" % detail)

    if report.failed:
        raise SystemExit(
            report.render() + "\n"
            "FLAT MATERIAL(S) -- the texture does not vary over the geometry.\n"
            "Check, in this order:\n"
            "  1. Is the texture banded on an axis the surface actually spans?\n"
            "     (a slab seen from below needs a different axis than a column)\n"
            "  2. Is the scale sane? With Object coords it is cycles PER METRE.\n"
            "  3. Do the chained Mix/ColorRamp stages still leave any amplitude?\n"
            "     Hand-compute the best-case output before trusting the graph.")
    return report
