"""
make_review_bundle.py -- concatenate the motor's conceptual core into ONE file
that can be pasted into (or uploaded to) another model for outside review.

WHY THIS EXISTS (2026-09-02)
The repo is PRIVATE, so handing another model the GitHub URL gets nothing: it
cannot read it. And the full tree is ~645 KB of .md + .py, most of it generator
code that is noise for a review of the METHOD. This bundles only the parts that
carry the reasoning -- the brief, the lessons, the protocol, the recipe index --
plus one recipe as a worked example of what a gate actually looks like here.

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
     "El pedido: qué es el motor, los 13 patrones de fallo, y las 6 preguntas"),
    ("LECCIONES.md",
     "Las 13 lecciones completas, cada una con el caso real que la pagó"),
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
]

HEADER = """# Motor de generación 3D — paquete para revisión externa

Generado por `tools/make_review_bundle.py`. Es el núcleo conceptual de un repo
privado: se excluyó el código de los generadores (~550 KB) porque es ruido para
una revisión del MÉTODO.

**Qué se espera de quien lee esto**: crítica del método de trabajo, no del
resultado artístico. Las preguntas concretas están al final de la parte 1.
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

    chunks = [HEADER]
    for i, (rel, desc) in enumerate(PARTS, 1):
        chunks.append(f"{i}. **{rel}** — {desc}\n")
    chunks.append("\n---\n")

    for i, (rel, desc) in enumerate(PARTS, 1):
        path = os.path.join(ROOT, rel)
        with open(path, encoding="utf-8") as fh:
            body = fh.read().rstrip()
        fence = rel.endswith(".py")
        chunks.append(f"\n# PARTE {i} — {rel}\n\n> {desc}\n\n")
        chunks.append(f"```python\n{body}\n```\n" if fence else body + "\n")
        chunks.append("\n---\n")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    text = "\n".join(chunks)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)

    kb = len(text.encode("utf-8")) / 1024
    print(f"[bundle] {OUT}")
    print(f"[bundle] {len(PARTS)} partes, {kb:.0f} KB, ~{kb * 0.26:.0f}k tokens aprox")
    return 0


if __name__ == "__main__":
    sys.exit(main())
