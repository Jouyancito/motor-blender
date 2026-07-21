"""Cross-project proof-of-fire: run the shared preflight_destructivo recipe
against an existing .blend, headless. Usage:
  blender -b <file.blend> --python _run_preflight_on_blend.py -- <out.json>
"""
import bpy, sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)).replace("gate", "recetas"))
from preflight_destructivo import preflight

out_path = sys.argv[sys.argv.index("--") + 1]
reports = []
for o in bpy.data.objects:
    if o.type == 'MESH':
        ok, report = preflight(o.name, verbose=False)
        reports.append(report)

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(reports, f, indent=2)
print("PREFLIGHT REPORTS:", json.dumps(reports, indent=2))
