# Changelog

All notable changes to this project will be documented in this file.

## 0.10 - 2026-09-04

### Fixed

- Calculate gradient clips from visible glyph outlines instead of the full
  font cell, avoiding unnecessary slices above and below the text while
  preserving alignment.
- Include border and shadow extents in text gradient bounds, with padding for
  blur and antialiasing. Shadow gradients follow the shadow offset.
- Measure visible text bounds with GDI on Windows and FreeType/HarfBuzz on
  Linux and macOS, including font, scale, and spacing overrides.

## 0.9 - 2026-07-01

### Added

- Allow gradient usage with drawing shapes in karaoke templates.

## 0.8 - 2026-07-01

### Fixed

- Fixed false unused-variable warnings when an included Python file reads a
  value defined by an earlier `code setup` line.

## 0.7 - 2026-06-15

### Changed

- Refined the public `StyleInfo` API exposed by style helpers and template
  context values.

### Fixed

- Fixed preset style mapping when the same source style is reused for multiple
  target styles.

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
