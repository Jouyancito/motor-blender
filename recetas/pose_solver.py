# RECETA: pose_solver -- pose a rigged humanoid by AIMING bones, not by guessing euler angles.
# QUE: aim(rig, bone, end, direction): rotate `bone` about its head so (end - head) points
#      along `direction` (armature space). two_bone_ik(S, a, b, W, pole): elbow/knee
#      position for a 2-bone chain reaching target W (analytic, pole-vector side).
#      palm_normal / orient_palm: roll a hand about its own axis so the palm faces a target
#      (the palm SIGN is measured at rest, not derived algebraically). curl_fingers.
#      swing_axis, rot_about, reset_pose, eval_points (evaluated mesh, for floor solves),
#      pt (bone head/tail) are the primitives the poses are written with.
# CUANDO: posing an MPFB (or any single-chain-limb) rig deterministically from measures:
#      "thigh 14 deg forward, shin yaw 12 deg", "hands stacked under the chin", then solve
#      the floor from the evaluated mesh (plantar flexion hill, 6 iterations).
# GOTCHAS: (1) palm sign by LOOK, not algebra -- rest palm may face the thigh or away; the
#      caller measures it once per side. (2) L/R: verify by looking, the rig frame faces
#      -Y and the figure is flipped 180 deg at the end. (3) aim() works on pose bones'
#      CURRENT matrices, so the order parent -> child matters: aim the upper arm, THEN
#      re-read the elbow head, THEN aim the forearm. (4) curl uses X euler; `curl_sign`
#      flips it if the rig's finger axis differs. (5) eval_points returns the EVALUATED
#      (posed) vertices, in base order only while no vertex-count-changing modifier is on.
# FUENTE: rem/v8/rem_v8_body_gen.py:249-309 (helpers) and :282-409 pose_figure (the
#      kneeling pose itself stays in rem: it is asset-specific, built FROM these).
#      motor pose_swing.py is the simpler cousin (one bone, world axis).
# EXEMPLAR:
#   aim(rig, "upperleg01.L", ("head", "lowerleg01.L"), Vector((0.05, -0.24, -0.97)), part="body")
import math

import numpy as np

import bpy
from mathutils import Matrix, Vector

try:
    from recetas.motor_stamp import stamp_object as _motor_stamp
except ImportError:  # recipes are also used with recetas/ itself on sys.path
    from motor_stamp import stamp_object as _motor_stamp

TECHNIQUE = "pose_solver"


def upd():
    bpy.context.view_layer.update()


def reset_pose(rig):
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.scale = (1, 1, 1)
    upd()


def eval_points(body):
    """Evaluated (posed) vertex positions, (N, 3), object space."""
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    A = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", A)
    ev.to_mesh_clear()
    return A.reshape(-1, 3)


def pt(rig, spec):
    kind, name = spec
    pb = rig.pose.bones[name]
    return pb.head.copy() if kind == "head" else pb.tail.copy()


def rot_about(rig, bone, pivot, R3):
    pb = rig.pose.bones[bone]
    pb.matrix = Matrix.Translation(pivot) @ R3.to_4x4() @ Matrix.Translation(-pivot) @ pb.matrix
    upd()


def aim(rig, bone, end, direction, part=None):
    """Rotate `bone` about its head so that (end - head) points along `direction`
    (armature space). `end` is ("head"|"tail", bone_name). Stamps the rig AND every object
    bound to it by an Armature modifier: verify_asset requires ALL objects of a part to carry
    the declared technique, and the posed body mesh is part of that part."""
    J = rig.pose.bones[bone].head.copy()
    d0 = (pt(rig, end) - J).normalized()
    q = d0.rotation_difference(Vector(direction).normalized())
    rot_about(rig, bone, J, q.to_matrix())
    _motor_stamp(rig, part, TECHNIQUE)
    for ob in bpy.data.objects:
        if ob.type == "MESH" and any(m.type == "ARMATURE" and m.object == rig for m in ob.modifiers):
            _motor_stamp(ob, part, TECHNIQUE)


def swing_axis(rig, bone, deg, axis):
    rot_about(rig, bone, rig.pose.bones[bone].head.copy(), Matrix.Rotation(math.radians(deg), 3, axis))


def palm_normal(rig, side):
    w = rig.pose.bones["wrist." + side].head
    u = (rig.pose.bones["finger3-1." + side].head - w).normalized()
    lat = rig.pose.bones["finger5-1." + side].head - rig.pose.bones["finger2-1." + side].head
    return u, u.cross(lat).normalized()


def orient_palm(rig, side, sign, target):
    """Roll the hand about its own axis so the palm faces `target` (palm sign measured at rest)."""
    u, n = palm_normal(rig, side)
    n = n * sign
    a = n - u * n.dot(u)
    b = target - u * target.dot(u)
    ang = math.atan2(u.dot(a.cross(b)), a.dot(b))
    rot_about(rig, "wrist." + side, rig.pose.bones["wrist." + side].head.copy(), Matrix.Rotation(ang, 3, u))


def curl_fingers(rig, side, curl_deg, curl_sign=1.0):
    """curl_deg: degrees per phalanx (3 values); the thumb (finger1) uses 0.6 of it."""
    for f in range(1, 6):
        amp = 0.6 if f == 1 else 1.0
        for k, deg in enumerate(curl_deg, start=1):
            nm = "finger%d-%d.%s" % (f, k, side)
            if nm in rig.pose.bones:
                pb = rig.pose.bones[nm]
                pb.rotation_mode = 'XYZ'
                pb.rotation_euler = (math.radians(deg * amp) * curl_sign, 0, 0)
    upd()


def two_bone_ik(S, a, b, W, pole):
    """Mid joint of a 2-bone chain (lengths a, b) from shoulder S reaching W; bends toward `pole`."""
    v = W - S
    dist = min(v.length, a + b - 1e-6)
    u = v.normalized()
    cosA = max(-1.0, min(1.0, (a * a + dist * dist - b * b) / (2 * a * dist)))
    A = math.acos(cosA)
    n = pole - u * pole.dot(u)
    n.normalize()
    return S + u * (a * cosA) + n * (a * math.sin(A))
