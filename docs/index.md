# Pykara Documentation

**Pykara** is a karaoke templating framework written in Python, inspired by
the legacy Karaoke Templater from Aegisub.

## Installation

```sh
pip install pykara
```

## Command-Line Usage

```sh
pykara input.ass output.ass
pykara input.ass output.ass --json output.json
pykara input.ass output.ass --warn-only
pykara input.ass output.ass --seed 42
pykara input.ass output.ass --font-dir ./fonts
pykara input.ass output.ass --generated-only
```

| Flag | Description |
| -------------- | --------------------------------------------------------------------------- |
| `input` | Source `.ass` file. |
| `output` | Destination `.ass` file. |
| `--json PATH` | Also write generated events as JSON. |
| `--warn-only` | Demote validation errors to warnings and continue. |
| `--seed N` | Initial deterministic RNG seed. |
| `--font-dir PATH` | Prefer fonts from a directory before user/system fonts. Can be repeated. |
| `--generated-only` | Write only generated `fx` lines to the `.ass` output. |

## Documentation

### Directives

- [Types](./directives/types.md) — `template`, `mixin`, `code`, and `preset`.
- [Scopes](./directives/scopes.md) — Execution frequency and scope rules.
- [Variables](./directives/variables.md) — Complete `$variable` reference.
- [Include](./directives/include.md) — Load shared Python setup files.
- [Objects](./directives/objects.md) — Properties available in `!expr!`.
- [Modifiers](./directives/modifiers.md) — Directive modifier keywords.
- [Setup Scope](./directives/setup-scope.md) — One-time setup before any karaoke line runs.
- [Line Scope](./directives/line-scope.md) — One execution per karaoke line.
- [Word Scope](./directives/word-scope.md) — One execution per word.
- [Syllable Scope](./directives/syllable-scope.md) — One execution per syllable.
- [Char Scope](./directives/char-scope.md) — One execution per character inside a syllable.

### Tools

- [retime](./tools/retime.md) — Choose source timing for generated lines.
- [motion](./tools/motion.md) — Shadow-based or frame-by-frame motion effects.
- [gradient](./tools/gradient.md) — Clip-based color gradients, with frame-by-frame support.
- [layer](./tools/layer.md) — Change the generated line layer while rendering.
- [color](./tools/color.md) — Build ASS colors, alpha values, and blends.
- [assets](./tools/assets.md) — Namespace for named resources organized by category.
- [coord](./tools/coord.md) — Calculate screen-space offsets or point spreads.
- [shape](./tools/shape.md) — Move, rotate, center, or generate ASS drawings.
- [global](./tools/global.md) — Call helper functions directly, without a namespace.
- [builtins](./tools/builtins.md) — Safe Python built-in functions.
- [math](./tools/math.md) — Numeric calculations inside `!expr!` and code.
- [random](./tools/random.md) — Pseudo-random variation for generated lines.

### Bridges

- [Bridges](./bridges.md) — Use Pykara from editors and external tools.

## License

Distributed under the MIT License.
