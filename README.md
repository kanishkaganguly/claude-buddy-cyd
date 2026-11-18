# CYD Claude Buddy

<p align="center">
  <img src="assets/project-cover.png" width="960" alt="CYD Claude Buddy — a yellow ESP32 display with the orange Clawd mascot">
</p>

A tiny desk companion for **Claude Code**, built on the **ESP32 Cheap Yellow Display**.
Clawd acts out your coding activity, tracks usage, and nudges you when Claude needs you.

> **About this fork:** it adds a browser flasher (no PlatformIO needed), a
> one-command Linux installer, live CPU / GPU / RAM graphs, a configurable
> screen timeout, and Linux fixes to
> [wangkant/claude-buddy-cyd](https://github.com/wangkant/claude-buddy-cyd).

- **Live animations** for editing, running commands, reading, thinking, and more.
- **Usage at a glance:** tokens, tool calls, turns, sessions, and daily trends.
- **USB, Bluetooth LE, or WiFi**, with a bridge that starts and stops on demand.
- **Flash from the browser, set up with one command:** no toolchain, no
  hand-edited config files.

[Animations](#clawd-in-action) · [Quick start](#quick-start) · [User guide](docs/GUIDE.md) · [Hook setup](tools/HOOKS.md)

## Clawd in action


All **29 animations**, as shown on the device. Click a preview to open the GIF.

### Working

<table>
  <tr>
    <td align="center" width="33%"><a href="data/clawd/typing.gif"><img src="data/clawd/typing.gif" width="190" height="140" alt="Clawd — typing"></a><br> <strong>Typing</strong></td>
    <td align="center" width="33%"><a href="data/clawd/writing.gif"><img src="data/clawd/writing.gif" width="190" height="140" alt="Clawd — writing"></a><br> <strong>Writing</strong></td>
    <td align="center" width="33%"><a href="data/clawd/terminal.gif"><img src="data/clawd/terminal.gif" width="190" height="140" alt="Clawd — running commands"></a><br> <strong>Running commands</strong></td>
  </tr>
  <tr>
    <td align="center" width="33%"><a href="data/clawd/hammering.gif"><img src="data/clawd/hammering.gif" width="190" height="140" alt="Clawd — building"></a><br> <strong>Building</strong></td>
    <td align="center" width="33%"><a href="data/clawd/reading.gif"><img src="data/clawd/reading.gif" width="190" height="140" alt="Clawd — reading"></a><br> <strong>Reading</strong></td>
    <td align="center" width="33%"><a href="data/clawd/scanning.gif"><img src="data/clawd/scanning.gif" width="190" height="140" alt="Clawd — inspecting"></a><br> <strong>Inspecting</strong></td>
  </tr>
  <tr>
    <td align="center" width="33%"><a href="data/clawd/searching.gif"><img src="data/clawd/searching.gif" width="190" height="140" alt="Clawd — searching"></a><br> <strong>Searching</strong></td>
    <td align="center" width="33%"><a href="data/clawd/planning.gif"><img src="data/clawd/planning.gif" width="190" height="140" alt="Clawd — planning"></a><br> <strong>Planning</strong></td>
    <td align="center" width="33%"><a href="data/clawd/tooling.gif"><img src="data/clawd/tooling.gif" width="190" height="140" alt="Clawd — using tools"></a><br> <strong>Using tools</strong></td>
  </tr>
  <tr>
    <td align="center" width="33%"><a href="data/clawd/delegating.gif"><img src="data/clawd/delegating.gif" width="190" height="140" alt="Clawd — delegating"></a><br> <strong>Delegating</strong></td>
    <td align="center" width="33%"><a href="data/clawd/pondering.gif"><img src="data/clawd/pondering.gif" width="190" height="140" alt="Clawd — thinking"></a><br> <strong>Thinking</strong></td>
    <td align="center" width="33%"><a href="data/clawd/sweeping.gif"><img src="data/clawd/sweeping.gif" width="190" height="140" alt="Clawd — compacting"></a><br> <strong>Compacting</strong></td>
  </tr>
</table>

### Creative

<table>
  <tr>
    <td align="center" width="33%"><a href="data/clawd/brewing.gif"><img src="data/clawd/brewing.gif" width="190" height="140" alt="Clawd — brewing"></a><br> <strong>Brewing</strong></td>
    <td align="center" width="33%"><a href="data/clawd/forging.gif"><img src="data/clawd/forging.gif" width="190" height="140" alt="Clawd — forging"></a><br> <strong>Forging</strong></td>
    <td align="center" width="33%"><a href="data/clawd/conjuring.gif"><img src="data/clawd/conjuring.gif" width="190" height="140" alt="Clawd — conjuring"></a><br> <strong>Conjuring</strong></td>
  </tr>
  <tr>
    <td align="center" width="33%"><a href="data/clawd/juggling.gif"><img src="data/clawd/juggling.gif" width="190" height="140" alt="Clawd — juggling"></a><br> <strong>Juggling</strong></td>
    <td align="center" width="33%"><a href="data/clawd/painting.gif"><img src="data/clawd/painting.gif" width="190" height="140" alt="Clawd — painting"></a><br> <strong>Painting</strong></td>
    <td align="center" width="33%"><a href="data/clawd/churning.gif"><img src="data/clawd/churning.gif" width="190" height="140" alt="Clawd — turning gears"></a><br> <strong>Turning gears</strong></td>
  </tr>
  <tr>
    <td align="center" width="33%"><a href="data/clawd/stacking.gif"><img src="data/clawd/stacking.gif" width="190" height="140" alt="Clawd — stacking blocks"></a><br> <strong>Stacking blocks</strong></td>
    <td align="center" width="33%"><a href="data/clawd/vibing.gif"><img src="data/clawd/vibing.gif" width="190" height="140" alt="Clawd — vibing"></a><br> <strong>Vibing</strong></td>
    <td></td>
  </tr>
</table>

### Rest & reactions

<table>
  <tr>
    <td align="center" width="33%"><a href="data/clawd/sleep.gif"><img src="data/clawd/sleep.gif" width="190" height="140" alt="Clawd — sleeping"></a><br> <strong>Sleeping</strong></td>
    <td align="center" width="33%"><a href="data/clawd/idle_blink.gif"><img src="data/clawd/idle_blink.gif" width="190" height="140" alt="Clawd — blinking"></a><br> <strong>Blinking</strong></td>
    <td align="center" width="33%"><a href="data/clawd/idle_look.gif"><img src="data/clawd/idle_look.gif" width="190" height="140" alt="Clawd — looking around"></a><br> <strong>Looking around</strong></td>
  </tr>
  <tr>
    <td align="center" width="33%"><a href="data/clawd/idle_hop.gif"><img src="data/clawd/idle_hop.gif" width="190" height="140" alt="Clawd — happy hop"></a><br> <strong>Happy hop</strong></td>
    <td align="center" width="33%"><a href="data/clawd/attention.gif"><img src="data/clawd/attention.gif" width="190" height="140" alt="Clawd — needs you"></a><br> <strong>Needs you</strong></td>
    <td align="center" width="33%"><a href="data/clawd/celebrate.gif"><img src="data/clawd/celebrate.gif" width="190" height="140" alt="Clawd — done!"></a><br> <strong>Done!</strong></td>
  </tr>
  <tr>
    <td align="center" width="33%"><a href="data/clawd/heart.gif"><img src="data/clawd/heart.gif" width="190" height="140" alt="Clawd — hello"></a><br> <strong>Hello</strong></td>
    <td align="center" width="33%"><a href="data/clawd/error.gif"><img src="data/clawd/error.gif" width="190" height="140" alt="Clawd — oops"></a><br> <strong>Oops</strong></td>
    <td align="center" width="33%"><a href="data/clawd/dizzy.gif"><img src="data/clawd/dizzy.gif" width="190" height="140" alt="Clawd — dizzy"></a><br> <strong>Dizzy</strong></td>
  </tr>
</table>

## Quick start

You need an **ESP32-2432S028R (CYD)**, a USB data cable, **Linux** with
**Python 3**, and **Chrome or Edge**. No PlatformIO: the firmware ships prebuilt.
The reference board uses an **ILI9341** display.

```bash
git clone https://github.com/kanishkaganguly/claude-buddy-cyd.git
cd claude-buddy-cyd
./install.sh
```

The installer opens the [web flasher](web/index.html) in Chrome (click
**Connect**, then **Install**). Then it reads the device token over USB, puts
the bridge and its Python libraries in `~/.claude/buddy/`, writes
`~/.claude/buddy.json`, and registers the
[Claude Code hooks](tools/HOOKS.md#2-hooks-claudesettingsjson) in
`~/.claude/settings.json` (backed up first). Start a Claude Code session and
Clawd wakes up.

USB and BLE work immediately; [WiFi is opt-in](docs/GUIDE.md#connections-usb-ble-wifi)
(the installer offers it). The bridge tries **USB → BLE → WiFi**. Re-flash with
`./install.sh flash` (leave **Erase device** unchecked to keep your token and
stats); remove everything with `./install.sh uninstall`.

Not on Linux? The flasher works in Chrome or Edge anywhere: run
`python3 -m http.server` in the repo, open <http://localhost:8000/web/>, then
follow the [manual setup](docs/GUIDE.md#first-time-setup).

## Using your buddy

Tap Clawd to say hello, swipe between stats, trends and live CPU / GPU / RAM
graphs of your PC while Claude works, and long-press for settings
(brightness, Quiet mode, Bluetooth on/off, and how long the screen stays on). Tap
**Got it** to dismiss an alert; triple-tap for a surprise.

If you turned on **on-device approval** during install, Claude's permission
prompts also appear on the screen: tap **Allow** or **Deny**. No tap within
about 26 s falls back to the normal terminal prompt.

| More details | Guide |
| --- | --- |
| Setup, transports, and remote computers | [Connection guide](docs/GUIDE.md#connections-usb-ble-wifi) |
| States, controls, and token counting | [Display & usage](docs/GUIDE.md#what-it-shows) |
| Battery power and other ESP32 boards | [Hardware](docs/GUIDE.md#hardware) |
| Common issues and development checks | [Troubleshooting](docs/GUIDE.md#troubleshooting) · [Development](docs/GUIDE.md#development) |

## License & credits

- **Code & tooling:** [MIT](LICENSE). © 2026 Qiankang (Kant) Wang.
- **This fork:** browser flasher, installer, System card, screen-off setting
  and Linux fixes by [Kanishka Ganguly](https://github.com/kanishkaganguly),
  under the same MIT license.
- **Clawd:** Anthropic's character, © Anthropic, PBC. These sprites are drawn by
  `tools/art/clawd_gen.py`; earlier releases adapted art from
  [clawd-on-desk](https://github.com/rullerzhou-afk/clawd-on-desk).
- Inspired by [claude-desktop-buddy](https://github.com/anthropics/claude-desktop-buddy) (MIT).
- CYD pinouts: [ESP32-Cheap-Yellow-Display](https://github.com/witnessmenow/ESP32-Cheap-Yellow-Display) (MIT).

Unofficial personal fan project, not affiliated with, sponsored by, or endorsed
by Anthropic. Claude and Clawd belong to Anthropic, PBC; used here to interoperate
with Claude Code for a non-commercial maker build.
