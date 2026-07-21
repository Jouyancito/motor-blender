# RECETA — preflight before any DESTRUCTIVE operation (Solidify / Boolean / Remesh /
# block vertex moves). Audit 2026-07-16 item 6: the melena_v5 Solidify explosion was
# PREDICTABLE — a one-sided sheet with 460 open edges and irregular tip normals is the
# documented failure precondition of Solidify Simple (Blender bug tracker #110057).
#
# Use via MCP (live) or headless:
#   from preflight_destructivo import preflight
#   ok, report = preflight('melena_v5')   # -> refuse the operation if not ok
#
# Rules encoded:
# - open (boundary) edges > 0  -> Solidify Simple/Boolean will misbehave: use Solidify
#   mode='COMPLEX' or fix normals + Clamp, or voxel-remesh the shells together first.
# - non-manifold edges         -> same class of danger.
# - thickness > shortest adjacent edge at sharp angles -> spikes (report min edge).
import bpy
import bmesh


def preflight(obj_name, verbose=True):
    o = bpy.data.objects.get(obj_name)
    if o is None or o.type != 'MESH':
        return False, {"error": f"'{obj_name}' not found or not a mesh"}
    bm = bmesh.new()
    bm.from_mesh(o.data)
    open_edges = sum(1 for e in bm.edges if len(e.link_faces) < 2)
    nonmanifold = sum(1 for e in bm.edges if not e.is_manifold)
    min_edge = min((e.calc_length() for e in bm.edges), default=0.0)
    n_verts, n_edges, n_faces = len(bm.verts), len(bm.edges), len(bm.faces)
    bm.free()
    report = {
        "object": obj_name, "verts": n_verts, "edges": n_edges, "faces": n_faces,
        "open_edges": open_edges, "nonmanifold_edges": nonmanifold,
        "min_edge_length": round(min_edge, 5),
        "max_safe_solidify_thickness": round(min_edge, 5),
    }
    ok = (open_edges == 0 and nonmanifold == 0)
    report["verdict"] = "OK for destructive ops" if ok else (
        "NOT SAFE: open/non-manifold edges present. Options: Solidify mode='COMPLEX', "
        "or normals_make_consistent + Clamp <= min_edge_length, or join+voxel_remesh "
        "(the proven organic-fuse recipe), or manual shell extrusion.")
    if verbose:
        for k, v in report.items():
            print(f"  {k}: {v}")
    return ok, report


if __name__ == "__main__":
    import sys
    name = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "base_v2"
    ok, _ = preflight(name)
    sys.exit(0 if ok else 2)
