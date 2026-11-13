#!/usr/bin/env bash
# One-command setup for the CYD Claude Buddy (Linux).
#
#   ./install.sh               flash in the browser, then set up this computer
#   ./install.sh --skip-flash  the board is already flashed: only set up
#   ./install.sh flash         only (re)flash: open the web flasher
#   ./install.sh uninstall     remove the hooks and ~/.claude/buddy/
#
# What it writes, all under ~/.claude:
#   buddy/          a private Python env (pyserial, bleak) + the hook and bridge
#   buddy.json      the device token (other keys you set are kept)
#   settings.json   the Claude Code hooks (backed up first; nothing else touched)
# Safe to re-run: every step checks what's already there.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
BUDDY_DIR="$CLAUDE_DIR/buddy"
VENV="$BUDDY_DIR/venv"
PY="$VENV/bin/python"
SETUP="$REPO/tools/buddy_setup.py"
BRIDGE="$REPO/tools/buddy_bridge.py"  # stdlib-only CLI: fine on system python3

say()  { printf '\n==> %s\n' "$*"; }
info() { printf '    %s\n' "$*"; }
die()  { printf '\nerror: %s\n' "$*" >&2; exit 1; }
ask() {  # ask "question" [y|n default] -> status 0 for yes
  local def="${2:-n}" hint="[y/N]" ans=""
  [[ $def == y ]] && hint="[Y/n]"
  read -r -p "    $1 $hint " ans || true
  ans="${ans:-$def}"
  [[ ${ans,,} == y* ]]
}
usage() { sed -n '2,7s/^# \{0,1\}//p' "$0"; }

# ---- preflight ---------------------------------------------------------------
preflight() {
  [[ "$(uname -s)" == Linux ]] || die "this installer is Linux-only"
  command -v python3 >/dev/null || die "python3 not found (sudo apt install python3)"
  python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))' \
    || die "Python 3.9 or newer is needed"
  python3 -c 'import venv, ensurepip' 2>/dev/null \
    || die "Python venv support is missing (sudo apt install python3-venv)"
  if ! id -nG | tr ' ' '\n' | grep -qx dialout; then
    die "your user can't open USB serial ports yet. Run
       sudo usermod -aG dialout $USER
     then log out and back in, and run ./install.sh again."
  fi
}

find_browser() {  # Web Serial: Chromium-based browsers only
  local b
  for b in google-chrome google-chrome-stable chromium chromium-browser \
           microsoft-edge microsoft-edge-stable brave-browser; do
    if command -v "$b" >/dev/null; then echo "$b"; return 0; fi
  done
  return 1
}

# ---- bridge port -------------------------------------------------------------
# While we flash or read the token, a Claude Code session on this computer
# could start a bridge (its hooks spawn one on demand) that grabs the USB port.
# Serving the flasher page on the bridge's own port prevents that: hook events
# reach this web server instead, fail open as usual, and spawn nothing.
HOLD_PID=""
bridge_port() {
  python3 - "$REPO/tools" <<'EOF' 2>/dev/null || echo 8787
import sys; sys.path.insert(0, sys.argv[1])
import buddy_bridge as bb
print(int(bb.load_cfg().get("port", 8787) or 8787))
EOF
}

hold_bridge_port() {
  local port; port="$(bridge_port)"
  for _ in 1 2 3 4 5; do
    python3 "$BRIDGE" stop >/dev/null 2>&1 || true
    python3 -m http.server --bind 127.0.0.1 --directory "$REPO" "$port" \
      >/dev/null 2>&1 &
    HOLD_PID=$!
    sleep 0.7
    if kill -0 "$HOLD_PID" 2>/dev/null; then
      FLASH_URL="http://127.0.0.1:$port/web/"
      return 0
    fi
    HOLD_PID=""
    sleep 1  # a bridge still letting go of the port
  done
  die "port $port is busy (a bridge that won't stop?): try again in a minute"
}

release_bridge_port() {
  if [[ -n $HOLD_PID ]]; then
    kill "$HOLD_PID" 2>/dev/null || true
    wait "$HOLD_PID" 2>/dev/null || true
    HOLD_PID=""
  fi
}
trap release_bridge_port EXIT

# ---- steps -------------------------------------------------------------------
setup_python() {
  say "Python environment for the bridge ($VENV)"
  mkdir -p "$BUDDY_DIR"
  if ! "$PY" -c '' 2>/dev/null; then
    rm -rf "$VENV"
    python3 -m venv "$VENV"
  fi
  "$PY" -m pip install --quiet --disable-pip-version-check \
    -r "$REPO/tools/requirements.txt"
  # the hook starts the bridge from its own folder, so they live side by side
  install -m 644 "$REPO/tools/buddy_hook.py" "$REPO/tools/buddy_bridge.py" \
    "$BUDDY_DIR/"
  info "pyserial + bleak installed; hook and bridge copied to $BUDDY_DIR"
}

flash() {
  say "Flash the board in the browser"
  local browser=""
  browser="$(find_browser)" || true
  info "Plug the CYD into this computer with a USB data cable."
  info "Flasher page: $FLASH_URL"
  if [[ -z $browser ]]; then
    info "No Chrome/Chromium/Edge found (Firefox can't flash: no Web Serial)."
    info "Open the address above in one of those browsers."
  elif [[ -z ${DISPLAY:-}${WAYLAND_DISPLAY:-} ]]; then
    info "No desktop session here: open the address above in Chrome or Edge."
  else
    if [[ "$(readlink -f "$(command -v "$browser")")" == /snap/* ]]; then
      info "(snap browser: if no port shows up, run: sudo snap connect ${browser%%-*}:raw-usb)"
    fi
    nohup "$browser" --new-window "$FLASH_URL" >/dev/null 2>&1 &
    disown || true
    info "Opened it in $browser."
  fi
  info "Click Connect, pick the USB Serial port, choose Install, and wait for"
  info "'Installation complete'."
  info "Updating an already set-up buddy? Leave 'Erase device' unchecked."
  read -r -p "    Press Enter when the flasher is done (and its dialog closed)... " _ || true
}

get_token() {
  say "Reading the device token over USB"
  TOKEN=""
  if TOKEN="$("$PY" "$SETUP" token)"; then
    info "token: $TOKEN"
    return 0
  fi
  info "Couldn't read it automatically. On the device: long-press the screen,"
  info "open Settings; the token is the bottom line."
  local current prompt="Token (16 characters, 0-9 a-f): "
  current="$(python3 - "$REPO/tools" <<'EOF' 2>/dev/null || true
import sys; sys.path.insert(0, sys.argv[1])
import buddy_bridge as bb
print(bb.load_cfg().get("token", ""))
EOF
)"
  [[ -n $current ]] && prompt="Token [Enter keeps $current]: "
  while :; do
    read -r -p "    $prompt" TOKEN || die "no token given"
    TOKEN="${TOKEN:-$current}"
    TOKEN="${TOKEN,,}"
    [[ $TOKEN =~ ^[0-9a-f]{16}$ ]] && return 0
    info "That doesn't look right; try again."
  done
}

configure() {
  say "Pointing Claude Code at the buddy"
  "$PY" "$SETUP" config --token "$TOKEN"
  local def=n approve=()
  [[ "$("$PY" "$SETUP" hooks status)" == approve ]] && def=y
  info "Optional: answer Claude's permission prompts by tapping Allow/Deny on the"
  info "device (falls back to the normal terminal prompt if you don't tap)."
  if ask "Enable on-device approval?" "$def"; then approve=(--approve); fi
  "$PY" "$SETUP" hooks install --python "$PY" \
    --hook "$BUDDY_DIR/buddy_hook.py" "${approve[@]}"
}

setup_wifi() {
  say "WiFi (optional)"
  info "USB and Bluetooth work as they are. WiFi is only for using the buddy"
  info "out of Bluetooth range or from several computers. Needs 2.4 GHz."
  ask "Set up WiFi now?" n || return 0
  local ssid pass
  read -r -p "    Network name (SSID): " ssid
  read -r -s -p "    Password: " pass; echo
  "$PY" "$BUDDY_DIR/buddy_bridge.py" wifi "$ssid" "$pass" \
    || info "WiFi setup didn't finish; retry later with: $PY $BUDDY_DIR/buddy_bridge.py wifi \"<ssid>\" \"<password>\""
}

smoke_test() {
  say "Checking the link"
  if "$PY" "$BUDDY_DIR/buddy_bridge.py" status; then
    "$PY" "$SETUP" hello && info "Clawd should be floating hearts on the screen now."
    return 0
  fi
  info "The bridge couldn't reach the buddy yet. Is it plugged in (or within"
  info "Bluetooth range) and showing the dashboard? Check again with:"
  info "  $PY $BUDDY_DIR/buddy_bridge.py status"
  return 1
}

uninstall() {
  say "Removing the CYD buddy from this computer"
  python3 "$BRIDGE" stop >/dev/null 2>&1 || true
  python3 "$SETUP" hooks remove
  rm -rf "$BUDDY_DIR"
  info "Removed $BUDDY_DIR."
  info "Kept your token and usage history; delete them by hand if you want:"
  info "  rm -f $CLAUDE_DIR/buddy.json $CLAUDE_DIR/buddy_tokens.json $CLAUDE_DIR/buddy_rt.json $CLAUDE_DIR/buddy_device.json"
}

# ---- main --------------------------------------------------------------------
cmd=install
skip_flash=0
for arg in "$@"; do
  case $arg in
    flash|uninstall) cmd=$arg ;;
    --skip-flash) skip_flash=1 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $arg (see ./install.sh --help)" ;;
  esac
done

case $cmd in
  uninstall)
    uninstall
    ;;
  flash)
    preflight
    hold_bridge_port
    flash
    release_bridge_port
    say "Done. The next Claude Code event reconnects the bridge."
    ;;
  install)
    preflight
    if command -v bluetoothctl >/dev/null \
        && bluetoothctl show 2>/dev/null | grep -q "Powered: yes"; then
      info "Bluetooth is on: the buddy can also run cable-free."
    fi
    setup_python
    hold_bridge_port
    [[ $skip_flash == 1 ]] || flash
    get_token
    configure
    release_bridge_port
    setup_wifi
    if smoke_test; then
      say "All set. Start a new Claude Code session and Clawd wakes up."
    else
      say "Setup is done, but the buddy didn't answer yet (see above)."
    fi
    info "status:    $PY $BUDDY_DIR/buddy_bridge.py status"
    info "re-flash:  ./install.sh flash"
    info "uninstall: ./install.sh uninstall"
    ;;
esac
