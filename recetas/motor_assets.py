# motor_assets.py -- which asset dirs are "in play", and for which session.
#
# The Stop gate used to read a global list and block EVERY session in EVERY
# project for any registered asset (review finding L1). Entries now carry the
# session_id of the PreToolUse payload that registered them; the Stop gate only
# judges assets its own session touched, or assets at/under its cwd when the
# entry has no session (registered from the start_asset.py CLI).
#
# State lives in ~/.claude/state/ (NOT ~/.claude/hooks, which is a symlink into
# the agent-stack git repo). MOTOR_GATE_STATE_DIR overrides it for tests.
# stdlib only: imported from hooks.

import json
import os
import time

HOME = os.path.expanduser("~")
FILE = "motor-assets.json"
MAX_AGE_DAYS = 14


def state_dir():
    return os.environ.get("MOTOR_GATE_STATE_DIR") or os.path.join(HOME, ".claude", "state")


def log(name, line):
    try:
        os.makedirs(state_dir(), exist_ok=True)
        with open(os.path.join(state_dir(), name), "a", encoding="utf-8") as fh:
            fh.write(line.rstrip("\n") + "\n")
    except OSError:
        pass


def _path():
    return os.path.join(state_dir(), FILE)


def entries():
    try:
        with open(_path(), encoding="utf-8") as fh:
            data = json.load(fh)
        return [e for e in data if isinstance(e, dict) and e.get("asset_dir")]
    except (OSError, ValueError):
        return []


def _save(items):
    os.makedirs(state_dir(), exist_ok=True)
    tmp = _path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(items, fh, indent=1)
    os.replace(tmp, _path())


def register(asset_dir, session_id=None):
    items = entries()
    for e in items:
        if e["asset_dir"] == asset_dir and e.get("session_id") == session_id:
            e["registered_at"] = time.time()
            break
    else:
        items.append({"asset_dir": asset_dir, "session_id": session_id,
                      "registered_at": time.time()})
    _save(items)


def prune(max_age_days=MAX_AGE_DAYS, drop_all=False):
    """Drop entries older than max_age_days or whose dir/manifest is gone.
    Returns (kept, dropped)."""
    now, kept, dropped = time.time(), [], []
    for e in entries():
        old = now - float(e.get("registered_at") or 0) > max_age_days * 86400
        gone = not os.path.isfile(os.path.join(e["asset_dir"], "_motor", "manifest.json"))
        (dropped if (drop_all or old or gone) else kept).append(e)
    _save(kept)
    return kept, dropped


def scoped(session_id, cwd):
    """Entries the given Stop payload is responsible for."""
    out = []
    cwd = os.path.realpath(cwd) if cwd else None
    for e in entries():
        d = os.path.realpath(e["asset_dir"])
        if e.get("session_id"):
            if session_id and e["session_id"] == session_id:
                out.append(e)
        elif cwd and (d == cwd or d.startswith(cwd + os.sep)):
            out.append(e)
    return out
