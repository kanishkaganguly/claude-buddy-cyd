"""Tests for the installer's helper: token parsing and reading (against a fake
board on a loopback socket via pyserial's socket:// URL), the buddy.json merge,
and the settings.json hook merge/removal (other hooks and keys are kept).
Run: cd tools && python3 -m unittest test_buddy_setup -v"""
import json
import os
import shutil
import socket
import tempfile
import threading
import unittest
from unittest import mock

import buddy_setup as bs

TOKEN = "0123456789abcdef"
CMD = "/venv/bin/python /home/u/.claude/buddy/buddy_hook.py"


class TestParseToken(unittest.TestCase):
    def test_boot_line(self):
        self.assertEqual(bs.parse_token(b"[hub] token=%s\r" % TOKEN.encode()),
                         TOKEN)

    def test_other_lines(self):
        for line in (b"", b"[CYD Buddy] USB / BLE / WiFi",
                     b"[hub] wifi credentials ignored: USB only",
                     b"[hub] token=nothex!!", b"[hub] token=0123"):
            self.assertIsNone(bs.parse_token(line), line)


class FakeBoard:
    """Accepts one connection and writes a boot log containing the token."""

    def __init__(self, lines):
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srv.bind(("127.0.0.1", 0))
        self.srv.listen(1)
        self.port = self.srv.getsockname()[1]
        self.lines = lines
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self):
        try:
            c, _ = self.srv.accept()
        except OSError:
            return
        with c:
            for line in self.lines:
                c.sendall(line + b"\r\n")
            try:
                c.recv(1)  # hold the connection until the reader closes
            except OSError:
                pass

    def close(self):
        self.srv.close()


class TestReadToken(unittest.TestCase):
    def test_reads_token_from_boot_log(self):
        dev = FakeBoard([b"ets Jun  8 2016 00:22:57", b"rst:0x1 (POWERON_RESET)",
                         b"[CYD Buddy] USB / BLE / WiFi + official Clawd",
                         b"[hub] token=" + TOKEN.encode(), b"[ble] advertising"])
        self.addCleanup(dev.close)
        url = "socket://127.0.0.1:%d" % dev.port
        self.assertEqual(bs.read_token(url, timeout=5, reset=False), TOKEN)

    def test_no_token_times_out(self):
        dev = FakeBoard([b"just noise"])
        self.addCleanup(dev.close)
        url = "socket://127.0.0.1:%d" % dev.port
        self.assertIsNone(bs.read_token(url, timeout=0.5, reset=False))


class TestConfig(unittest.TestCase):
    def test_merge_keeps_other_keys(self):
        cfg = {"token": "old", "transport": "usb", "budget": 5}
        self.assertEqual(bs.merge_config(cfg, TOKEN),
                         {"token": TOKEN, "transport": "usb", "budget": 5})

    def test_merge_from_nothing(self):
        self.assertEqual(bs.merge_config({}, TOKEN), {"token": TOKEN})
        self.assertEqual(bs.merge_config(None, TOKEN), {"token": TOKEN})


def _ours(settings):
    return [(evt, h) for evt, groups in settings.get("hooks", {}).items()
            for g in groups for h in g.get("hooks", [])
            if "buddy_hook.py" in h.get("command", "")]


class TestHooks(unittest.TestCase):
    OTHER = {"$schema": "x", "model": "opus", "permissions": {"allow": ["Bash"]},
             "hooks": {
                 "Stop": [{"hooks": [{"type": "command", "command": "notify"}]}],
                 "PreToolUse": [{"matcher": "Bash", "hooks": [
                     {"type": "command", "command": "guard.sh"}]}]}}

    def test_install_into_empty(self):
        out = bs.merge_hooks({}, CMD)
        self.assertEqual(sorted(out["hooks"]), sorted(bs.STATUS_EVENTS))
        for evt in bs.STATUS_EVENTS:
            self.assertEqual(out["hooks"][evt], [{"hooks": [
                {"type": "command", "command": CMD, "async": True,
                 "timeout": 10}]}])
        self.assertNotIn(bs.APPROVE_EVENT, out["hooks"])

    def test_install_keeps_everything_else(self):
        out = bs.merge_hooks(self.OTHER, CMD)
        for k in ("$schema", "model", "permissions"):
            self.assertEqual(out[k], self.OTHER[k])
        self.assertEqual(out["hooks"]["Stop"][0], self.OTHER["hooks"]["Stop"][0])
        self.assertEqual(out["hooks"]["PreToolUse"][0],
                         self.OTHER["hooks"]["PreToolUse"][0])
        self.assertEqual(len(_ours(out)), len(bs.STATUS_EVENTS))

    def test_input_not_mutated(self):
        before = json.loads(json.dumps(self.OTHER))
        bs.merge_hooks(self.OTHER, CMD, approve=True)
        bs.strip_hooks(self.OTHER)
        self.assertEqual(self.OTHER, before)

    def test_reinstall_is_idempotent(self):
        once = bs.merge_hooks(self.OTHER, CMD)
        self.assertEqual(bs.merge_hooks(once, CMD), once)

    def test_reinstall_replaces_old_command(self):
        old = bs.merge_hooks(self.OTHER, 'python "/old/repo/tools/buddy_hook.py"',
                             approve=True)
        new = bs.merge_hooks(old, CMD)
        self.assertEqual({h["command"] for _, h in _ours(new)}, {CMD})
        self.assertNotIn(bs.APPROVE_EVENT, new["hooks"])

    def test_approve_adds_sync_permission_hook(self):
        out = bs.merge_hooks({}, CMD, approve=True)
        self.assertEqual(out["hooks"][bs.APPROVE_EVENT], [{"hooks": [
            {"type": "command", "command": CMD, "timeout": 30}]}])

    def test_remove_restores_original(self):
        self.assertEqual(bs.strip_hooks(bs.merge_hooks(self.OTHER, CMD)),
                         self.OTHER)
        self.assertEqual(bs.strip_hooks(bs.merge_hooks({"model": "x"}, CMD)),
                         {"model": "x"})

    def test_our_events(self):
        self.assertEqual(bs.our_events(self.OTHER), set())
        self.assertEqual(bs.our_events(bs.merge_hooks(self.OTHER, CMD)),
                         set(bs.STATUS_EVENTS))
        self.assertIn(bs.APPROVE_EVENT, bs.our_events(
            bs.merge_hooks({}, CMD, approve=True)))

    def test_remove_keeps_shared_group_neighbours(self):
        mixed = {"hooks": {"Stop": [{"hooks": [
            {"type": "command", "command": "notify"},
            {"type": "command", "command": CMD}]}]}}
        self.assertEqual(bs.strip_hooks(mixed), {"hooks": {"Stop": [{"hooks": [
            {"type": "command", "command": "notify"}]}]}})


class TestSettingsFile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.path = os.path.join(self.tmp, "settings.json")
        p = mock.patch.object(bs, "SETTINGS", self.path)
        p.start()
        self.addCleanup(p.stop)

    def _run(self, *argv):
        with mock.patch("sys.stdout"):
            return bs.main(list(argv))

    def test_install_backs_up_then_remove_restores(self):
        with open(self.path, "w") as f:
            json.dump(TestHooks.OTHER, f)
        self.assertEqual(self._run("hooks", "install", "--python", "/v/python",
                                   "--hook", "/h/buddy_hook.py"), 0)
        backups = [n for n in os.listdir(self.tmp) if ".bak-" in n]
        self.assertEqual(len(backups), 1)
        with open(os.path.join(self.tmp, backups[0])) as f:
            self.assertEqual(json.load(f), TestHooks.OTHER)
        with open(self.path) as f:
            self.assertEqual(len(_ours(json.load(f))), len(bs.STATUS_EVENTS))
        self.assertEqual(self._run("hooks", "remove"), 0)
        with open(self.path) as f:
            self.assertEqual(json.load(f), TestHooks.OTHER)

    def test_unchanged_writes_no_backup(self):
        args = ("hooks", "install", "--python", "/v/python",
                "--hook", "/h/buddy_hook.py")
        self._run(*args)
        self._run(*args)
        # first run had no file to back up; the second changed nothing
        self.assertEqual([n for n in os.listdir(self.tmp) if ".bak-" in n], [])

    def test_rejects_other_hook_names(self):
        with mock.patch("sys.stderr"), self.assertRaises(SystemExit):
            self._run("hooks", "install", "--python", "/v/python",
                      "--hook", "/h/b.py")

    def test_config_writes_private_file(self):
        cfg = os.path.join(self.tmp, "buddy.json")
        with mock.patch.object(bs.bb, "CFG", cfg):
            self.assertEqual(self._run("config", "--token", TOKEN), 0)
            self.assertNotEqual(self._run("config", "--token", "nope"), 0)
        with open(cfg) as f:
            self.assertEqual(json.load(f), {"token": TOKEN})
        self.assertEqual(os.stat(cfg).st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
