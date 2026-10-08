"""test_blender_gates.py -- fixtures for the gates that need bpy.

    blender -b --factory-startup --python-exit-code 1 --python tools/test_blender_gates.py

tools/test_gates.py launches this itself (and FAILS if Blender is missing unless
MOTOR_TESTS_NO_BLENDER=1 says so explicitly). Prints `BLENDER_RESULT ok total`.
Every detector is shown a known-bad input AND a clean control.
"""
import math
import os
import sys
import tempfile

import bpy
import bmesh

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from recetas import mesh_quality as mq          # noqa: E402
from recetas import gltf_check                   # noqa: E402
from recetas.verdict import PASS, FAIL           # noqa: E402

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print("  %s  %s%s" % ("ok  " if cond else "FAIL", name,
                          (" -- " + str(detail)) if detail and not cond else ""))


def fresh():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def obj_from(bm, name="t"):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.update()
    return ob


def cube(name="cube"):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    return obj_from(bm, name)


def uv_cube(name="uvcube"):
    """primitive_cube_add ships a clean UV unwrap (bmesh create_cube does not)."""
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    ob = bpy.context.object
    ob.name = name
    return ob


def rows(rep):
    return {r["prop"].split(": ", 1)[-1]: r["state"] for r in rep.rows}


def judged(ob, limits=None):
    rep, m = mq.check_mesh([ob], limits or {}, verbose=False)
    return rows(rep), m[ob.name]


def main():
    print("\nmesh_quality.py (Blender)")
    fresh()
    st, m = judged(cube())
    check("control: un cubo limpio pasa nonmanifold/degenerate/winding/normales",
          st["nonmanifold_edges"] == PASS and st["degenerate_faces"] == PASS
          and st["inconsistent_winding_edges"] == PASS
          and st["normals_outward"] == PASS, st)
    check("control: el volumen del cubo es +1 m3 y esta cerrado",
          abs(m["signed_volume"] - 1.0) < 1e-6 and m["closed"], m["signed_volume"])

    fresh()
    bm = bmesh.new()
    v = [bm.verts.new(c) for c in ((0, 0, 0), (1, 0, 0), (0.5, 1, 0), (0.5, -1, 0),
                                   (0.5, 0, 1))]
    bm.faces.new((v[0], v[1], v[2]))
    bm.faces.new((v[0], v[1], v[3]))
    bm.faces.new((v[0], v[1], v[4]))   # three faces on edge v0-v1
    st, m = judged(obj_from(bm))
    check("non-manifold (3 caras en una arista) -> FAIL",
          st["nonmanifold_edges"] == FAIL and m["nonmanifold_edges"] == 1, st)

    fresh()
    bm = bmesh.new()
    a, b, c = (bm.verts.new(p) for p in ((0, 0, 0), (1, 0, 0), (2, 0, 0)))
    bm.faces.new((a, b, c))            # collinear -> zero area
    st, m = judged(obj_from(bm))
    check("cara degenerada (area 0) -> FAIL",
          st["degenerate_faces"] == FAIL and m["degenerate_faces"] == 1, st)

    fresh()
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.faces.ensure_lookup_table()
    bmesh.ops.reverse_faces(bm, faces=[bm.faces[0]])
    st, m = judged(obj_from(bm))
    check("una cara invertida (winding inconsistente) -> FAIL",
          st["inconsistent_winding_edges"] == FAIL and m["inconsistent_edges"] == 4, m)

    fresh()
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    st, m = judged(obj_from(bm))
    check("cubo entero con normales hacia adentro -> FAIL normals_outward",
          st["normals_outward"] == FAIL and m["inconsistent_edges"] == 0
          and m["inward_closed"], (st, m["signed_volume"]))

    fresh()
    ob = uv_cube()
    st, m = judged(ob, {"needs_uv": True})
    check("control: cubo con UV por defecto, sin solapamiento -> PASS",
          m["uv"]["has_uv"] and st["uv_present"] == PASS and st["uv_overlap"] == PASS,
          (st, m["uv"]))
    uv = ob.data.uv_layers.active.data
    for i, loop in enumerate(uv):        # overlap: map every face onto the same square
        loop.uv = ((0, 0), (1, 0), (1, 1), (0, 1))[i % 4]
    st, m = judged(ob, {"needs_uv": True})
    check("todas las caras sobre el mismo cuadrado UV -> uv_overlap FAIL",
          st["uv_overlap"] == FAIL and m["uv"]["overlap"] > 0.5, m["uv"])

    fresh()
    ob = uv_cube()
    ob.data.uv_layers.remove(ob.data.uv_layers.active)
    st, m = judged(ob, {"needs_uv": True})
    check("familia que exige texturas y malla SIN UV -> uv_present FAIL",
          st["uv_present"] == FAIL and not m["uv"]["has_uv"], st)
    st, _ = judged(ob, {"needs_uv": False})
    check("control: sin exigir texturas, la falta de UV no falla",
          "uv_present" in st and st["uv_present"] != FAIL, st)
    st, m = judged(cube("c2"), {"max_tris": 5})
    check("presupuesto de triangulos excedido (12 > 5) -> FAIL",
          st["tri_budget"] == FAIL, st)
    st, m = judged(cube("c3"), {"max_tris": 12})
    check("control: 12 tris con presupuesto 12 -> PASS", st["tri_budget"] == PASS, st)

    check("UV overlap puro: 2 triangulos identicos solapan al 50 %",
          abs(mq.uv_overlap_ratio([((0, 0), (1, 0), (0, 1))] * 2) - 0.5) < 0.02)
    check("UV overlap puro: 2 triangulos disjuntos -> 0",
          mq.uv_overlap_ratio([((0, 0), (0.4, 0), (0, 0.4)),
                               ((0.6, 0.6), (1, 0.6), (0.6, 1))]) < 0.01)

    print("\ngltf_check.py (Blender export + node validator)")
    fresh()
    cube("g")
    with tempfile.TemporaryDirectory() as tmp:
        good = os.path.join(tmp, "good.glb")
        bpy.ops.export_scene.gltf(filepath=good)
        res = gltf_check.validate(good)
        state, detail = gltf_check.judge(res)
        check("control: un GLB exportado por Blender valida con 0 errores",
              state == PASS and res.get("numErrors") == 0, (res, detail))
        bad = os.path.join(tmp, "bad.glb")
        with open(good, "rb") as fh, open(bad, "wb") as out:
            out.write(fh.read(200))
        res = gltf_check.validate(bad)
        state, _ = gltf_check.judge(res)
        check("un GLB truncado -> el validador lo rechaza (FAIL)",
              state == FAIL and res.get("numErrors", 0) >= 1, res)
        old = os.environ.get("MOTOR_GLTF_VALIDATOR_DIR")
        os.environ["MOTOR_GLTF_VALIDATOR_DIR"] = os.path.join(tmp, "nope")
        try:
            res = gltf_check.validate(good)
        finally:
            if old is None:
                del os.environ["MOTOR_GLTF_VALIDATOR_DIR"]
            else:
                os.environ["MOTOR_GLTF_VALIDATOR_DIR"] = old
        state, detail = gltf_check.judge(res)
        check("validador no instalado -> FAIL ruidoso, no pase silencioso",
              state == FAIL and "validator not installed" in detail, detail)

    ok = sum(1 for _, c in results if c)
    print("\nBLENDER_RESULT %d %d" % (ok, len(results)))
    if ok != len(results):
        for n, c in results:
            if not c:
                print("  FALLO:", n)
        sys.exit(1)


main()
