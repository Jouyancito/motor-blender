# RECETA: pose_swing — rotar un hueso en eje de MUNDO alrededor de su cabeza
# QUÉ: pose de extremidades por rig (reversible, no destructivo) — el fix de brazos que subió
#      IoU 0.651→0.760 en una operación.
# CUÁNDO: la silueta difiere por POSE, no por volumen (chequear overlay antes: brazos, stance).
# GOTCHAS: (1) el SIGNO por lado se verifica con un VISTAZO, no con álgebra — dos veces el
#      razonamiento a ciegas erró la dirección; (2) objetos NO parentados al rig (garras sueltas)
#      quedan flotando — moverlos o reconstruirlos después; (3) view_layer.update() antes de leer
#      posiciones resultantes; (4) medir la mano en world para confirmar el ángulo.
# EXEMPLAR: swing(rig, 'upperarm_L', -25); swing(rig, 'upperarm_R', 25)  # bajar brazos
import bpy
import math
from mathutils import Matrix


def swing(rig, bone_name, deg, axis='Y'):
    pb = rig.pose.bones[bone_name]
    Mw = rig.matrix_world @ pb.matrix
    pivot = Mw.to_translation()
    Rw = Matrix.Rotation(math.radians(deg), 4, axis)
    pb.matrix = rig.matrix_world.inverted() @ (
        Matrix.Translation(pivot) @ Rw @ Matrix.Translation(-pivot) @ Mw)
    bpy.context.view_layer.update()
    return (rig.matrix_world @ pb.matrix).to_translation()
