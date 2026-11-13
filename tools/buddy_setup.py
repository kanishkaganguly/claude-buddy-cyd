#!/usr/bin/env python3
"""Setup helper for install.sh: read the device token, write buddy.json,
register the Claude Code hooks, and say hello on the device.

  buddy_setup.py token [--port P] [--timeout S]  # reset the board over USB,
                                                 # print the token it boots with
  buddy_setup.py config --token T                # merge into ~/.claude/buddy.json
  buddy_setup.py hooks install --python P --hook H [--approve]
  buddy_setup.py hooks remove
  buddy_setup.py hooks status                    # absent | installed | approve
  buddy_setup.py hello                          # Clawd waves (bridge running)

The hooks commands back up ~/.claude/settings.json first and only ever touch
hook entries that run buddy_hook.py; everything else in the file is kept.
"""
import argparse
import json
import os
import re
import shlex
import sys
import time

import buddy_bridge as bb

CLAUDE_DIR = os.path.join(os.path.expanduser("~"), ".claude")
SETTINGS = os.path.join(CLAUDE_DIR, "settings.json")
HOOK_MARK = "buddy_hook.py"  # how our entries are recognised on re-runs
# async status events (tools/HOOKS.md §2), plus PreCompact for the sweep clip
STATUS_EVENTS = ("SessionStart", "UserPromptSubmit", "PreToolUse",
                 "PostToolUse", "Stop", "SessionEnd", "Notification",
                 "PreCompact")
APPROVE_EVENT = "PermissionRequest"  # synchronous, opt-in (HOOKS.md §2.1)

# printed once per boot by src/main.cpp: "[hub] token=<16 hex chars>"
TOKEN_RE = re.compile(rb"\[hub\] token=([0-9a-f]{16})\b")


# ---- token -------------------------------------------------------------------

def parse_token(line):
    """One line of boot output (bytes) -> the token, or None."""
    m = TOKEN_RE.search(line)
    return m.group(1).decode("ascii") if m else None


def find_ports():
    """USB-serial ports that may be the buddy (the bridge's own VID list)."""
    from serial.tools import list_ports
    return [p.device for p in list_ports.comports() if p.vid in bb.USB_VIDS]


def read_token(port, timeout=10.0, reset=True):
    """Reboot the board and read the token from its boot output.

    DTR stays released (GPIO0 high: a normal boot, not the ROM loader) and a
    short RTS pulse drives EN low through the CYD's auto-reset circuit."""
    import serial
    if "://" in port:
        s = serial.serial_for_url(port, do_not_open=True)
    else:
        s = serial.Serial()
        s.port = port
    s.baudrate = 115200
    s.timeout = 0.2
    s.dtr = False
    s.rts = False
    s.open()
    try:
        if reset:
            s.rts = True
            time.sleep(0.1)
            s.rts = False
        buf = b""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            buf += s.read(s.in_waiting or 1)
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                tok = parse_token(line)
                if tok:
                    return tok
        return parse_token(buf)
    finally:
        s.close()


# ---- buddy.json --------------------------------------------------------------

def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _write_json(path, obj, mode=None):
    """Atomic replace: write a sibling temp file, then rename over."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
        f.write("\n")
    if mode is not None:
        os.chmod(tmp, mode)
    os.replace(tmp, path)


def merge_config(cfg, token):
    """buddy.json dict -> the same with "token" set; other keys kept."""
    out = dict(cfg) if isinstance(cfg, dict) else {}
    out["token"] = token
    return out


# ---- settings.json hooks -----------------------------------------------------

def hook_command(python, hook):
    return "%s %s" % (shlex.quote(python), shlex.quote(hook))


def _is_ours(h):
    return isinstance(h, dict) and HOOK_MARK in str(h.get("command", ""))


def strip_hooks(settings):
    """settings dict -> a copy without any hook entry running buddy_hook.py.
    Matcher groups and events left empty by that are dropped too; everything
    else (other hooks, other keys) is kept as it was."""
    out = dict(settings)
    hooks = out.get("hooks")
    if not isinstance(hooks, dict):
        return out
    new = {}
    for evt, groups in hooks.items():
        if not isinstance(groups, list):
            new[evt] = groups
            continue
        kept = []
        for g in groups:
            if not isinstance(g, dict) or not isinstance(g.get("hooks"), list):
                kept.append(g)
                continue
            inner = [h for h in g["hooks"] if not _is_ours(h)]
            if inner:
                kept.append(dict(g, hooks=inner))
            elif not any(_is_ours(h) for h in g["hooks"]):
                kept.append(g)  # an empty group that was never ours
        if kept:
            new[evt] = kept
    if new:
        out["hooks"] = new
    else:
        out.pop("hooks", None)
    return out


def our_events(settings):
    """The hook events that currently run buddy_hook.py."""
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return set()
    return {evt for evt, groups in hooks.items() if isinstance(groups, list)
            for g in groups if isinstance(g, dict)
            for h in (g.get("hooks") if isinstance(g.get("hooks"), list) else [])
            if _is_ours(h)}


def merge_hooks(settings, command, approve=False):
    """settings dict -> a copy with our hooks registered exactly once."""
    out = strip_hooks(settings)
    hooks = dict(out.get("hooks") or {})
    for evt in STATUS_EVENTS:
        hooks[evt] = list(hooks.get(evt, [])) + [{"hooks": [
            {"type": "command", "command": command, "async": True,
             "timeout": 10}]}]
    if approve:
        hooks[APPROVE_EVENT] = list(hooks.get(APPROVE_EVENT, [])) + [{"hooks": [
            {"type": "command", "command": command, "timeout": 30}]}]
    out["hooks"] = hooks
    return out


def _save_settings(new):
    """Back up the current settings.json, then replace it. No-op if equal."""
    old = _load_json(SETTINGS)
    if new == old:
        return None
    backup = None
    if os.path.exists(SETTINGS):
        backup = "%s.bak-%s" % (SETTINGS, time.strftime("%Y%m%d-%H%M%S"))
        with open(SETTINGS, "rb") as src, open(backup, "wb") as dst:
            dst.write(src.read())
    _write_json(SETTINGS, new)
    return backup


# ---- CLI ---------------------------------------------------------------------

def _cmd_token(a):
    ports = [a.port] if a.port else find_ports()
    if not ports:
        print("no USB-serial port found (is the buddy plugged in?)",
              file=sys.stderr)
        return 1
    for port in ports:
        try:
            tok = read_token(port, timeout=a.timeout)
        except Exception as e:  # busy, unplugged, no permission
            print("%s: %s" % (port, e), file=sys.stderr)
            continue
        if tok:
            print(tok)
            return 0
        print("%s: no token in the boot output" % port, file=sys.stderr)
    return 1


def _cmd_config(a):
    if not re.fullmatch(r"[0-9a-f]{16}", a.token):
        print("that doesn't look like a device token (16 hex characters)",
              file=sys.stderr)
        return 1
    _write_json(bb.CFG, merge_config(_load_json(bb.CFG), a.token), mode=0o600)
    print("wrote %s" % bb.CFG)
    return 0


def _cmd_hooks(a):
    cur = _load_json(SETTINGS)
    if a.action == "status":
        evts = our_events(cur)
        print("approve" if APPROVE_EVENT in evts else
              "installed" if evts else "absent")
        return 0
    if a.action == "install":
        new = merge_hooks(cur, hook_command(a.python, a.hook), a.approve)
    else:
        new = strip_hooks(cur)
    backup = _save_settings(new)
    if backup is None and new == cur:
        print("%s already up to date" % SETTINGS)
    else:
        print("updated %s%s" % (SETTINGS,
                                " (backup: %s)" % backup if backup else ""))
    return 0


def _cmd_hello(_a):
    port = int(bb.load_cfg().get("port", 8787) or 8787)
    body = {"fx": "heart", "msg": "Installed!", "running": 0,
            "ts": int(time.time() * 1000)}
    try:
        code, _ = bb._client(port, "POST", "/event", body, timeout=5)
    except OSError as e:
        print("bridge not reachable: %s" % e, file=sys.stderr)
        return 1
    return 0 if code == 202 else 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="buddy_setup.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("token", help="reset the board, print its token")
    t.add_argument("--port", help="serial port (default: probe USB-serial)")
    t.add_argument("--timeout", type=float, default=10.0)
    c = sub.add_parser("config", help="write the token into buddy.json")
    c.add_argument("--token", required=True)
    h = sub.add_parser("hooks", help="register / remove the Claude Code hooks")
    h.add_argument("action", choices=("install", "remove", "status"))
    h.add_argument("--python", help="interpreter the hooks run with")
    h.add_argument("--hook", help="path to buddy_hook.py")
    h.add_argument("--approve", action="store_true",
                   help="also add the on-device PermissionRequest hook")
    sub.add_parser("hello", help="send a hello to the device via the bridge")
    a = ap.parse_args(argv)
    if a.cmd == "hooks" and a.action == "install":
        if not (a.python and a.hook):
            ap.error("hooks install needs --python and --hook")
        if os.path.basename(a.hook) != HOOK_MARK:
            # re-runs and `hooks remove` find our entries by this file name
            ap.error("--hook must point at a file named %s" % HOOK_MARK)
    return {"token": _cmd_token, "config": _cmd_config, "hooks": _cmd_hooks,
            "hello": _cmd_hello}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
