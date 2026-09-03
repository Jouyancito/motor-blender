"""
make_review_bundle.py -- concatenate the motor's conceptual core into ONE file
that can be pasted into (or uploaded to) another model for outside review.

WHY THIS EXISTS (2026-09-02)
The repo went PUBLIC on 2026-09-02 (github.com/Jouyancito/motor-blender), so a
reviewer can now be handed the URL. The bundle still earns its place: the full
tree is ~645 KB of .md + .py, most of it generator code that is noise for a
review of the METHOD, and a model given a repo browses it in whatever order it
likes. This fixes the reading order -- ask first, current state second, the
August audits only afterwards -- which is precisely what the first round got
wrong.

Give reviewers BOTH: the bundle to read, the URL to check anything it omits.

Run:
    python tools/make_review_bundle.py
    -> _out/MOTOR_BUNDLE.md   (gitignored; regenerate rather than commit)
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "_out", "MOTOR_BUNDLE.md")

# Order matters: the brief goes first because it frames everything and carries
# the questions. Someone who stops reading after part 1 has still got the ask.
PARTS = [
    ("BRIEF_REVISION_EXTERNA.md",
     "El pedido: qué es el motor, los patrones de fallo, y las 6 preguntas"),
    ("ESTADO_ACTUAL.md",
     "QUÉ ESTÁ IMPLEMENTADO HOY. Leer ANTES que las auditorías: en la primera "
     "ronda de revisión, dos de los cuatro modelos afirmaron como presente algo "
     "que era falso hacía diez días, porque el paquete llevaba las auditorías "
     "que proponían los arreglos y no los archivos que los implementaron"),
    ("LECCIONES.md",
     "Las 14 lecciones completas, cada una con el caso real que la pagó"),
    ("CREATION_PROTOCOL.md",
     "El protocolo de creación (en inglés) — el preflight y sus reglas duras"),
    ("recetas/RECETAS.md",
     "Índice de la biblioteca de recetas verificadas"),
    ("TECNICAS.md",
     "Técnicas observadas en referencias y traducidas a conocimiento del motor"),
    ("AUDIT_ACTIVACION_2026-08-23.md",
     "Auditoría: cuánto del conocimiento del motor se activa solo (la medición "
     "del 2,5 % citada en la lección 1)"),
    ("AUDIT_2026-08-23.md",
     "Auditoría general del motor"),
    ("recetas/material_swatch.py",
     "Un gate real, como ejemplo concreto: prueba que un material varía sobre "
     "su geometría. Incluye, en sus propios comentarios, las DOS veces que este "
     "mismo archivo estuvo roto de la forma que existe para prevenir"),
    ("recetas/verdict.py",
     "Los cuatro estados. NOT_TESTED deja de confundirse con PASS, y "
     "NOT_APPLICABLE exige una razón escrita"),
    ("recetas/asset_spec.py",
     "El punto 4d del preflight convertido en gate: una parte móvil sin "
     "renglón estructural corta el build antes del primer bpy"),
    ("recetas/preflight_router.py",
     "Resuelve QUÉ reglas aplican desde QUÉ se construye. El índice de capa 0 "
     "cerraba 'no sabía que existía'; esto cierra 'no sabía que aplicaba'"),
    ("tools/test_gates.py",
     "Los fixtures adversariales: 26 casos, 6 de ellos entradas malas conocidas "
     "que cada gate DEBE rechazar. Un gate que nunca falló un control positivo "
     "es decoración"),
]

# Files that live in the CONSUMING repo, not here. Their absence is a warning,
# not a failure -- the motor has to stay usable without the game checkout. But
# the first review round proved that leaving CLAUDE.md out is what let two
# reviewers describe a fixed problem as current, so it ships when it is there.
EXTERNAL_PARTS = [
    (os.path.expanduser("~/Desktop/Juego/DungeonParty-A/CLAUDE.md"),
     "CLAUDE.md del repo consumidor — LA CAPA 0 REAL. Es lo que se carga solo "
     "en cada sesión: el preflight de 10 puntos y el índice de canon. Faltaba "
     "en la primera ronda, y por eso se recomendó implementar cosas que ya "
     "estaban implementadas"),
]

HEADER = """# Motor de generación 3D — paquete para revisión externa

Generado por `tools/make_review_bundle.py`. Es el núcleo conceptual del motor:
se excluyó el código de los generadores (~550 KB) porque es ruido para una
revisión del MÉTODO.

**El repo completo es público: https://github.com/Jouyancito/motor-blender** —
si algo de acá te queda corto, o querés ver un generador entero, está ahí. Este
paquete existe para fijar el ORDEN DE LECTURA, no para ocultar nada.

**Qué se espera de quien lee esto**: crítica del método de trabajo, no del
resultado artístico. Las preguntas concretas están al final de la parte 1.

**ORDEN DE LECTURA — importa.** Parte 1 (el pedido) y parte 2 (ESTADO ACTUAL)
antes que nada. Las auditorías que vienen más adelante son de agosto y PROPONEN
arreglos que en varios casos ya están implementados; la parte 2 dice cuáles y
con qué evidencia. En la primera ronda de revisión ese documento no existía, y
dos de cuatro revisores describieron como problema presente algo resuelto diez
días antes. No fue error de ellos: el paquete llevaba las auditorías que
proponían los arreglos y no los archivos que los implementaron.
Interesa el desacuerdo más que la confirmación.

Los documentos están en español salvo `CREATION_PROTOCOL.md` y el código, que
están en inglés.

## Contenido

"""


def main():
    missing = [rel for rel, _ in PARTS
               if not os.path.exists(os.path.join(ROOT, rel))]
    if missing:
        # Fail loudly: a bundle silently missing its lessons would be reviewed
        # as if those were all there is. Exactly the stale-measurement problem.
        raise SystemExit("BUNDLE INCOMPLETO — faltan:\n  " + "\n  ".join(missing))

    # External parts go right after ESTADO_ACTUAL, not at the end. CLAUDE.md is
    # the layer that actually loads by itself; a reviewer who meets it on page
    # 40 has already formed an opinion from the August audits.
    resolved = [(os.path.join(ROOT, rel), rel, desc) for rel, desc in PARTS]
    insert_at = next((i for i, (_p, rel, _d) in enumerate(resolved)
                      if rel == "ESTADO_ACTUAL.md"), 0) + 1
    for abs_path, desc in EXTERNAL_PARTS:
        label = "(externo) " + os.path.basename(abs_path)
        if os.path.exists(abs_path):
            resolved.insert(insert_at, (abs_path, label, desc))
            insert_at += 1
        else:
            print("[bundle] AVISO: falta la parte externa %s" % abs_path)
            print("[bundle]        el paquete sale sin la capa 0 real, que es "
                  "exactamente lo que descarriló la primera revisión")

    chunks = [HEADER]
    for i, (_p, label, desc) in enumerate(resolved, 1):
        chunks.append(f"{i}. **{label}** — {desc}\n")
    chunks.append("\n---\n")

    for i, (path, label, desc) in enumerate(resolved, 1):
        with open(path, encoding="utf-8") as fh:
            body = fh.read().rstrip()
        fence = label.endswith(".py")
        chunks.append(f"\n# PARTE {i} — {label}\n\n> {desc}\n\n")
        chunks.append(f"```python\n{body}\n```\n" if fence else body + "\n")
        chunks.append("\n---\n")

    n_parts = len(resolved)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    text = "\n".join(chunks)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)

    kb = len(text.encode("utf-8")) / 1024
    print(f"[bundle] {OUT}")
    print(f"[bundle] {n_parts} partes, {kb:.0f} KB, ~{kb * 0.26:.0f}k tokens aprox")
    return 0


if __name__ == "__main__":
    sys.exit(main())
