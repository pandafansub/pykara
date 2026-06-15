# Changelog

All notable changes to this project will be documented in this file.

## 0.6 - 2026-06-14

### Added

- Added the global `get_style` helper for accessing ASS style definitions.
- Added the `math.remap` helper for converting values between numeric ranges.

## 0.5 - 2026-06-12

### Added

- Added CLI framerate inputs for frame-by-frame effects, including timecode
  and timeline support for effect expansion.

### Fixed

- Added support for gradients in mixins.
- Added support for rational FPS values in frame-by-frame expansion.

## 0.4 - 2026-06-09

### Added

- Added `preset` declarations for loading reusable Pykara declarations from
  another ASS file, including preserved styles, `for` style expansion, and
  `map` style remapping.
- Added an Aegisub `Remove FX` macro for deleting generated `fx` dialogue
  lines from the bridge menu.

### Fixed

- Improved validation for cross-declaration references, string arguments, and
  mixin/template compatibility.

## 0.3 - 2026-06-08

### Added

- Added `include` support for `code setup` directives, allowing shared Python
  setup files to be loaded into templates.

### Fixed

- Simplified missing font errors so unresolved font names are reported more
  clearly.

## 0.2 - 2026-06-07

### Added

- Added the `loop` expression object for loop-aware templates and code.
- Added documentation, specification coverage, and tests for loop expression
  values.

## 0.1 - 2026-06-05

Initial public release of pykara.
