# Bridges

Bridges let editors call the `pykara` CLI without embedding the Python engine.

## Aegisub Automation Script

[`bridge/pykara.lua`](../bridge/pykara.lua) adds a `Pykara Templater` menu
with two macros:

- `Apply template` — passes the file to `pykara`, removes existing `fx` lines,
  appends the generated ones, and comments source `karaoke` lines.
- `Remove FX` — removes dialogue lines whose Effect field is exactly `fx`.

### Installation

Copy or symlink `bridge/pykara.lua` into your Aegisub Automation autoload
folder and reload scripts (or restart Aegisub). `pykara` must be on the `PATH`
visible to Aegisub.

| Platform | Autoload folder |
|----------|-----------------|
| Windows | `C:\Program Files\Aegisub\automation\autoload` |
| Linux | `~/.aegisub/automation/autoload` |
| macOS | `~/Library/Application Support/Aegisub/automation/autoload` |

### Usage

1. Open the `.ass` file in Aegisub.
1. **Save the file** — the macro reads from disk.
1. Run `Automation` → `Pykara Templater` → `Apply template`.

To remove generated lines, run `Remove FX` from the same menu.
