# use_size.py -- judge an asset at the size it is USED, not the size that is
# convenient to look at.
#
# WHY THIS EXISTS (2026-08-09)
#
# The slime desktop pet was built, rendered at 512 px, assembled into a contact
# sheet, judged, and presented. Only afterwards did anyone check how it reads at
# the size a desktop companion actually is. At 120 px the carved eye strokes are
# barely there; at 72 px the face is GONE and the thing is a blue-grey bean. The
# verdict given on the 512 px sheet was therefore worthless, and twenty minutes
# went into a pass whose central defect was invisible at the inspection size.
#
# It is the same failure as tree_pack shipping at bush scale for weeks: every
# render framed the asset the way that flattered it. The rule generalises, and the
# USE SIZE is different per asset family:
#
#   environment prop   -> a 1.65 m camera at walking distance
#   character / mob    -> beside the 1.8 m player post
#   desktop sprite     -> 72-120 px on screen
#   UI icon            -> its actual slot, 32-48 px
#
# So this module does not hardcode a size. The caller declares what "used" means
# for its asset, and the build refuses to finish without the evidence.
from __future__ import annotations

import os


def use_size_strip(render_path, sizes, out_path=None, pad=14,
                   card=(0.93, 0.94, 0.92), bg=(0.20, 0.22, 0.24)):
    """Render one image at several USE sizes, side by side, biggest first.

    Uses Blender's OWN image API, not Pillow. Blender ships its own Python and it
    has no PIL -- the first version of this module imported Pillow and failed the
    build with ModuleNotFoundError, which at least proved the gate fires. Colours
    are 0-1 floats because that is what bpy speaks.

    `sizes` is the honest part: pass the sizes this asset is really seen at. A
    strip that only goes down to half resolution proves nothing.
    """
    import bpy

    if not os.path.exists(render_path):
        raise FileNotFoundError(f"use_size_strip: no render at {render_path}")
    if not sizes:
        raise ValueError("use_size_strip: declare the sizes this asset is USED at")

    sizes = sorted(set(int(s) for s in sizes), reverse=True)
    big = sizes[0]
    width = sum(sizes) + pad * (len(sizes) + 1)
    height = big + pad * 2

    sheet = bpy.data.images.new("use_size_strip", width=width, height=height,
                                alpha=False)
    buf = [0.0] * (width * height * 4)
    for i in range(width * height):
        buf[i * 4] = bg[0]
        buf[i * 4 + 1] = bg[1]
        buf[i * 4 + 2] = bg[2]
        buf[i * 4 + 3] = 1.0

    x_cursor = pad
    for s in sizes:
        tile = bpy.data.images.load(render_path, check_existing=False)
        tile.scale(s, s)
        px = [0.0] * (s * s * 4)
        tile.pixels.foreach_get(px)
        # bpy rows run BOTTOM-up, same as our buffer, so y maps straight across.
        y0 = pad + (big - s) // 2
        for ty in range(s):
            for tx in range(s):
                si = (ty * s + tx) * 4
                a = px[si + 3]
                di = ((y0 + ty) * width + (x_cursor + tx)) * 4
                for c in range(3):
                    # Composite the transparent render over a light card, so the
                    # asset is judged on something like the surface it will sit on.
                    buf[di + c] = card[c] * (1.0 - a) + px[si + c] * a
        bpy.data.images.remove(tile)
        x_cursor += s + pad

    sheet.pixels.foreach_set(buf)
    out_path = out_path or os.path.join(os.path.dirname(render_path), "_use_size.png")
    sheet.filepath_raw = out_path
    sheet.file_format = "PNG"
    sheet.save()
    bpy.data.images.remove(sheet)
    return out_path


def require_use_size(render_path, sizes, out_path=None):
    """Same, but the build FAILS if the evidence cannot be produced.

    Called last in a build script under `--python-exit-code 1`, this makes the
    build its own gate: an asset cannot finish without a picture of itself at the
    size it will be used. No external hook needed, and it cannot be forgotten the
    way a checklist item can.
    """
    path = use_size_strip(render_path, sizes, out_path)
    print(f"[use_size] evidence at {sizes} px -> {path}")
    print("[use_size] LOOK AT THIS BEFORE JUDGING ANYTHING ELSE.")
    return path
