#!/usr/bin/env python3
"""gen_base.py — MOTOR: generación de base 3D LOCAL desde imagen/boceto (sin Meshy).

Objetivo (Joan 2026-07-13): independencia de Meshy — el juego quema sus límites rápido.
Backend: TripoSR local (MIT, Stability+Tripo, Tier A) corriendo en la GTX 1080 vía WSL,
mismo patrón que UniRig. Entrada: una imagen (foto de boceto en una hoja sirve — el modelo
quita el fondo con rembg). Salida: malla OBJ/GLB en _motor/bases/.

Uso (Windows python, raíz corporeo-3d):
  python _motor/gen_base.py foto_boceto.jpg [--nombre golem_v2]

VRAM: necesita ~4GB libres. Con Blender abierto queda justo; si falla por OOM,
cerrar Blender/Ollama y reintentar (lección UniRig: Ollama solo come 4.7GB).
"""
import argparse
import os
import shlex
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASES = os.path.join(ROOT, "_motor", "bases")


def to_wsl(path):
    p = os.path.abspath(path).replace("\\", "/")
    return "/mnt/" + p[0].lower() + p[2:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("imagen", help="imagen o foto de boceto (jpg/png)")
    ap.add_argument("--nombre", default=None, help="nombre de salida (default: el de la imagen)")
    ap.add_argument("--mc-res", default="256", help="resolución de marching cubes (256 default)")
    args = ap.parse_args()

    if not os.path.isfile(args.imagen):
        print(f"ABORT: no existe {args.imagen}")
        return 2
    name = args.nombre or os.path.splitext(os.path.basename(args.imagen))[0]
    outdir = os.path.join(BASES, name)
    os.makedirs(outdir, exist_ok=True)
    q = shlex.quote
    t0 = time.time()
    cmd = (
        "source ~/miniconda3/etc/profile.d/conda.sh && conda activate gen3d && "
        # WSL2: cudnn busca libcuda.so pero el driver stub solo expone libcuda.so.1
        "mkdir -p ~/lib && ln -sf /usr/lib/wsl/lib/libcuda.so.1 ~/lib/libcuda.so && "
        "export LD_LIBRARY_PATH=$HOME/lib:/usr/lib/wsl/lib:$CONDA_PREFIX/lib:$LD_LIBRARY_PATH && "
        "cd ~/TripoSR && "
        f"python run.py {q(to_wsl(args.imagen))} --output-dir {q(to_wsl(outdir))} "
        f"--mc-resolution {args.mc_res} --model-save-format glb"
    )
    print(f"[gen_base] TripoSR local <- {args.imagen}")
    r = subprocess.run(["wsl", "bash", "-lc", cmd])
    if r.returncode != 0:
        print("ABORT: TripoSR falló. ¿VRAM? (cerrar Blender/Ollama y reintentar)")
        return 1
    print(f"[gen_base] listo en {time.time()-t0:.0f}s -> {outdir}")
    print("[gen_base] siguiente: inspección + retopo/rig según receta; el gate juzga después.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
