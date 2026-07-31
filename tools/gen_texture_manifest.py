"""gen_texture_manifest.py -- stdlib-only provenance/verify tool for _textures/.

WHY THIS EXISTS (reproducibility fix, 2026-07-29):
  village_gen.py's TEX_DIR points at ../_textures and USE_REAL_TEXTURES=True
  is the default, but _textures/ was in .gitignore since v12 (commit fa30ed1)
  -- a fresh clone had zero textures and no record of what should be there.
  Fix chosen: track _textures/*.jpg directly in git (27 files, ~20MB total,
  trivial size -- no LFS needed) PLUS this manifest for provenance/integrity,
  since the textures are third-party downloaded assets (PolyHaven.com, CC0
  license -- see v12 commit message "real PolyHaven CC0 textures"), not
  something this repo generates. No generator/fetch script for them exists
  anywhere in the repo; they were downloaded by hand in July 2026.

USAGE:
  python tools/gen_texture_manifest.py              # regenerate MANIFEST.json
  python tools/gen_texture_manifest.py --verify      # check existing files against MANIFEST.json

No third-party deps -- stdlib only (hashlib, struct, json, os). Texture
dimensions are read by parsing JPEG SOF markers directly (no Pillow needed).
"""
import hashlib
import json
import os
import struct
import sys

TEX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_textures")
MANIFEST_PATH = os.path.join(TEX_DIR, "MANIFEST.json")

PROVENANCE_NOTE = (
    "All textures in this directory are CC0-licensed photo textures sourced "
    "from PolyHaven (polyhaven.com), downloaded by hand and committed in "
    "v12 (commit fa30ed1, 2026-07-20). CC0 = public domain, no attribution "
    "legally required. Filename convention: <slug>_<diff|nor|rough>.jpg -- "
    "diff = base color, nor = normal map (GL/OpenGL convention), "
    "rough = roughness map. Consumed by mat_textured() / TEX_DIR in "
    "recetas/village_gen.py."
)


def _jpeg_dimensions(path):
    """Parse width/height straight out of JPEG SOF0/SOF2 markers. Returns
    (width, height) or (None, None) if the file isn't a parseable JPEG."""
    try:
        with open(path, "rb") as f:
            data = f.read(2)
            if data != b"\xff\xd8":
                return (None, None)
            while True:
                marker = f.read(2)
                if len(marker) < 2 or marker[0] != 0xFF:
                    return (None, None)
                code = marker[1]
                # SOF0..SOF15 except DHT(C4)/JPG(C8)/DAC(CC) carry frame dims
                if code in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                            0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    f.read(3)  # length(2) + precision(1)
                    h, w = struct.unpack(">HH", f.read(4))
                    return (w, h)
                if code in (0xD8, 0xD9):
                    return (None, None)
                seg_len = struct.unpack(">H", f.read(2))[0]
                f.seek(seg_len - 2, os.SEEK_CUR)
    except (IOError, OSError, struct.error):
        return (None, None)


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest():
    entries = []
    for name in sorted(os.listdir(TEX_DIR)):
        if not name.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        path = os.path.join(TEX_DIR, name)
        if not os.path.isfile(path):
            continue
        w, h = _jpeg_dimensions(path) if name.lower().endswith((".jpg", ".jpeg")) else (None, None)
        entries.append({
            "filename": name,
            "sha256": _sha256(path),
            "size_bytes": os.path.getsize(path),
            "width": w,
            "height": h,
            "source": "polyhaven.com",
            "license": "CC0",
        })
    return {
        "provenance": PROVENANCE_NOTE,
        "generated_by": "tools/gen_texture_manifest.py",
        "file_count": len(entries),
        "textures": entries,
    }


def verify_manifest():
    if not os.path.exists(MANIFEST_PATH):
        print("MANIFEST.json not found at %s" % MANIFEST_PATH)
        return 1
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    ok = True
    seen = set()
    for entry in manifest["textures"]:
        path = os.path.join(TEX_DIR, entry["filename"])
        seen.add(entry["filename"])
        if not os.path.exists(path):
            print("MISSING: %s" % entry["filename"])
            ok = False
            continue
        actual_hash = _sha256(path)
        if actual_hash != entry["sha256"]:
            print("HASH MISMATCH: %s (expected %s, got %s)" %
                  (entry["filename"], entry["sha256"], actual_hash))
            ok = False

    on_disk = {n for n in os.listdir(TEX_DIR)
               if n.lower().endswith((".jpg", ".jpeg", ".png"))}
    extra = on_disk - seen
    for name in sorted(extra):
        print("UNTRACKED (not in manifest): %s" % name)
        ok = False

    if ok:
        print("OK: %d textures verified against MANIFEST.json" % len(manifest["textures"]))
        return 0
    return 1


def main():
    if "--verify" in sys.argv:
        sys.exit(verify_manifest())
    manifest = build_manifest()
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    print("Wrote %s (%d textures)" % (MANIFEST_PATH, manifest["file_count"]))


if __name__ == "__main__":
    main()
