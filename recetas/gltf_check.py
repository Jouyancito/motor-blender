# gltf_check.py -- run the Khronos glTF-Validator on a generator's .glb.
#
# The validator is a node module (npm `gltf-validator`), not a Python package.
# There is NO silent fallback: if node or the module is missing the check FAILS
# with "validator not installed" and the install command, because a validation
# step that passes when it cannot run is the exact failure of every gate in
# this repo's history (LECCIONES 14).
#
# Install once (measured 2026-10-08: network available, ~0.4 s):
#     npm install --prefix ~/.cache/motor-gltf-validator gltf-validator@2.0.0-dev.3.10
import json
import os
import shutil
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, "tools", "gltf_validate.js")
INSTALL_HINT = ("npm install --prefix ~/.cache/motor-gltf-validator "
                "gltf-validator@2.0.0-dev.3.10")


def validate(path, node=None, runner=RUNNER, timeout=60):
    """Return the validator's JSON summary, or {"error": ...}."""
    node = node or shutil.which("node")
    if not node:
        return {"error": "validator not installed: node not found on PATH. "
                         "Install: " + INSTALL_HINT}
    if not os.path.isfile(path):
        return {"error": "no such file: %s" % path}
    try:
        p = subprocess.run([node, runner, path], capture_output=True, text=True,
                           timeout=timeout)
    except (FileNotFoundError, PermissionError):
        return {"error": "validator not installed: cannot execute %r. Install: %s"
                         % (node, INSTALL_HINT)}
    try:
        out = json.loads(p.stdout.strip().splitlines()[-1])
    except (IndexError, ValueError):
        return {"error": "validator produced no JSON (rc=%s): %s"
                         % (p.returncode, (p.stderr or p.stdout)[:200])}
    if p.returncode == 2:
        out["error"] = "validator not installed (%s). Install: %s" % (
            out.get("base"), INSTALL_HINT)
    return out


def judge(result, max_errors=0):
    """Pure: validator summary -> (state, detail) using verdict states."""
    from recetas.verdict import PASS, FAIL
    if "error" in result:
        return FAIL, result["error"]
    n = result["numErrors"]
    detail = "%s: %d errors, %d warnings, %d infos (validator %s)" % (
        result.get("file"), n, result["numWarnings"], result["numInfos"],
        result.get("version"))
    if n > max_errors:
        detail += " | " + "; ".join(result.get("errors", [])[:3])
        return FAIL, detail
    return PASS, detail
