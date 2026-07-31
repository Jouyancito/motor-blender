# glb_export.py -- GLB export contract for the biome packs.
#
# The packs do NOT all pass the same export flags today (divergence D-EXPORT):
# grass_pack passes only use_selection/export_format/export_yup/export_apply and
# therefore lets export_animations keep the exporter's own default of True;
# rock_pack omits export_format; the other four pass format+apply+animations=
# False+cameras=False+lights=False.
#
# So a kwarg passed as None here is OMITTED from the bpy.ops call entirely. That
# is what lets every pack reproduce its exact current flag set byte-for-byte
# until a byte-compare proves they can safely be unified.
import os
import bpy


def reset_transforms(objects):
    """Drop-in ready: local origin, no baked showcase offset."""
    for obj in objects:
        obj.location = (0.0, 0.0, 0.0)


def _select_only(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    if objects:
        bpy.context.view_layer.objects.active = objects[0]


def export_glb(filepath, objects, fmt='GLB', yup=True, apply=True, animations=False,
               cameras=False, lights=False, selection=True):
    """Export `objects` to `filepath`. Any kwarg left as None is omitted."""
    if selection:
        _select_only(objects)

    kw = {"filepath": filepath}
    for key, value in (("use_selection", selection),
                       ("export_format", fmt),
                       ("export_yup", yup),
                       ("export_apply", apply),
                       ("export_animations", animations),
                       ("export_cameras", cameras),
                       ("export_lights", lights)):
        if value is not None:
            kw[key] = value

    try:
        bpy.ops.export_scene.gltf(**kw)
    except TypeError:
        # export_yup has been renamed/removed across exporter versions; retry
        # without it rather than failing the whole build.
        kw.pop("export_yup", None)
        bpy.ops.export_scene.gltf(**kw)


def export_variants(dirpath, objects, name_fn, **export_kwargs):
    """One GLB per object, filename from name_fn(obj)."""
    for obj in objects:
        export_glb(os.path.join(dirpath, name_fn(obj)), [obj], **export_kwargs)
