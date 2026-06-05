# Bridges

Bridges let editors and other tools call the `pykara` command without
embedding the Python engine directly.

## Aegisub Automation Script

Pykara includes an Aegisub Automation script at
[`bridge/pykara.lua`](../bridge/pykara.lua).

The Automation script adds a `pykara Apply Templates` macro. It runs the
current subtitle file through the installed `pykara` CLI, reads the generated
`.ass` output, removes old `fx` lines from the open subtitle, appends the new
`fx` lines, and comments source `karaoke` lines.

### Installation

Copy or symlink `bridge/pykara.lua` into your Aegisub Automation autoload
folder, then reload Automation scripts or restart Aegisub. Make sure `pykara`
is available in the same `PATH` seen by Aegisub.

Common locations:

| Platform | Autoload folder |
|----------|-----------------|
| Windows | `C:\Program Files\Aegisub\automation\autoload` |
| Linux | `~/.aegisub/automation/autoload` |
| macOS | `~/Library/Application Support/Aegisub/automation/autoload` |

### Usage

1. Open the `.ass` file in Aegisub.
1. Make sure the file contains Pykara template declarations and `karaoke`
   source lines.
1. **Save the file.** The macro reads the subtitle from disk, so any unsaved
   changes will not be processed.
1. Run `Automation` -> `pykara Apply Templates`.
