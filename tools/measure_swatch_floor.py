"""measure_swatch_floor.py -- re-measure the instrument floor of material_swatch.

Run (needs Blender, CPU Cycles is enough):
    blender -b --factory-startup --python-exit-code 1 \
        --python tools/measure_swatch_floor.py

It renders a flat CONTROL plus synthetic materials of KNOWN albedo amplitude
through render_swatches() at 8-bit and 16-bit PNG depth and prints `detail` for
each. The point is to know what the instrument can resolve before trusting a
threshold (REVIEW_FABLE_2026-09-08 D5). The numbers that justify
MIN_DETAIL_DEFAULT live in the comment above it in material_swatch.py.
"""
import os
import sys

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from recetas.material_swatch import render_swatches  # noqa: E402

AMPLITUDES = (0.002, 0.005, 0.01, 0.03, 0.1)
OUT = os.path.join(ROOT, "_out", "swatch_floor")


def make_mat(name, amplitude):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 1.0
    if amplitude == 0.0:
        bsdf.inputs["Base Color"].default_value = (0.5, 0.5, 0.5, 1.0)
        return m
    coord = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 8.0
    noise.inputs["Detail"].default_value = 8.0
    nt.links.new(coord.outputs["Object"], noise.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = 'RGBA'
    mix.inputs[6].default_value = (0.5 - amplitude, 0.5 - amplitude,
                                   0.5 - amplitude, 1.0)
    mix.inputs[7].default_value = (0.5 + amplitude, 0.5 + amplitude,
                                   0.5 + amplitude, 1.0)
    nt.links.new(noise.outputs["Fac"], mix.inputs[0])
    nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    return m


def run(depth):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mats = {"CONTROL_flat": make_mat("c", 0.0)}
    for a in AMPLITUDES:
        mats["amp_%.3f" % a] = make_mat("a%s" % a, a)
    stats = render_swatches(mats, os.path.join(OUT, "floor_%sbit.png" % depth),
                            color_depth=depth)
    print("\n  color_depth=%s" % depth)
    for k, v in stats.items():
        print("    %-14s detail=%.5f  mean=%.3f" % (k, v["detail"], v["mean"]))
    return stats


def verify(stats):
    """The 16-bit path must separate the flat control from a +-3 % swing with
    the shipped threshold. SystemExit (rc != 0 under --python-exit-code 1)."""
    from recetas.material_swatch import MIN_DETAIL_DEFAULT
    ctl, weak = stats["CONTROL_flat"]["detail"], stats["amp_0.030"]["detail"]
    if not (ctl < MIN_DETAIL_DEFAULT < weak):
        raise SystemExit("threshold %.5f does not separate control %.5f from "
                         "+-3%% swing %.5f" % (MIN_DETAIL_DEFAULT, ctl, weak))
    print("  VERIFIED: control %.5f < threshold %.5f < +-3%% swing %.5f"
          % (ctl, MIN_DETAIL_DEFAULT, weak))


os.makedirs(OUT, exist_ok=True)
run("8")
verify(run("16"))
